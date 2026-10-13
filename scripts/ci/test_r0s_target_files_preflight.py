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
    lock = root / "target/r0s/installer/assertions.edify"
    fw.mkdir(parents=True)
    work.mkdir(parents=True)
    lock.parent.mkdir(parents=True)
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
        "ro.build.version.sdk=36\nro.product.device=r0s\nro.unica.device=r0s\n")
    for part in gate.PARTITIONS:
        (work / part).mkdir(exist_ok=True)
        (work / "configs" / ("file_context-" + part)).write_text("fixture\n")
        (work / "configs" / ("fs_config-" + part)).write_text("fixture\n")
    for part in ("boot", "vendor_boot", "dtbo"):
        (work / "kernel" / (part + ".img")).write_bytes(b"fixture")
    lock.write_text('abort("E3099: native A16 NOT qualified for flashing.");\n')
    return fw, work, lock


def run():
    count = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        fw, work, lock = fixture(root)

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
        lock.write_text("ui_print('UNSAFE');\n")
        blocked()
        lock.write_text('abort("E3099: native A16 NOT qualified for flashing.");\n')
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
    assert count == 8, count
    print(f"r0s target-files preflight fixtures PASS ({count} cases)")


if __name__ == "__main__":
    run()
