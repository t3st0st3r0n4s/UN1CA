#!/usr/bin/env python3
"""Read-only A16 r0s cloud-vs-host kernel parity; no repack, signing or flashing.

Use the artifact from GitHub Actions run 38706744894, built at:
  milxnaq/s5e9925 78f891e1d3cf... + KernelSU Next 8f902aeb...
Compare raw cloud compiler products with the retained host compiler and
the *reconciled* signed A16 package. Never equate a raw upstream boot
image with its signed GZH3 final image by comparing whole-file hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

KERNEL_PIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU_PIN = "8f902aeb16033024143ae36cf711df902cf02fae"
CI_SHA = "987ff0ad4f9b3d741a3664af55722d86248b788b1a7a613073886bd9283f1e59"
ZIP_NAME = "UN1CA-A16-E3099-UNRECONCILED-ExtremeKRNL-v2.5_r0s_KSU_15-10-2026_09-14-07.zip"
HOST_NAME = "ExtremeKRNL-v2.5_r0s_KSUNext-v3.4.1_13-10-2026_19-42-41.zip"
MODULES = ("fingerprint.ko", "fingerprint_sysfs.ko", "input_booster_lkm.ko",
           "sec_debug_coredump.ko", "wlan.ko")
PARTS = ("boot", "vendor_boot", "dtbo")
BIN = "META-INF/com/google/android/update-binary"
EDIFY = "META-INF/com/google/android/updater-script"
EXPECTED_MEMBERS = {BIN, EDIFY, *(f"files/{p}.img" for p in PARTS)}

class Hold(Exception):
    pass

def need(ok: bool, msg: str):
    if not ok:
        raise Hold(msg)

def filehash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def bytehash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def call(*args) -> str:
    r = subprocess.run(list(map(str, args)), text=True, capture_output=True)
    need(r.returncode == 0, "command failed: " + " ".join(map(str, args)) +
         "\n" + r.stderr[-1000:])
    return r.stdout

def unpack(path: Path, dst: Path, unpack_bootimg: Path) -> dict[str, Path]:
    dst.mkdir()
    call(unpack_bootimg, "--boot_img", path, "--out", dst)
    return {f.name: f for f in dst.iterdir() if f.is_file()}

def compare(label: str, left: Path, right: Path, failures: list[str]):
    need(left.is_file(), "missing comparison input: " + str(left))
    need(right.is_file(), "missing comparison input: " + str(right))
    a, b = filehash(left), filehash(right)
    status = "MATCH" if a == b else "DIFF"
    print(f"[{status}] {label} cloud={a} host={b}")
    if a != b:
        failures.append(label)

def get_one(m: dict[str, Path], name: str, what: str) -> Path:
    need(name in m, f"{what}: no {name} after unpack_bootimg")
    return m[name]

def run(root: Path, artifact: Path, host_zip: Path, cloud_sha: str):
    need(re.fullmatch(r"[0-9a-f]{64}", cloud_sha) is not None,
         "expected cloud ZIP sha256 must be 64 lowercase hex digits")
    need(artifact.is_file() and host_zip.is_file(), "missing artifact or host ZIP")
    need(filehash(artifact) == cloud_sha, "CI ZIP digest differs; do not trust payload")
    provenance = artifact.parent / "provenance.json"
    need(provenance.is_file(), "CI provenance.json missing")
    report = json.loads(provenance.read_text())
    need(report.get("status") == "HOST-ONLY_UNRECONCILED_E3099_NONFLASHABLE",
         "CI provenance status invalid")
    need(report.get("kernel_source") == KERNEL_PIN and
         report.get("ksunext_source") == KSU_PIN, "CI source commit pin mismatch")
    need(report.get("ksunext_release") == "v3.4.1" and
         report.get("zip_sha256") == cloud_sha, "CI release or ZIP hash mismatch")
    need(report.get("A16_GZH3_boot_chain_reconciled") is False and
         report.get("A16_board_pass") is False, "CI provenance incorrectly qualified")

    kernel = root / "out/kernel_tmp-exynos2200"
    work = root / "out/target/r0s/work_dir"
    need((kernel / "build/out/r0s").is_dir(), "retained host compiler output missing")
    need(call("git", "-C", kernel, "rev-parse", "HEAD").strip() == KERNEL_PIN,
         "host kernel source pin drift")
    need(call("git", "-C", kernel / "KernelSU-Next",
              "rev-parse", "HEAD").strip() == KSU_PIN, "host KSU pin drift")
    need((work / "kernel/.r0s_extremekrnl_a16_integrated").is_file(),
         "A16 GZH3 late-integration marker missing")
    signed_report = host_zip.with_suffix(".provenance.json")
    need(signed_report.is_file(), "host signed ZIP provenance missing")
    host_prov = json.loads(signed_report.read_text())
    need(host_prov.get("kernel_zip_sha256") == filehash(host_zip),
         "host signed ZIP/provenance hash mismatch")
    need(host_prov.get("kernel_source") == KERNEL_PIN and
         host_prov.get("ksunext_source") == KSU_PIN, "host source pin mismatch")
    need(host_prov.get("ksunext_release") == "v3.4.1",
         "host package KernelSU version mismatch")
    unpacker = root / "out/tools/bin/unpack_bootimg"
    need(unpacker.is_file(), "existing UN1CA unpack_bootimg tool missing")
    failed: list[str] = []

    with tempfile.TemporaryDirectory(prefix="r0s_cloud_host_parity_") as scratch:
        t = Path(scratch)
        with zipfile.ZipFile(artifact) as cloud, zipfile.ZipFile(host_zip) as signed:
            need(set(cloud.namelist()) == EXPECTED_MEMBERS and
                 len(cloud.namelist()) == 5, "unexpected cloud ZIP entries")
            need(set(signed.namelist()) == EXPECTED_MEMBERS and
                 len(signed.namelist()) == 5, "unexpected host ZIP entries")
            need(cloud.testzip() is None and signed.testzip() is None,
                 "ZIP CRC verification failed")
            need(cloud.read(EDIFY).startswith(b'abort("E3099:'),
                 "cloud updater safety abort absent")
            need(b"E3099" not in signed.read(EDIFY),
                 "host reference updater unexpectedly contains E3099")
            need(cloud.read(BIN) == signed.read(BIN),
                 "updater binary differs between cloud and host")
            print("Original ExtremeKRNL recovery update-binary MATCH")
            images = {}
            for part in PARTS:
                raw = t / f"cloud_{part}.img"
                final = t / f"signed_{part}.img"
                raw.write_bytes(cloud.read(f"files/{part}.img"))
                final.write_bytes(signed.read(f"files/{part}.img"))
                images[part] = (raw, final)
                expected = report.get("images", {}).get(part, {})
                need(expected.get("sha256") == filehash(raw) and
                     expected.get("bytes") == raw.stat().st_size,
                     "cloud " + part + " disagrees with its provenance")
                compare("cloud vs retained upstream " + part + ".img",
                        raw, kernel / "build/out/r0s" / (part + ".img"), failed)
                compare("signed ZIP vs integrated workdir " + part + ".img",
                        final, work / "kernel" / (part + ".img"), failed)

        cb = unpack(images["boot"][0], t / "cb", unpacker)
        hb = unpack(kernel / "build/out/r0s/boot.img", t / "hb", unpacker)
        sb = unpack(images["boot"][1], t / "sb", unpacker)
        compare("compiled Image cloud vs host", get_one(cb, "kernel", "cloud boot"),
                get_one(hb, "kernel", "host upstream boot"), failed)
        compare("compiled Image cloud vs GZH3 signed",
                get_one(cb, "kernel", "cloud boot"),
                get_one(sb, "kernel", "signed boot"), failed)
        cv = unpack(images["vendor_boot"][0], t / "cv", unpacker)
        hv = unpack(kernel / "build/out/r0s/vendor_boot.img", t / "hv", unpacker)
        sv = unpack(images["vendor_boot"][1], t / "sv", unpacker)
        for fragment in ("dtb", "vendor_ramdisk01"):
            compare("cloud vs upstream host " + fragment,
                    get_one(cv, fragment, "cloud vendor_boot"),
                    get_one(hv, fragment, "host vendor_boot"), failed)
            compare("cloud vs GZH3 signed " + fragment,
                    get_one(cv, fragment, "cloud vendor_boot"),
                    get_one(sv, fragment, "signed vendor_boot"), failed)

        # CI exposes all five module hashes from its real modules_install.
        # Their presence in the unchanged installed vendor_dlkm is a
        # prerequisite for a three-image-only kernel update.
        modules = report.get("compiled_vendor_modules_sha256", {})
        need(set(modules) == set(MODULES), "CI five-module provenance incomplete")
        for module in MODULES:
            cloud_hash = modules[module]
            for label, local in (
                ("retained compiled", kernel / "build/out/r0s/modules/lib/modules" / module),
                ("integrated vendor_dlkm", work / "vendor_dlkm/lib/modules" / module),
            ):
                need(local.is_file(), label + " module missing: " + module)
                host_hash = filehash(local)
                status = "MATCH" if host_hash == cloud_hash else "DIFF"
                print(f"[{status}] {module}: cloud vs {label} ({cloud_hash} / {host_hash})")
                if host_hash != cloud_hash:
                    failed.append(module + " vs " + label)

        # dtbo.img is padded and/or AVB-modified in signed target-files.
        # Do not compare signed dtbo to the raw unpadded input by full hash.
        print("[INFO] signed DTBO is not asserted byte-identical to raw DTBO "
              "(partition padding/AVB may differ).")

    if failed:
        print("\nA16 CLOUD/HOST PARITY HOLD; " + str(len(failed)) +
              " differences, NOT a substitute for the GZH3 package.")
        for item in failed:
            print("  DIFFERENCE: " + item)
        raise Hold("cloud raw build differs from the existing host compiler "
                   "or GZH3 payload; reconciliation/signing required")
    print("\nA16 CLOUD/HOST BINARY PARITY PASS")
    print("Existing reference GZH3 ZIP remains the only verified host "
          "package; cloud CI has NOT produced a new signed ZIP.")
    print("A16 physical boot and native kernel-only update are still untested.")

def self_test():
    need(bytehash(b"") ==
         "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
         "sha256 fixture")
    need(len(MODULES) == 5 and len(EXPECTED_MEMBERS) == 5,
         "3-image/recovery contract fixture")
    need(CI_SHA == "987ff0ad4f9b3d741a3664af55722d86248b788b1a7a613073886bd9283f1e59",
         "pinned build fixture")
    print("A16 cloud/host parity self-test PASS (no device or kernel writes)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repo", type=Path, default=Path.cwd(),
                        help="UN1CA checkout root")
    parser.add_argument("--artifact-dir", type=Path,
                        help="directory created by gh run download")
    parser.add_argument("--cloud-sha256", default=CI_SHA,
                        help="sha256 of exact CI inner ZIP (pinned run #1 by default)")
    parser.add_argument("--host-zip", type=Path,
                        help="signed GZH3 reference ZIP (default: known Oct 13 build)")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            root = args.repo.resolve()
            need((root / "scripts/r0s/package_extremekrnl_update_a16.py").is_file(),
                 "not an UN1CA checkout: " + str(root))
            need(args.artifact_dir is not None, "--artifact-dir is required")
            folder = args.artifact_dir.resolve()
            need(folder.is_dir(), "CI artifact directory missing; run gh run download first")
            matches = [f for f in folder.rglob("*.zip") if
                       f.name == ZIP_NAME]
            need(len(matches) == 1,
                 "expected exactly one pinned run #1 E3099 ZIP; found "
                 + str(len(matches)))
            host = (args.host_zip.resolve() if args.host_zip else
                    root / "out" / HOST_NAME)
            run(root, matches[0], host, args.cloud_sha256)
    except (Hold, OSError, zipfile.BadZipFile, ValueError,
            subprocess.SubprocessError) as exc:
        print("A16 CLOUD/HOST PARITY HOLD: " + str(exc), file=sys.stderr)
        sys.exit(2)
