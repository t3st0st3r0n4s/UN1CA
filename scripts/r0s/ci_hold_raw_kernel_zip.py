#!/usr/bin/env python3
"""Safely quarantine upstream A16 ExtremeKRNL's raw ZIP as a CI-only artifact.

The upstream kernel build includes an incompatible (non-GZH3-reconciled)
vendor_boot ramdisk. Never publish its original ZIP as a flashable UN1CA update.
The original upstream updater binary / image payloads are left byte-identical;
only the recovery updater script is prefixed with the mandatory E3099 abort.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

KERNEL_PIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU_PIN = "8f902aeb16033024143ae36cf711df902cf02fae"
BINARY_BLOB = "0a6085a9251b664ed0b591d8457ca2c01afaaa8e"
SCRIPT_BLOB = "3973dff6043769d063b792c78739c5236a8e808a"
IMAGES = ("boot", "vendor_boot", "dtbo")
CAPS = (67108864, 33554432, 8388608)
MODULES = ("fingerprint.ko", "fingerprint_sysfs.ko", "input_booster_lkm.ko",
           "sec_debug_coredump.ko", "wlan.ko")
BIN = "META-INF/com/google/android/update-binary"
SCRIPT = "META-INF/com/google/android/updater-script"
MEMBERS = {BIN, SCRIPT, *(f"files/{n}.img" for n in IMAGES)}
ABORT = ('abort("E3099: UN1CA Android 16 upstream kernel ZIP is '
         'NOT GZH3-reconciled and NOT qualified for flashing.");\n')
PATTERN = re.compile(r"ExtremeKRNL-[A-Za-z0-9.+-]+_r0s_KSU_"
                     r"\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}\.zip")

def need(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError("A16 KERNEL CI HOLD: " + msg)

def sh(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def test():
    need(ABORT.startswith('abort("E3099:') and ABORT.endswith(');\n'), "guard format")
    need(len(MEMBERS) == 5, "archive contract")
    need(PATTERN.fullmatch("ExtremeKRNL-v2.5_r0s_KSU_13-10-2026_21-00-00.zip") is not None,
         "upstream name fixture")
    need(blob(b"test") == "30d74d258442c7c65512eafab474568dd706c430", "git blob fixture")
    print("A16 QUARANTINED KERNEL ZIP SELF-TEST PASS (no firmware/build/flash)")

def package(kernel: Path, dist: Path) -> None:
    need(sh("git", "-C", str(kernel), "rev-parse", "HEAD") == KERNEL_PIN,
         "wrong ExtremeKRNL commit")
    need(sh("git", "-C", str(kernel / "KernelSU-Next"), "rev-parse", "HEAD") == KSU_PIN,
         "wrong KernelSU Next commit")
    need("v3.4.1" in sh("git", "-C", str(kernel / "KernelSU-Next"),
                       "tag", "--points-at", "HEAD").splitlines(),
         "pinned KSU commit lacks verified v3.4.1 release tag")
    config = (kernel / "out/.config").read_text()
    for setting in ("CONFIG_KSU=y", "CONFIG_MODULES=y", "CONFIG_MODVERSIONS=y",
                    "CONFIG_CFI_CLANG=y"):
        need(setting in config.splitlines(), "built kernel missing " + setting)
    candidates = list((kernel / "build/out/r0s").glob("*_r0s_KSU_*.zip"))
    need(len(candidates) == 1 and PATTERN.fullmatch(candidates[0].name) is not None,
         "not exactly one named upstream kernel ZIP")
    srczip = candidates[0]
    with zipfile.ZipFile(srczip) as z:
        file_names = [info.filename for info in z.infolist() if not info.is_dir()]
        need(set(file_names) == MEMBERS and len(file_names) == 5,
             "upstream recovery ZIP file inventory changed")
        need(z.testzip() is None, "upstream ZIP CRC failure")
        binary = z.read(BIN)
        script = z.read(SCRIPT)
        need(blob(binary) == BINARY_BLOB, "upstream updater binary changed")
        need(blob(script) == SCRIPT_BLOB, "upstream updater script changed")
        text = script.decode()
        writes = [line.strip() for line in text.splitlines()
                  if line.strip().startswith("package_extract_file(")]
        expected = [f'package_extract_file("files/{n}.img", "/dev/block/by-name/{n}");'
                    for n in IMAGES]
        need(len(writes) == 3 and set(writes) == set(expected),
             "upstream updater no longer writes exactly three images")
        images = {}
        for image, cap in zip(IMAGES, CAPS):
            payload = z.read(f"files/{image}.img")
            need(0 < len(payload) <= cap, image + " partition capacity exceeded")
            if image == "boot":
                need(payload.startswith(b"ANDROID!"), "boot magic invalid")
            images[image] = payload

    module_hashes = {}
    for name in MODULES:
        path = kernel / "build/out/r0s/modules/lib/modules" / name
        need(path.is_file(), "required vendor module absent: " + name)
        vermagic = sh("modinfo", "-F", "vermagic", str(path))
        need(vermagic.startswith("5.10.269-"), name + " vermagic mismatch: " + vermagic)
        module_hashes[name] = sha(path.read_bytes())

    dist.mkdir(parents=True, exist_ok=True)
    name = "UN1CA-A16-E3099-UNRECONCILED-" + srczip.name
    out = dist / name
    need(not out.exists(), "refusing to overwrite " + str(out))
    with tempfile.TemporaryDirectory(dir=dist) as td:
        temporary = Path(td) / "output.zip"
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as writer:
            writer.writestr(BIN, binary, compress_type=zipfile.ZIP_STORED)
            writer.writestr(SCRIPT, ABORT.encode() + script,
                            compress_type=zipfile.ZIP_DEFLATED)
            for image in IMAGES:
                writer.writestr(f"files/{image}.img", images[image],
                                compress_type=zipfile.ZIP_STORED)
        with zipfile.ZipFile(temporary) as check:
            need(set(check.namelist()) == MEMBERS and check.testzip() is None,
                 "locked ZIP invalid")
            need(check.read(SCRIPT).startswith(ABORT.encode()),
                 "E3099 development safety abort absent")
            need(check.read(BIN) == binary, "updater binary changed")
            for image in IMAGES:
                need(check.read(f"files/{image}.img") == images[image],
                     image + " changed during packaging")
        temporary.replace(out)

    report = {
        "device": "SM-S901B", "android": 16, "rom": "UN1CA",
        "status": "HOST-ONLY_UNRECONCILED_E3099_NONFLASHABLE",
        "kernel_source": KERNEL_PIN, "ksunext_source": KSU_PIN,
        "ksunext_release": "v3.4.1",
        "upstream_zip_name": srczip.name,
        "quarantined_zip_name": name,
        "zip_sha256": sha(out.read_bytes()),
        "images": {k: {"bytes": len(v), "sha256": sha(v)} for k, v in images.items()},
        "compiled_vendor_modules_sha256": module_hashes,
        "vendor_dlkm_updated": False,
        "A16_GZH3_boot_chain_reconciled": False,
        "A16_board_pass": False,
    }
    (dist / "provenance.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (dist / "NOT_FOR_FLASH.txt").write_text(
        "DO NOT FLASH. HOST-ONLY UN1CA A16 ExtremeKRNL build output.\n"
        "The upstream vendor_boot is NOT reconciled with native GZH3 "
        "ERoFS/first-stage fstab/bootconfig.\n"
        "The ZIP's updater-script intentionally aborts with E3099 "
        "before any partition writes.\n"
        "It is NOT a KernelSU update for an installed UN1CA A16 ROM.\n"
        "Use existing scripts/r0s/reconcile_extremekrnl_gzh3_a16.py "
        "and package_extremekrnl_update_a16.py with verified signed "
        "A16 target-files before qualifying a flashable ZIP.\n"
        "Matching vendor_dlkm modules and ABI must also be verified.\n"
    )
    print("A16 KERNEL COMPILE + E3099-LOCKED ZIP HOST PACKAGE PASS")
    print("NO A16 GZH3 RECONCILIATION OR BOARD VALIDATION")
    print(out)
    print("SHA256=" + report["zip_sha256"])

if __name__ == "__main__":
    try:
        if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
            test()
        elif len(sys.argv) == 3:
            package(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
        else:
            raise RuntimeError("Usage: ci_hold_raw_kernel_zip.py --self-test | KERNEL_DIR DIST_DIR")
    except (RuntimeError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
