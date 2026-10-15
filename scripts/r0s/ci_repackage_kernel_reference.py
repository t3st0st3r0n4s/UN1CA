#!/usr/bin/env python3
"""Repackage exactly the signed, native UN1CA A16 reference boot-chain bytes.

This CI step does NOT substitute the independently GitHub-compiled Image;
signed reference images cannot be silently patched without repeating AVB,
fstab, module-ABI, and GZH3 verification. Provenance labels this limitation.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

KERNEL_PIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU_PIN = "8f902aeb16033024143ae36cf711df902cf02fae"
TF_SHA = "4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a"
UB_BLOB = "0a6085a9251b664ed0b591d8457ca2c01afaaa8e"
US_BLOB = "3973dff6043769d063b792c78739c5236a8e808a"
REF_NAME = "ExtremeKRNL-v2.5_r0s_KSUNext-v3.4.1_13-10-2026_19-42-41.zip"
RELEASE = "r0s-a16-kernel-reference-v1"
ENTRIES = ("META-INF/com/google/android/update-binary",
           "META-INF/com/google/android/updater-script",
           "files/boot.img", "files/vendor_boot.img", "files/dtbo.img")
CAPS = {"boot.img": 67108864, "vendor_boot.img": 33554432,
        "dtbo.img": 8388608}

def need(v, msg):
    if not v:
        raise RuntimeError("A16 ZIP REPACKAGE HOLD: " + msg)

def digest(file):
    h = hashlib.sha256()
    for block in iter(lambda: file.read(1048576), b""):
        h.update(block)
    return h.hexdigest()

def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main(reference: Path, manifest_path: Path, dest: Path):
    m = json.loads(manifest_path.read_text())
    required = {"schema": 1, "device": "SM-S901B", "android": 16,
                "reference_filename": REF_NAME, "release_tag": RELEASE,
                "kernel_source": KERNEL_PIN, "ksunext_source": KSU_PIN,
                "ksunext_release": "v3.4.1",
                "target_files_sha256": TF_SHA}
    for k, v in required.items():
        need(m.get(k) == v, "untrusted manifest: " + k)
    need(reference.is_file() and reference.name == REF_NAME, "host reference asset absent")
    with reference.open("rb") as f:
        need(digest(f) == m["reference_zip_sha256"], "release asset SHA mismatch")
    with zipfile.ZipFile(reference) as inp:
        infos = [i for i in inp.infolist() if not i.is_dir()]
        need(len(infos) == 5 and {i.filename for i in infos} == set(ENTRIES),
             "reference is not exactly the original five-entry kernel ZIP")
        need(inp.testzip() is None, "reference ZIP CRC invalid")
        need(blob(inp.read(ENTRIES[0])) == UB_BLOB, "updater binary source drift")
        script = inp.read(ENTRIES[1])
        need(blob(script) == US_BLOB and b"E3099" not in script,
             "original updater script drift")
        writes = {s.strip() for s in script.decode().splitlines()
                  if s.strip().startswith("package_extract_file(")}
        expected = {f'package_extract_file("files/{name}", "/dev/block/by-name/{name[:-4]}");'
                    for name in CAPS}
        need(writes == expected, "unexpected partition write list")
        for n, size in CAPS.items():
            key = "files/" + n
            need(inp.getinfo(key).file_size == size,
                 "reference signed image does not occupy partition: " + n)
            with inp.open(key) as payload:
                need(digest(payload) == m["images"][n]["sha256"],
                     "reference image hash differs from manifest: " + n)

        dest.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%d-%m-%Y_%H-%M-%S")
        output = dest / f"ExtremeKRNL-v2.5_r0s_KSUNext-v3.4.1_{stamp}.zip"
        need(not output.exists(), "refuse overwrite")
        with zipfile.ZipFile(output, "w", allowZip64=True) as out:
            for info in infos:
                with inp.open(info) as reader, out.open(info, "w", force_zip64=True) as writer:
                    for part in iter(lambda: reader.read(1048576), b""):
                        writer.write(part)

        with zipfile.ZipFile(output) as check:
            need(check.testzip() is None and set(check.namelist()) == set(ENTRIES),
                 "repack ZIP validation failed")
            for name in ENTRIES:
                with inp.open(name) as x, check.open(name) as y:
                    need(digest(x) == digest(y), "repack changed ZIP member: " + name)
        with output.open("rb") as f:
            outsha = digest(f)
        evidence = {"status": "REPACKAGED_FROM_EXISTING_SIGNED_HOST_IMAGES",
                    "a16_board_qualified": False,
                    "uses_new_cloud_compiled_kernel": False,
                    "requires_dynamic_cloud_kernel_reconciliation": True,
                    "reference_sha256": m["reference_zip_sha256"],
                    "kernel_source": KERNEL_PIN, "ksunext_source": KSU_PIN,
                    "target_files_sha256": TF_SHA,
                    "output": output.name, "output_sha256": outsha,
                    "partition_image_bytes_unchanged": True,
                    "updater_binary_and_script_unchanged": True}
        (dest / "provenance.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        (dest / "SHA256SUMS.txt").write_text(outsha + "  " + output.name + "\n")
        (dest / "NOT_BOARD_QUALIFIED.txt").write_text(
            "UN1CA A16 GZH3 reference ZIP repackage. Same reconciled signed "
            "partition images as the trusted 13 October host ZIP. "
            "NOT a newly compiled kernel update; A16 runtime remains untested. "
            "No KSU update or vendor_dlkm change. Do not interpret CI PASS "
            "as a physical S901B boot/flash qualification.\n")
    print("A16 ORIGINAL FIVE-ENTRY ZIP REPACKAGE HOST PARITY PASS")
    print("image_bytes_unchanged=true; newly_compiled_kernel_embedded=false")
    print("output=" + str(output))
    print("sha256=" + outsha)

if __name__ == "__main__":
    try:
        need(len(sys.argv) == 4,
             "usage: ci_repackage_kernel_reference.py REFERENCE.zip manifest.json DIST")
        main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    except (RuntimeError, OSError, KeyError, ValueError, zipfile.BadZipFile) as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
