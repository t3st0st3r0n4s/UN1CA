#!/usr/bin/env python3
"""Prepare a kernel-only legacy TWRP updater ZIP for UN1CA A16 r0s.

TachyonOS A15's ExtremeKRNL ZIP has already been flashed successfully using
the user's existing TWRP. Reuse that established installation style, without
rebuilding or revalidating the A15 recovery or touching its source.

Unlike the upstream A16 ExtremeKRNL ZIP, carry the native GZH3-reconciled
boot/vendor_boot/dtbo *and* the matching vendor_dlkm as a block OTA. Reuse
UN1CA's already proven, statically linked update-binary and the same
block_image_update(map_partition(...)) semantics as its full OTA.

Do NOT call remove_all_groups or update_dynamic_partitions on a kernel-only
update: other installed A16 logical partitions must be preserved. This ZIP is
E3099 LOCKED and cannot currently flash anything; it is for HOST qualification
and a future **already-installed A16** kernel update, not for first A16 install.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "out/r0s_A16_GZH3_HOST_ONLY-target_files.zip"
OUTPUT = ROOT / "out/r0s_A16_ExtremeKRNL_KSUNext_v3.4.1_TWRP_E3099_LOCKED.zip"
E3099 = ('abort("E3099: UN1CA sixteen-r0s is under development and '
         'NOT qualified for flashing.");')
KERNEL_PIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU_PIN = "8f902aeb16033024143ae36cf711df902cf02fae"
KSU_APK_SHA = "f41778ee812512ae96bf53e7265114de5e0414bc5cb92397f49e1052d77da118"
BOOTS = ("vendor_boot", "dtbo", "boot")
CAPS = {"boot.img": 67_108_864, "vendor_boot.img": 33_554_432,
        "dtbo.img": 8_388_608}
MANIFEST = "KERNEL_UPDATE_MANIFEST.json"
NOTICE = "READ_ME_E3099_NOT_FLASHABLE.txt"
UPDATER = "META-INF/com/google/android/updater-script"
BINARY = "META-INF/com/google/android/update-binary"
DAT = "vendor_dlkm.new.dat.br"
TRANSFER = "vendor_dlkm.transfer.list"
PATCH = "vendor_dlkm.patch.dat"
PAYLOADS = set(CAPS) | {DAT, TRANSFER, PATCH}
EXPECTED = PAYLOADS | {MANIFEST, NOTICE, UPDATER, BINARY}
SCRIPT = (
    '# This is a kernel-only updater for a previously installed UN1CA A16 ROM.\n'
    '# Existing TWRP and updater proven for A15; A16 update paths unqualified.\n'
    'getprop("ro.boot.em.model") == "SM-S901B" || '
    'abort("E3004: This updater is only for SM-S901B.");\n'
    + E3099 + '\n'
    'ui_print("UN1CA A16 ExtremeKRNL / KernelSU Next kernel-only update");\n'
    '# No update_dynamic_partitions / remove_all_groups: preserve system etc.\n'
    'block_image_update(map_partition("vendor_dlkm"), '
    'package_extract_file("vendor_dlkm.transfer.list"), '
    '"vendor_dlkm.new.dat.br", "vendor_dlkm.patch.dat") || '
    'abort("E2001: vendor_dlkm kernel modules update failed.");\n'
    'package_extract_file("vendor_boot.img", "/dev/block/by-name/vendor_boot") || '
    'abort("E2002: vendor_boot update failed.");\n'
    'package_extract_file("dtbo.img", "/dev/block/by-name/dtbo") || '
    'abort("E2003: dtbo update failed.");\n'
    'package_extract_file("boot.img", "/dev/block/by-name/boot") || '
    'abort("E2004: boot update failed.");\n'
    'ui_print("Kernel-only update complete.");\n'
)
README = (
    "NOT FLASHABLE. The real update-binary is included but updater-script\n"
    "immediately aborts E3099 BEFORE EVERY partition-write operation.\n"
    "DO NOT REMOVE E3099 or attempt device installation.\n\n"
    "This is the native GZH3/UN1CA Android 16 ExtremeKRNL v2.5 +\n"
    "KernelSU Next v3.4.1 kernel-only maintenance package for an already\n"
    "installed A16 UN1CA r0s; NOT a first-install A15-to-A16 ROM update.\n"
    "It uses the existing TWRP's previously tested legacy updater launch,\n"
    "not a newly compiled/replaced TWRP.\n\n"
    "Partition operations after a future qualification and E3099 removal:\n"
    "  1. Block-update existing dynamic vendor_dlkm (modules, AVB, EROFS).\n"
    "  2. Write matched, signed vendor_boot/dtbo/boot by-name images.\n"
    "  3. Preserve system/product/vendor/odm, BL, CP, vbmeta, recovery,\n"
    "     userdata and existing dynamic partition group definitions.\n"
    "The update assumes the installed A16 vendor_dlkm logical partition\n"
    "already exists and its allocated size accepts the new EROFS image.\n"
    "Missing gates: installed-A16 identity check, dynamic mapping and\n"
    "size validation, AVB trust, bootloader/kernel runtime, rollback, and\n"
    "real-device A16 kernel-only update. Never use on TachyonOS A15.\n"
)


class Hold(RuntimeError):
    pass


def need(yes, reason):
    if not yes:
        raise Hold(reason)


def hash_stream(stream):
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(chunk)
    return h.hexdigest()


def sha(path):
    with path.open("rb") as f:
        return hash_stream(f)


def zip_hash(z, name):
    with z.open(name) as f:
        return hash_stream(f)


def pinned_input(source, expected_sha):
    need(re.fullmatch(r"[0-9a-f]{64}", expected_sha or ""),
         "pass the exact current target-files SHA256")
    need(source.is_file() and source.stat().st_size > 0, "target-files ZIP missing")
    need(sha(source) == expected_sha, "source target-files SHA256 mismatch")
    need(E3099 in (ROOT / "target/r0s/installer/assertions.edify").read_text(),
         "mandatory source E3099 missing")
    work = ROOT / "out/target/r0s/work_dir"
    need((work / "kernel/.r0s_extremekrnl_a16_integrated").is_file(),
         "reconciled A16 ExtremeKRNL not integrated")
    manager = work / "system/system/etc/unica/ksunext/manager_payload.bin"
    need(manager.is_file() and sha(manager) == KSU_APK_SHA,
         "A16 ROM has not embedded the matching KSU Manager v3.4.1")
    binary = ROOT / "prebuilts/bootable/deprecated-ota/updater"
    need(binary.is_file() and binary.stat().st_size > 0,
         "existing UN1CA legacy updater-binary missing")
    with zipfile.ZipFile(source) as z:
        names = z.namelist()
        for name, cap in CAPS.items():
            need(names.count(name) == 1 and z.getinfo(name).file_size == cap,
                 "AVB-signed boot-chain partition size mismatch: " + name)
        need(names.count("vendor_dlkm.img") == 1, "vendor_dlkm.img missing")
        need(names.count("unsparse_super_empty.img") == 1,
             "GZH3 dynamic metadata absent")
        need(z.testzip() is None, "source archive CRC failure")
    print("A16 KERNEL-ONLY TWRP UPDATER INPUT PASS — E3099 ACTIVE", flush=True)
    print("existing TWRP binary is not rechecked or modified", flush=True)
    print("target-files SHA256: " + expected_sha, flush=True)


def deep_audits(expected_sha):
    env = {**os.environ, "PATH": str(ROOT / "out/tools/bin")
           + os.pathsep + os.environ.get("PATH", "")}
    for name in ("audit_target_files_host.sh", "audit_packaged_kernel_modules.sh"):
        print("===== A16 TARGET-FILES AUDIT: " + name + " =====", flush=True)
        r = subprocess.run(["bash", str(ROOT / "scripts/r0s" / name),
                            str(SOURCE), expected_sha], env=env)
        need(r.returncode == 0, "A16 host audit failed: " + name)


def run_convert(img, scratch):
    out = scratch / "sdat"
    out.mkdir()
    map_file = scratch / "vendor_dlkm.map"
    tool = str(ROOT / "out/tools/bin/img2sdat")
    if not Path(tool).is_file():
        tool = shutil.which("img2sdat")
    need(tool, "img2sdat host tool missing")
    p = subprocess.run([tool, "-o", str(out), "--tgt-block-map",
                        str(map_file), str(img)],
                       capture_output=True, text=True)
    need(p.returncode == 0, "img2sdat failed: " + p.stderr[-1000:])
    newdat = out / "vendor_dlkm.new.dat"
    transfer = out / TRANSFER
    need(newdat.is_file() and newdat.stat().st_size > 0,
         "vendor_dlkm.new.dat not generated")
    need(transfer.is_file() and transfer.stat().st_size > 0,
         "vendor_dlkm transfer list not generated")
    brotli = str(ROOT / "out/tools/bin/brotli")
    if not Path(brotli).is_file():
        brotli = shutil.which("brotli")
    need(brotli, "brotli host tool missing")
    p = subprocess.run([brotli, "--quality=6", "--output=" + str(out / DAT),
                        str(newdat)], capture_output=True, text=True)
    need(p.returncode == 0 and (out / DAT).is_file(),
         "vendor_dlkm Brotli compression failed: " + p.stderr[-1000:])
    # Full UN1CA OTAs pass a patch.dat filename even for all-new dat payload.
    patch = out / PATCH
    if not patch.exists():
        patch.write_bytes(b"")
    need(patch.is_file(), "vendor_dlkm patch.dat absent")
    print("vendor_dlkm block update generated (no dynamic group recreation)")
    return out


def manifest_payload(blobs, expected_sha):
    recs = {}
    for name in (sorted(PAYLOADS) + [BINARY]):
        recs[name] = {"size": blobs[name].stat().st_size,
                      "sha256": sha(blobs[name])}
    return {
        "status": "HOST_ONLY_E3099_LOCKED",
        "device": "SM-S901B", "codename": "r0s", "android_api": 36,
        "firmware": "S901BXXSOGZH3",
        "kernel": "5.10.269-ExtremeKRNL-v2.5+",
        "kernel_source": KERNEL_PIN,
        "ksunext_version": "3.4.1", "ksunext_commit": KSU_PIN,
        "target_files_sha256": expected_sha,
        "type": "legacy_twrp_kernel_only_block_ota",
        "dynamic_operation": "block_image_update(map_partition(vendor_dlkm))",
        "dynamic_partition_group_changes": False,
        "boot_images": list(BOOTS),
        "first_install_supported": False,
        "recovery_replacement": False,
        "a16_board_qualified": False,
        "e3099_before_all_writes": True,
        "payload": recs,
    }


def archive_verify(path, source_sha=None):
    need(path.is_file() and path.stat().st_size > 0, "update archive missing")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and set(names) == EXPECTED,
             "unexpected or missing kernel updater ZIP entries")
        need(z.testzip() is None, "kernel-only ZIP CRC failure")
        code = z.read(UPDATER).decode()
        need(code == SCRIPT, "updater-script modified from pinned writer recipe")
        need(code.count(E3099) == 1, "E3099 missing or duplicated")
        operations = ("block_image_update(", "package_extract_file(")
        indices = [code.find(term) for term in operations]
        indices = [n for n in indices if n >= 0]
        # Ignore comments by testing the exact source recipe and its ordering.
        need(indices and code.find(E3099) < min(indices),
             "E3099 not before partition operations")
        active = [line for line in code.splitlines()
                  if not line.lstrip().startswith("#")]
        need(not any("remove_all_groups" in line or
                     "update_dynamic_partitions(" in line for line in active),
             "kernel-only updater must not alter installed super group")
        need(code.count('block_image_update(map_partition("vendor_dlkm")') == 1,
             "vendor_dlkm not updated exactly once")
        for p in BOOTS:
            need(code.count('package_extract_file("' + p +
                            '.img", "/dev/block/by-name/' + p + '")') == 1,
                 "boot chain not updated exactly once: " + p)
        need(z.read(NOTICE).decode() == README, "E3099 warning changed")
        info = json.loads(z.read(MANIFEST))
        need(info["status"] == "HOST_ONLY_E3099_LOCKED" and
             info["a16_board_qualified"] is False and
             info["e3099_before_all_writes"] is True and
             info["dynamic_partition_group_changes"] is False and
             info["first_install_supported"] is False,
             "manifest incorrectly promotes flashability")
        need(info["kernel_source"] == KERNEL_PIN and info["ksunext_commit"] == KSU_PIN,
             "kernel/KSU pin drift")
        if source_sha:
            need(info["target_files_sha256"] == source_sha,
                 "source target-files identity changed")
        for name, rec in info["payload"].items():
            need(name in names and z.getinfo(name).file_size == rec["size"] and
                 zip_hash(z, name) == rec["sha256"],
                 "archive payload hash mismatch: " + name)
    print("A16 KERNEL-ONLY TWRP UPDATE ZIP HOST VERIFY PASS — E3099 LOCKED")
    print("Real legacy updater present; only vendor_dlkm + 3 boot-chain images")
    print("No full ROM rebuild, recovery replacement, BL/CP or system writes")


def archive_build(expected_sha):
    need(not OUTPUT.exists(), "refusing to overwrite prior output: " + str(OUTPUT))
    pinned_input(SOURCE, expected_sha)
    deep_audits(expected_sha)
    need(not OUTPUT.exists(), "output appeared during host audits")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".r0s_ksu_kernel_update_",
                                     dir=OUTPUT.parent) as folder:
        scratch = Path(folder)
        with zipfile.ZipFile(SOURCE) as z:
            for name in CAPS:
                with z.open(name) as f, (scratch / name).open("wb") as w:
                    shutil.copyfileobj(f, w)
            with z.open("vendor_dlkm.img") as f, (scratch / "vendor_dlkm.img").open("wb") as w:
                shutil.copyfileobj(f, w)
        datdir = run_convert(scratch / "vendor_dlkm.img", scratch)
        staging = scratch / "update.zip"
        blobs = {name: scratch / name for name in CAPS}
        blobs[DAT] = datdir / DAT
        blobs[TRANSFER] = datdir / TRANSFER
        blobs[PATCH] = datdir / PATCH
        blobs[BINARY] = ROOT / "prebuilts/bootable/deprecated-ota/updater"
        with zipfile.ZipFile(staging, "w", allowZip64=True) as z:
            for name, source in sorted(blobs.items()):
                z.write(source, name, compress_type=zipfile.ZIP_STORED)
            z.writestr(UPDATER, SCRIPT)
            z.writestr(NOTICE, README)
            m = manifest_payload(blobs, expected_sha)
            z.writestr(MANIFEST, json.dumps(m, sort_keys=True, indent=2) + "\n")
        archive_verify(staging, expected_sha)
        need(not OUTPUT.exists(), "output appeared during assembly")
        staging.replace(OUTPUT)
    print("A16 KERNEL-ONLY TWRP UPDATER HOST PACKAGE PASS")
    print("output: " + str(OUTPUT))
    print("SHA256: " + sha(OUTPUT))
    print("E3099 LOCKED — NOT FLASHABLE; A16 BOARD DEFERRED")


def self_test():
    need(SCRIPT.count(E3099) == 1, "one-shot E3099 gate broken")
    # The marker is immediately after the device assert and before writes.
    need(SCRIPT.find(E3099) < SCRIPT.find("block_image_update("),
         "E3099 precedes OTA calls")
    need('block_image_update(map_partition("vendor_dlkm")' in SCRIPT,
         "vendor_dlkm update missing")
    lines = [s.strip() for s in SCRIPT.splitlines() if not s.lstrip().startswith("#")]
    need(not any("update_dynamic_partitions(" in s or "remove_all_groups" in s
                 for s in lines), "unsafe group reconstruction")
    need(len(CAPS) == 3 and len(KERNEL_PIN) == len(KSU_PIN) == 40,
         "boot partitions or pins changed")
    need(not any(("system.img" in s or "product.img" in s or "vendor.img" in s)
                 for s in lines), "kernel-only updater includes OS partition")
    print("A16 TWRP kernel-only updater self-test PASS (no device/host outputs)")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("self-test", "check", "build", "verify"))
    p.add_argument("sha256", nargs="?", help="target-files SHA256 for check/build")
    args = p.parse_args()
    if args.mode == "self-test":
        self_test()
    elif args.mode == "check":
        pinned_input(SOURCE, args.sha256)
    elif args.mode == "build":
        archive_build(args.sha256)
    else:
        archive_verify(OUTPUT)


if __name__ == "__main__":
    try:
        main()
    except (Hold, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print("A16 KERNEL-ONLY UPDATER HOLD: " + str(exc), file=sys.stderr)
        sys.exit(2)
