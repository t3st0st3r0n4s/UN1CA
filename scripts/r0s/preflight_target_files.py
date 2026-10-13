#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only disk and input preflight for the native GZH3 target-files builder."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys

FOTA = "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"
PARTITIONS = ("system", "odm", "product", "vendor", "vendor_dlkm")
SUPER_BYTES = 11_744_051_200
GROUP_BYTES = 11_739_856_896
RESERVE_BYTES = 7 * 1024 ** 3


class Blocked(Exception):
    pass


def require(value, reason):
    if not value:
        raise Blocked(reason)


def metadata(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            require(k not in result, "duplicate metadata property: " + k)
            result[k] = v.strip()
    return result


def occupied_bytes(path):
    raw = subprocess.check_output(("du", "-sb", "--", str(path)), text=True)
    return int(raw.split()[0])


def budget_bytes(work_bytes):
    # Planning allowance: 1x uncompressed super-empty, ~1x partition images,
    # ~1x ZIP, plus 7GiB reserve. This is an estimate, not a peak bound.
    return SUPER_BYTES + work_bytes * 2 + RESERVE_BYTES


def validate(root, free_bytes=None):
    fw = root / "out/fw/SM-S901B_EUX"
    work = root / "out/target/r0s/work_dir"
    output_dir = root / "out"
    lock = root / "target/r0s/installer/assertions.edify"
    require(lock.is_file(), "missing installer abort")
    require(re.search(r'^\s*abort\("E3099:.*NOT qualified for flashing',
                      lock.read_text(), re.M), "E3099 lock was removed")
    require((fw / ".extracted").is_file() and
            (fw / ".extracted").read_text().strip() == FOTA,
            "wrong/missing native GZH3 extraction")
    require((work / ".completed").is_file() and
            re.fullmatch("[0-9a-f]{40}", (work / ".completed").read_text().strip()),
            "missing/invalid completed workdir hash")
    meta_path = fw / "os_partitions_metadata.txt"
    require(meta_path.is_file(), "missing native super metadata")
    meta = metadata(meta_path)
    for key, expected in (
        ("super_partition_group", "group_basic"),
        ("super_partition_size", str(SUPER_BYTES)),
        ("super_group_basic_group_size", str(GROUP_BYTES)),
    ):
        require(meta.get(key) == expected, "stock super metadata differs: " + key)
    native_parts = meta.get("super_group_basic_partition_list", "").split()
    require(len(native_parts) == 5 and set(native_parts) == set(PARTITIONS),
            "stock GZH3 super partition set differs")
    actual = {entry.name for entry in work.iterdir()
              if entry.is_dir() and entry.name not in ("configs", "kernel")}
    require(actual == set(PARTITIONS), "workdir partition set differs")
    require((work / "system/system/system_ext").is_dir(),
            "native embedded system_ext missing")
    for part in PARTITIONS:
        for prefix in ("file_context-", "fs_config-"):
            require((work / "configs" / (prefix + part)).is_file(),
                    "workdir metadata missing: " + prefix + part)
    for name in ("boot", "vendor_boot", "dtbo"):
        require((work / "kernel" / (name + ".img")).is_file(),
                "workdir boot image missing: " + name)
    props_file = work / "system/system/build.prop"
    require(props_file.is_file(), "workdir build.prop missing")
    props = metadata(props_file)
    for key, value in (
        ("ro.build.version.sdk", "36"),
        ("ro.product.device", "r0s"),
        ("ro.unica.device", "r0s"),
    ):
        require(props.get(key) == value, "workdir property mismatch: " + key)
    require(output_dir.is_dir(), "out/ directory missing")
    tempdir = root / "out/target/r0s/tmp"
    require(not tempdir.exists() or
            (tempdir.is_dir() and not any(tempdir.iterdir())),
            "builder temp directory contains existing data: " + str(tempdir))
    work_bytes = sum(occupied_bytes(work / p) for p in PARTITIONS)
    require(work_bytes > 0, "empty workdir partition tree")
    minimum = budget_bytes(work_bytes)
    if free_bytes is None:
        free_bytes = shutil.disk_usage(output_dir).free
    require(free_bytes >= minimum,
            "insufficient capacity: available=" + str(free_bytes) +
            " planning_budget=" + str(minimum))
    return work_bytes, minimum, free_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        work_bytes, minimum, free_bytes = validate(args.root.resolve())
    except (Blocked, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("r0s TARGET-FILES PREFLIGHT BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print("NATIVE GZH3 TARGET-FILES INPUT/CAPACITY PRECHECK PASS")
    print(f"workdir_partition_bytes={work_bytes}")
    print(f"super_empty_worst_case_bytes={SUPER_BYTES}")
    print(f"minimum_free_budget_bytes={minimum}")
    print(f"available_bytes={free_bytes}")
    print("Budget: full-sized super-empty + 2x partition tree + 7GiB reserve.")
    print("Peak is an estimate, not a bound; monitor disk during packaging.")
    print("Read-only: no images, target-files or OTA built; E3099 active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
