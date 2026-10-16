#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic validation of guarded target-files inputs and capacity."""
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "r0s_capacity", ROOT / "scripts/r0s/preflight_target_files.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixture(root):
    fw = root / "out/fw/SM-S901B_EUX"
    work = root / "out/target/r0s/work_dir"
    fw.mkdir(parents=True)
    work.mkdir(parents=True)
    (fw / ".extracted").write_text(gate.FOTA)
    (fw / "os_partitions_metadata.txt").write_text(
        "super_partition_group=group_basic\n"
        "super_partition_size=11744051200\n"
        "super_group_basic_group_size=11739856896\n"
        "super_group_basic_partition_list=system odm product vendor vendor_dlkm\n")
    (work / ".completed").write_text("a" * 40)
    (work / "configs").mkdir()
    (work / "kernel").mkdir()
    (work / "system/system/system_ext").mkdir(parents=True)
    (work / "system/system/build.prop").write_text(
        "ro.build.version.sdk=36\nro.product.device=r0s\nro.unica.device=r0s\n"
        "ro.kernel.qemu=0\nro.kernel.qemu=0\n")
    for part in gate.PARTITIONS:
        (work / part).mkdir(exist_ok=True)
        (work / "configs" / ("file_context-" + part)).write_text("fixture\n")
        (work / "configs" / ("fs_config-" + part)).write_text("fixture\n")
    for part in ("boot", "vendor_boot", "dtbo"):
        (work / "kernel" / (part + ".img")).write_bytes(b"fixture")
    return fw, work


def run():
    count = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        fw, work = fixture(root)

        def passed():
            nonlocal count
            gate.validate(root, free_bytes=100 * 1024 ** 3)
            count += 1

        def blocked(free=100 * 1024 ** 3):
            nonlocal count
            try:
                gate.validate(root, free_bytes=free)
            except gate.Blocked:
                count += 1
                return
            raise AssertionError("invalid capacity/firmware input accepted")

        passed()
        blocked(free=1000)
        (fw / ".extracted").write_text("S901BOTHER/S901BOTHER/S901BOTHER")
        blocked()
        (fw / ".extracted").write_text(gate.FOTA)
        (work / "system/system/build.prop").write_text("ro.build.version.sdk=35\n")
        blocked()
        (work / "system/system/build.prop").write_text(
            "ro.build.version.sdk=36\nro.product.device=r0s\nro.unica.device=r0s\n")
        (work / "system_ext").mkdir()
        blocked()
        (work / "system_ext").rmdir()
        tempdir = root / "out/target/r0s/tmp"
        tempdir.mkdir()
        (tempdir / "valuable.bin").write_bytes(b"do not delete")
        blocked()
        (tempdir / "valuable.bin").unlink()
        passed()

        # Non-identity duplicates in Android build.prop are permitted, but
        # duplicated SDK/device identity fields must always be rejected.
        props_file = work / "system/system/build.prop"
        normal_props = props_file.read_text()
        props_file.write_text(normal_props + "ro.product.device=r0s\n")
        blocked()
        props_file.write_text(normal_props)

        # Native dynamic-partition metadata must remain strictly unique.
        super_meta_file = fw / "os_partitions_metadata.txt"
        normal_meta = super_meta_file.read_text()
        super_meta_file.write_text(normal_meta + "super_partition_size=11744051200\n")
        blocked()
        super_meta_file.write_text(normal_meta)
        passed()
    assert count == 10, count
    print(f"r0s target-files preflight fixtures PASS ({count} cases)")


if __name__ == "__main__":
    run()
