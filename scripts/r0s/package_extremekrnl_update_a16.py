#!/usr/bin/env python3
"""Create a HOST-ONLY A16 r0s kernel-update recovery payload from target-files.

The upstream ExtremeKRNL recovery ZIP is unsafe for GZH3: it uses native-
incompatible vendor_boot ramdisk00 and omits matching vendor_dlkm modules.
This packaging gate copies the *verified, AVB-signed* reconciled boot images
and vendor_dlkm partition image from existing host-only target-files.

It intentionally does NOT include an update-binary or any flashing command.
The contained updater-script unconditionally aborts with E3099. This ZIP
is a retained development payload, NOT a flashable recovery ZIP. Do not
relax until recovery mapping, AVB trust, bootloader, ABI and BOARD qualify.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "out/r0s_A16_GZH3_HOST_ONLY-target_files.zip"
OUTPUT = ROOT / "out/r0s_A16_ExtremeKRNL_KSUNext_v3.4.1_GZH3_RECOVERY_HOLD.zip"
E3099 = ('abort("E3099: UN1CA sixteen-r0s is under development and '
         'NOT qualified for flashing.");')
KERNEL_PIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU_PIN = "8f902aeb16033024143ae36cf711df902cf02fae"
MANAGER_APK_SHA = "f41778ee812512ae96bf53e7265114de5e0414bc5cb92397f49e1052d77da118"
SOURCE_PARTITIONS = ("boot.img", "vendor_boot.img", "dtbo.img",
                     "vendor_dlkm.img")
CAPS = {"boot.img": 67108864, "vendor_boot.img": 33554432,
        "dtbo.img": 8388608}
ZIPS = {"images/" + name: name for name in SOURCE_PARTITIONS}
DOC = (
    "NOT FLASHABLE / E3099 ACTIVE\n\n"
    "Android 16, Samsung Galaxy S22 SM-S901B (r0s), GZH3/UN1CA.\n"
    "Kernel 5.10.269 ExtremeKRNL v2.5, built-in KernelSU Next v3.4.1.\n"
    "The 'images/' payload contains AVB-signed boot, vendor_boot, dtbo,\n"
    "and the matching GZH3 vendor_dlkm EROFS logical-partition image.\n"
    "These are derived from the validated UN1CA target-files archive, NOT\n"
    "from the upstream ExtremeKRNL recovery ZIP. No update-binary exists.\n"
    "The updater-script aborts unconditionally with E3099, no partition\n"
    "writer is provided, and no phone is accessed by the package builder.\n"
    "The user must NOT rename, flash, sideload or extract-and-dd this ZIP.\n"
    "A future installer needs a qualified TWRP/OTA/recovery environment,\n"
    "r0s/GZH3 identification, proper dynamic vendor_dlkm mapping, AVB\n"
    "chain/trust, exact module ABI, backups/rollback, and actual BOARD PASS.\n"
    "Even after qualification, kernel-only updates must carry any changed\n"
    "vendor_dlkm modules and preserve native GZH3 vendor_boot ramdisk00.\n"
)
UPDATER = "# Unconditional development abort; never writes partitions.\n" + E3099 + "\n"
MANIFEST_NAME = "KERNEL_UPDATE_MANIFEST.json"
README_NAME = "NOT_FLASHABLE.txt"
UPDATER_NAME = "META-INF/com/google/android/updater-script"


class Hold(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Hold(reason)


def digest(f):
    h = hashlib.sha256()
    while True:
        b = f.read(1024 * 1024)
        if not b:
            break
        h.update(b)
    return h.hexdigest()


def file_digest(p):
    with p.open("rb") as f:
        return digest(f)


def zip_digest(z, member):
    with z.open(member) as f:
        return digest(f)


def entry(name, data):
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 13, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info, data


def inputs(source, source_digest):
    need(re.fullmatch(r"[0-9a-f]{64}", source_digest), "expected SHA256 must be 64 lowercase hex digits")
    need(source.is_file() and source.stat().st_size > 0, "target-files ZIP missing")
    need(file_digest(source) == source_digest, "target-files SHA256 does not match")
    lock = (ROOT / "target/r0s/installer/assertions.edify").read_text()
    need(E3099 in lock, "E3099 global installer lock missing")
    work = ROOT / "out/target/r0s/work_dir"
    need((work / "kernel/.r0s_extremekrnl_a16_integrated").is_file(),
         "hybrid kernel not marked as integrated")
    need((work / "system/system/etc/unica/ksunext/manager_payload.bin").is_file(),
         "A16 manager auto-install payload missing from workdir")
    need(file_digest(work / "system/system/etc/unica/ksunext/manager_payload.bin")
         == MANAGER_APK_SHA, "A16 KSU manager payload changed")
    with zipfile.ZipFile(source) as z:
        names = z.namelist()
        for name in SOURCE_PARTITIONS:
            need(names.count(name) == 1, "target-files missing/duplicated " + name)
            item = z.getinfo(name)
            need(item.file_size > 0, "empty " + name)
            if name in CAPS:
                need(item.file_size == CAPS[name],
                     "signed boot image is not filled to physical partition cap: " + name)
        need("unsparse_super_empty.img" in names, "GZH3 LP metadata absent")
        need(z.testzip() is None, "target-files ZIP member CRC failure")
    print("A16 KSU KERNEL-UPDATE PAYLOAD SOURCE/PIN CHECK PASS — E3099 ACTIVE")
    print("Source archive: " + str(source))
    print("Source SHA256: " + source_digest)


def deep_audits(source, source_digest):
    for name in ("audit_target_files_host.sh", "audit_packaged_kernel_modules.sh"):
        script = ROOT / "scripts/r0s" / name
        need(script.is_file(), "missing deep audit: " + name)
        env = dict(os.environ)
        env["PATH"] = str(ROOT / "out/tools/bin") + os.pathsep + env.get("PATH", "")
        print("===== HOST DEEP AUDIT: " + name + " =====", flush=True)
        r = subprocess.run(["bash", str(script), str(source), source_digest], env=env)
        need(r.returncode == 0, "source target-files failed: " + name)


def build(source, source_digest, output):
    need(not output.exists(), "existing output will not be overwritten: " + str(output))
    inputs(source, source_digest)
    deep_audits(source, source_digest)
    need(not output.exists(), "output appeared while validating")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, stage_name = tempfile.mkstemp(prefix=".r0s-ksu-recovery-hold-", suffix=".zip",
                                      dir=output.parent)
    os.close(fd)
    stage = Path(stage_name)
    try:
        packed = {}
        with zipfile.ZipFile(source) as zsrc, zipfile.ZipFile(stage, "w", allowZip64=True) as zout:
            for output_name, input_name in ZIPS.items():
                h = hashlib.sha256()
                with zsrc.open(input_name) as reader, zout.open(
                    zipfile.ZipInfo(output_name, date_time=(2026, 10, 13, 0, 0, 0)),
                    "w", force_zip64=True
                ) as writer:
                    while True:
                        b = reader.read(1024 * 1024)
                        if not b:
                            break
                        h.update(b)
                        writer.write(b)
                packed[output_name] = {"sha256": h.hexdigest(),
                                       "size": zsrc.getinfo(input_name).file_size}
            manifest = {
                "status": "HOST_ONLY_NOT_FLASHABLE",
                "device": "SM-S901B",
                "codename": "r0s",
                "source_firmware": "S901BXXSOGZH3",
                "android_api": 36,
                "kernel_release": "5.10.269-ExtremeKRNL-v2.5+",
                "kernel_source_commit": KERNEL_PIN,
                "ksunext_version": "3.4.1",
                "ksunext_commit": KSU_PIN,
                "source_target_files_sha256": source_digest,
                "payload": packed,
                "e3099_enforced": True,
                "board_qualified": False,
                "recovery_installer_included": False,
            }
            for name, body in (
                (README_NAME, DOC.encode()),
                (UPDATER_NAME, UPDATER.encode()),
                (MANIFEST_NAME, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()),
            ):
                info, data = entry(name, body)
                zout.writestr(info, data)
        verify(stage, expected_source_digest=source_digest)
        need(not output.exists(), "output appeared while assembling")
        stage.replace(output)
    finally:
        stage.unlink(missing_ok=True)
    print("A16 EXTREMEKRNL / KSU NEXT RECOVERY-HOLD PAYLOAD HOST PASS")
    print("Archive: " + str(output))
    print("SHA256: " + file_digest(output))
    print("NOT FLASHABLE; E3099 ACTIVE; target-files and original kernel cache preserved")


def verify(archive, expected_source_digest=None):
    need(archive.is_file() and archive.stat().st_size > 0, "missing package")
    with zipfile.ZipFile(archive) as z:
        need(z.testzip() is None, "kernel update ZIP CRC failed")
        names = z.namelist()
        need(set(names) == set(ZIPS) | {README_NAME, UPDATER_NAME, MANIFEST_NAME},
             "unexpected or missing recovery payload members")
        need("META-INF/com/google/android/update-binary" not in names,
             "unsafe: flashable updater binary is present")
        need(z.read(README_NAME).decode() == DOC, "NOT_FLASHABLE warning changed")
        need(z.read(UPDATER_NAME).decode() == UPDATER,
             "unconditional E3099 updater-script changed")
        m = json.loads(z.read(MANIFEST_NAME))
        need(m.get("status") == "HOST_ONLY_NOT_FLASHABLE"
             and m.get("e3099_enforced") is True
             and m.get("board_qualified") is False
             and m.get("recovery_installer_included") is False,
             "unsafe manifest gate state")
        need(m.get("kernel_source_commit") == KERNEL_PIN
             and m.get("ksunext_commit") == KSU_PIN
             and m.get("ksunext_version") == "3.4.1",
             "kernel/KSU provenance drift")
        src = m.get("source_target_files_sha256")
        need(isinstance(src, str) and re.fullmatch(r"[0-9a-f]{64}", src),
             "source target-files SHA256 missing")
        if expected_source_digest:
            need(src == expected_source_digest, "source target-files digest drift")
        for member in ZIPS:
            meta = m["payload"].get(member, {})
            need(meta.get("size") == z.getinfo(member).file_size,
                 "member size mismatch: " + member)
            need(meta.get("sha256") == zip_digest(z, member),
                 "member SHA256 mismatch: " + member)
    print("A16 KERNEL-UPDATE RECOVERY-HOLD ARCHIVE VERIFY PASS — no writes to any device")
    print("NO update-binary / updater-script E3099 / TWRP flashing unsupported")


def self_test():
    need(E3099 in UPDATER and "package_extract_file" not in UPDATER,
         "updater-script accidentally writes partitions")
    need(len(KERNEL_PIN) == len(KSU_PIN) == 40 and len(MANAGER_APK_SHA) == 64,
         "source hash pins malformed")
    need(set(CAPS) <= set(SOURCE_PARTITIONS), "partitions mismatched")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "test.zip"
        payload = b"not a flashable recovery package"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr(UPDATER_NAME, UPDATER)
        with zipfile.ZipFile(path) as z:
            need(z.read(UPDATER_NAME).decode() == UPDATER, "unconditional abort altered")
        need(payload and not any(x in UPDATER for x in ("dd if=", "block_image_update(", "package_extract_file(")),
             "unsafe recovery writer")
    print("A16 kernel-only update payload safety/pin self-test PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "build", "verify", "self-test"))
    parser.add_argument("sha256", nargs="?", help="expected existing target-files SHA256 (check/build)")
    args = parser.parse_args()
    if args.mode == "self-test":
        need(args.sha256 is None, "self-test takes no digest")
        self_test()
    elif args.mode in ("check", "build"):
        need(args.sha256 is not None, "supply the exact SHA256 of target-files")
        if args.mode == "check":
            inputs(SOURCE, args.sha256)
        else:
            build(SOURCE, args.sha256, OUTPUT)
    elif args.mode == "verify":
        need(args.sha256 is None, "verify takes no digest")
        verify(OUTPUT)


if __name__ == "__main__":
    try:
        main()
    except (Hold, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print("A16 KERNEL UPDATE PACKAGING BLOCKED: " + str(exc), file=sys.stderr)
        sys.exit(2)
