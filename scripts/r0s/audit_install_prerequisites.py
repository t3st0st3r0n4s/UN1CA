#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only FYI3 -> GZH3 ROM write-set and live BL/CP snapshot. NO FLASH."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PIN = "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"
LOGICAL = ("system", "vendor", "product", "odm", "vendor_dlkm")
BOOT = ("boot.img", "vendor_boot.img", "dtbo.img")
PROPERTIES = (
    "ro.product.device", "ro.product.model", "ro.build.version.sdk",
    "ro.build.PDA", "ro.bootloader", "ro.boot.bootloader",
    "gsm.version.baseband", "ro.boot.flash.locked",
    "ro.boot.vbmeta.device_state", "ro.boot.verifiedbootstate",
    "ro.boot.other.locked",
)


class Blocked(Exception):
    pass


def require(condition, why):
    if not condition:
        raise Blocked(why)


def revision(name):
    m = re.fullmatch(r"S901BXX[SU]([1-9A-Z])[A-Z0-9]{4}", name or "")
    if not m:
        return None
    c = m.group(1)
    return int(c) if c.isdigit() else ord(c) - ord("A") + 10


def self_test():
    assert revision("S901BXXSIFYI3") == 18
    assert revision("S901BXXSOGZH3") == 24
    assert revision("S901BXXS9FYI3") == 9
    assert revision("S901BXXUAFYI3") == 10
    assert revision("S901BXXSIFYI3-other") is None
    assert revision("G991BXXSJHZC2") is None
    assert revision("") is None
    print("r0s Samsung FYI3/GZH3 rollback parsing: 7 synthetic tests PASS")


def host_gate():
    extracted = ROOT / "out/fw/SM-S901B_EUX/.extracted"
    require(extracted.is_file() and extracted.read_text().strip() == PIN,
            "extracted GZH3 marker incorrect or missing")
    source = ROOT / "out/r0s_A16_GZH3_HOST_ONLY-target_files.zip"
    require(source.is_file(), "HOST_ONLY target-files ZIP missing")
    with zipfile.ZipFile(source) as z:
        members = set(z.namelist())
        intended = {x + ".img" for x in LOGICAL} | set(BOOT)
        actual = {n for n in members if n.endswith(".img") and "/" not in n
                  and n != "unsparse_super_empty.img"}
        require(actual == intended, "unexpected target-files partition image set: "
                + str(sorted(actual ^ intended)))
        meta = dict(line.split("=", 1)
                    for line in z.read("build_info.txt").decode().splitlines()
                    if "=" in line)
        require(meta.get("device") == "r0s" and
                meta.get("use_dynamic_partitions") == "true" and
                meta.get("super_partition_size") == "11744051200" and
                meta.get("super_partition_group") == "group_basic" and
                meta.get("super_group_basic_group_size") == "11739856896",
                "package build-info does not match GZH3 geometry")
    print("PACKAGE_HOST_GATE=PASS")
    print("GZH3_LOGICAL_IMAGES=" + ",".join(LOGICAL))
    print("GZH3_BOOT_IMAGES=" + ",".join(BOOT))
    print("NOT_PACKAGED=BL,CP,vbmeta,recovery,init_boot,userdata,metadata")
    print("BL_RP_FROM_FYI3=18 BL_RP_GZH3=24 RP_INCREASE=6")
    print("FULL_OTA_REQUIRES_ARTIFACT_VERIFICATION")


def device_gate():
    p = subprocess.run(["adb", "devices"], text=True, capture_output=True,
                       timeout=15)
    require(p.returncode == 0, "ADB unavailable")
    connected = [line for line in p.stdout.splitlines()
                 if len(line.split()) == 2 and line.split()[1] == "device"]
    require(len(connected) == 1, "require exactly one online ADB device")
    # Fixed allowlist: no unique identifiers, IMEI, serial, accounts or root.
    probe = "for k in " + " ".join(PROPERTIES) + (
        '; do printf "%s=" "$k"; getprop "$k"; done; '
        'for p in boot vendor_boot dtbo recovery vbmeta super; do '
        'if [ -e "/dev/block/by-name/$p" ]; then echo "block_$p=present"; '
        'else echo "block_$p=not_visible"; fi; done'
    )
    r = subprocess.run(["adb", "shell", probe], text=True, capture_output=True,
                       timeout=40)
    require(r.returncode == 0, "ADB read-only getprop probe failed")
    props = dict(line.split("=", 1) for line in r.stdout.replace("\r", "").splitlines()
                 if "=" in line)
    require(props.get("ro.product.device") == "r0s", "ADB target not r0s")
    require(props.get("ro.product.model", "").startswith("SM-S901B"),
            "ADB model not SM-S901B")
    print("===== LIVE S901B BASELINE (READ-ONLY) =====")
    for key in PROPERTIES:
        print(key + "=" + (props.get(key) or "UNAVAILABLE"))
    for name in ("boot", "vendor_boot", "dtbo", "recovery", "vbmeta", "super"):
        print("partition_" + name + "=" + props.get("block_" + name, "UNAVAILABLE"))
    actual = props.get("ro.bootloader") or props.get("ro.boot.bootloader", "")
    rp = revision(actual)
    print("LIVE_BOOTLOADER_RP=" + (str(rp) if rp is not None else "UNKNOWN"))
    lock = props.get("ro.boot.flash.locked")
    state = props.get("ro.boot.vbmeta.device_state")
    if lock == "1" or state == "locked":
        print("UNLOCK_INDICATOR=LOCKED_OR_CONFLICT; BLOCK")
    elif lock == "0" or state == "unlocked":
        print("UNLOCK_INDICATOR=UNLOCKED; CONFIRM_IN_DOWNLOAD_MODE")
    else:
        print("UNLOCK_INDICATOR=UNKNOWN; CONFIRM_IN_DOWNLOAD_MODE")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--host-only", action="store_true")
    opt = ap.parse_args()
    try:
        if opt.self_test:
            self_test()
            return 0
        host_gate()
        if not opt.host_only:
            device_gate()
        print("GATE_BL_A15_TO_GZH3_BOOT=UNPROVEN")
        print("GATE_BL_UPGRADE_UNLOCK_SURVIVAL=UNPROVEN")
        print("GATE_CP_TO_GZH3_RIL=UNPROVEN")
        print("GATE_VBMETA_MIXED_TRUST=UNPROVEN")
        print("GATE_TWRP_BLOCK_OTA=UNPROVEN")
        print("GATE_DATA_FORMAT=REQUIRED_ONLY_AFTER_ALL_OTHER_GATES")
        print("BOARD_QUALIFICATION=DEFERRED; NO_PARTITIONS_WRITTEN")
        return 0
    except (Blocked, OSError, ValueError, zipfile.BadZipFile,
            subprocess.TimeoutExpired) as exc:
        print("r0s INSTALLATION BASELINE BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
