#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Inspect existing TachyonOS r0s recovery ZIPs for a reversible A16 route.

Read-only; verifies archive structure, never unpacks payloads or flashes.
"""
from pathlib import Path
import argparse
import re
import sys
import zipfile

LOGICAL = ("system", "vendor", "product", "odm", "vendor_dlkm")
RAW = ("boot.img", "vendor_boot.img", "dtbo.img")
META = (
    "META-INF/com/google/android/updater-script",
    "META-INF/com/google/android/update-binary",
    "dynamic_partitions_op_list",
)


def inspect(zpath):
    issues = []
    with zipfile.ZipFile(zpath, allowZip64=True) as z:
        names = set(z.namelist())
        required = set(META) | set(RAW)
        for part in LOGICAL:
            required.add(part + ".transfer.list")
            required.add(part + ".new.dat.br")
        missing = sorted(required - names)
        if missing:
            issues.append("missing=" + ",".join(missing))
        unwanted = sorted(x for x in names if x in (
            "recovery.img", "vbmeta.img", "init_boot.img", "modem.img",
            "bl.img", "cp.img", "system_ext.transfer.list",
            "system_ext.new.dat.br"))
        if unwanted:
            issues.append("unwanted=" + ",".join(unwanted))
        if all(x in names for x in META):
            for item in META:
                if z.getinfo(item).file_size > 256 * 1024:
                    issues.append("oversized_metadata=" + item)
            if not any(x.startswith("oversized_metadata") for x in issues):
                script = z.read(META[0]).decode("utf-8", errors="replace")
                op = z.read(META[2]).decode("utf-8", errors="replace")
                if ("update_dynamic_partitions(" not in script or
                        "block_image_update(" not in script):
                    issues.append("missing_legacy_block_ota_ops")
                if 'getprop("ro.bootloader")' not in script:
                    issues.append("missing_firmware_compat_assertion")
                if "FYI3" not in script:
                    issues.append("FYI3_assertion_not_explicit")
                if "remove_all_groups" not in op:
                    issues.append("missing_dynamic_group_reset")
                adds = {
                    line.split()[1] for line in op.splitlines()
                    if re.fullmatch(r"add\s+\w+\s+\w+", line.strip())
                }
                if adds != set(LOGICAL):
                    issues.append("unexpected_logical_partition_set=" +
                                  ",".join(sorted(adds)))
        # ZIP member test is intentionally not run: large data need no copy/decompression.
    return issues


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", nargs="*", type=Path,
                   help="TachyonOS recovery ZIP(s); omit to auto-search TachyonOS out/")
    p.add_argument("--tachyon-root", type=Path,
                   default=Path.home() / "android/tachyonos_s901b")
    opt = p.parse_args()
    if opt.zip:
        candidates = opt.zip
    else:
        out = opt.tachyon_root.expanduser() / "out"
        candidates = sorted(out.glob("TachyonOS_*_r0s*.zip"))
    if not candidates:
        print("ROLLBACK_ARCHIVE_NOT_FOUND: provide path to existing FYI3 TachyonOS ZIP")
        return 2
    ok = 0
    for file in candidates:
        if not file.is_file():
            print("BLOCKED " + str(file) + ": not a regular file")
            continue
        try:
            defects = inspect(file)
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
            defects = ["zip_read_error=" + str(exc)]
        print("===== " + file.name + " =====")
        print("path=" + str(file.resolve()))
        print("bytes=" + str(file.stat().st_size))
        if defects:
            print("ROLLBACK_ZIP_STATIC=BLOCKED " + "; ".join(defects))
        else:
            print("ROLLBACK_ZIP_STATIC=PASS (5 logical + boot/vendor_boot/dtbo)")
            ok += 1
    print("eligible_archive_count=" + str(ok))
    print("STATIC ONLY: not proof of decrypt, board boot or no-data-loss rollback.")
    print("Existing TWRP, protected EFS backups, and A15 userdata restore remain separate.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
