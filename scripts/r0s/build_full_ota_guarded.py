#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Guarded UN1CA SM-S901B GZH3 OTA packaging from retained target-files.

Default produces a development-locked E3099 ZIP. Explicit --installable
omits ONLY that exact abort in the generated updater, preserving the
SM-S901B device assertion and all payloads. Both are unqualified for
physical Android 16 boot; this script never accesses a device.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "out/r0s_A16_GZH3_HOST_ONLY-target_files.zip"
OUTPUT = ROOT / "out/UN1CA_r0s_A16_GZH3_E3099_BLOCKED_full_ota.zip"
INSTALLABLE_OUTPUT = ROOT / "out/UN1CA_r0s_A16_GZH3_INSTALLABLE_UNQUALIFIED.zip"
PIN_SHA256 = "4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a"
LOCK = ROOT / "target/r0s/installer/assertions.edify"
LOGICAL = ("system", "vendor", "product", "odm", "vendor_dlkm")
RAW = ("boot.img", "vendor_boot.img", "dtbo.img")
E3099 = 'abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");'
GIB = 1024 ** 3


class Blocked(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Blocked(reason)


def digest(path):
    hash_obj = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(2 * 1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def locked():
    require(LOCK.is_file() and E3099 in LOCK.read_text(),
            "source installer E3099 safety lock missing")


def check_ota(zpath, *, installable=False):
    """Check actual assembled updater ZIP, including no-write-before-abort."""
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        unique = set(names)
        require(len(unique) == len(names), "duplicate archive members")
        require(all(not n.startswith("/") and ".." not in n.split("/") and
                    "\\" not in n for n in names), "unsafe archive pathname")
        essential = {
            "META-INF/com/google/android/update-binary",
            "META-INF/com/google/android/updater-script",
            "dynamic_partitions_op_list",
            "unsparse_super_empty.img",
        } | set(RAW)
        for part in LOGICAL:
            essential.update((part + ".transfer.list", part + ".patch.dat"))
            require((part + ".new.dat.br" in unique) !=
                    (part + ".new.dat" in unique),
                    "missing/ambiguous OTA data payload: " + part)
        require(essential <= unique,
                "missing OTA components: " + repr(sorted(essential - unique)))
        forbidden = {
            "vbmeta.img", "recovery.img", "modem.img", "cp.img", "bl.img",
            "init_boot.img", "system_ext.img", "system_ext.new.dat",
            "system_ext.new.dat.br", "system_ext.transfer.list",
            "system_ext.patch.dat",
        }
        require(not (forbidden & unique),
                "OTA contains forbidden partitions: " +
                repr(sorted(forbidden & unique)))
        for name in ("META-INF/com/google/android/updater-script",
                     "dynamic_partitions_op_list"):
            require(z.getinfo(name).file_size <= 128 * 1024,
                    "oversized updater metadata: " + name)
        script = z.read("META-INF/com/google/android/updater-script").decode("utf-8")
        op = z.read("dynamic_partitions_op_list").decode("utf-8")
        assert_index = script.find(E3099)
        write_index = min((v for v in (
            script.find("update_dynamic_partitions("),
            script.find("block_image_update("),
            script.find("package_extract_file("),
        ) if v >= 0), default=-1)
        if installable:
            require(assert_index == -1 and "E3099:" not in script,
                    "installable ZIP still contains the E3099 development abort")
            model = 'getprop("ro.boot.em.model") == "SM-S901B"'
            require(model in script and
                    (write_index < 0 or script.find(model) < write_index),
                    "SM-S901B model assertion missing or after writes")
        else:
            require(assert_index >= 0 and
                    (write_index < 0 or assert_index < write_index),
                    "unconditional E3099 abort not before partition writes")
            require(script.count(E3099) == 1, "incorrect E3099 abort count")
        require("update_dynamic_partitions(" in script, "no dynamic partition command")
        require(script.count("block_image_update(") == 5, "not exactly five block updates")
        for p in LOGICAL:
            require('map_partition("' + p + '")' in script,
                    "updater missing partition mapping: " + p)
        for p in RAW:
            require('package_extract_file("' + p + '"' in script,
                    "missing raw image install: " + p)
        commands = [line.strip().split() for line in op.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        require(all(cmd for cmd in commands), "invalid op-list")
        require(commands[0] == ["remove_all_groups"], "OTA does not reset prior group")
        require(commands[1] == ["add_group", "group_basic", "11739856896"],
                "OTA group name/capacity differs")
        for cmd in commands[2:]:
            require(len(cmd) in (3,) and cmd[0] in ("add", "resize"),
                    "unknown OTA group operation: " + repr(cmd))
        added = [cmd[1] for cmd in commands if cmd[0] == "add"]
        resized = [cmd[1] for cmd in commands if cmd[0] == "resize"]
        require(len(added) == len(LOGICAL) and set(added) == set(LOGICAL) and
                len(resized) == len(LOGICAL) and set(resized) == set(LOGICAL),
                "logical add/resize set differs from five S901B partitions")
        for cmd in commands:
            if cmd[0] == "add":
                require(cmd[2] == "group_basic", "partition placed in wrong group")
            elif cmd[0] == "resize":
                require(cmd[2].isdigit() and int(cmd[2]) > 0,
                        "invalid resized logical partition bytes")
        for n in RAW:
            require(z.getinfo(n).file_size > 4096, "raw boot image unexpectedly small")
    print("UN1CA single-ZIP layout and " +
          ("INSTALLABLE/NO-E3099" if installable else "E3099-FIRST") +
          " updater checks PASS")
    print("Five logical partitions + boot/vendor_boot/dtbo; no BL, CP, recovery or vbmeta")
    print("STATIC ONLY: updater protocol, boot and TWRP on-device remain unqualified")


def check_source():
    locked()
    require(INPUT.is_file() and INPUT.stat().st_size > 1024 * 1024,
            "canonical GZH3 target-files ZIP missing")
    require(digest(INPUT) == PIN_SHA256, "target-files SHA-256 differs from host PASS")
    structural = ROOT / "scripts/r0s/check_target_files_zip.py"
    ret = subprocess.run([sys.executable, str(structural), str(INPUT)])
    require(ret.returncode == 0, "retained source structure check failed")
    with zipfile.ZipFile(INPUT) as z:
        i = z.getinfo
        logical_bytes = sum(i(p + ".img").file_size for p in LOGICAL)
        raw_bytes = sum(i(p).file_size for p in RAW)
        super_bytes = i("unsparse_super_empty.img").file_size
        # Builder: extract all, convert logical images to DAT, generate zip,
        # sign second ZIP. This is a conservative storage planning allowance.
        required = super_bytes + logical_bytes * 2 + raw_bytes + INPUT.stat().st_size * 2 + 6 * GIB
    free = shutil.disk_usage(OUTPUT.parent).free
    print("===== HOST-ONLY OTA CAPACITY GATE =====")
    print("existing_input_sha256=" + PIN_SHA256)
    print("disk_free_gib=" + str(round(free / GIB, 2)))
    print("planning_required_gib=" + str(round(required / GIB, 2)))
    print("planning budget includes extracted super and images, DAT conversion,")
    print("signing duplication, and 6 GiB reserve; not a strict peak bound")
    require(free >= required, "insufficient disk free for safe full OTA packaging")
    return required


def self_test():
    with tempfile.TemporaryDirectory() as td:
        file = Path(td) / "test.zip"
        ops = ("remove_all_groups\n"
               "add_group group_basic 11739856896\n" +
               "".join("add " + p + " group_basic\n" for p in LOGICAL) +
               "".join("resize " + p + " 4096\n" for p in LOGICAL))
        def make(valid=True):
            script = ('getprop("ro.boot.em.model") == "SM-S901B" || abort("E3004");\n' +
                      (E3099 + "\n" if valid else "") +
                      'assert(update_dynamic_partitions(package_extract_file("dynamic_partitions_op_list")));\n' +
                      "".join('block_image_update(map_partition("' + p +
                              '"), package_extract_file("' + p + '.transfer.list"), "' +
                              p + '.new.dat.br", "' + p + '.patch.dat");\n' for p in LOGICAL) +
                      "".join('package_extract_file("' + p +
                              '", "/dev/block/by-name/' + p.removesuffix(".img") +
                              '");\n' for p in RAW))
            with zipfile.ZipFile(file, "w") as z:
                z.writestr("META-INF/com/google/android/updater-script", script)
                z.writestr("META-INF/com/google/android/update-binary", b"bin")
                z.writestr("dynamic_partitions_op_list", ops)
                z.writestr("unsparse_super_empty.img", b"super")
                for p in LOGICAL:
                    for ext in ("transfer.list", "new.dat.br", "patch.dat"):
                        z.writestr(p + "." + ext, b"data")
                for p in RAW:
                    z.writestr(p, bytes(4097))
        make()
        check_ota(file)
        try:
            check_ota(file, installable=True)
        except Blocked:
            pass
        else:
            raise AssertionError("locked installer wrongly accepted as installable")
        make(False)
        check_ota(file, installable=True)
        try:
            check_ota(file)
        except Blocked:
            pass
        else:
            raise AssertionError("unlocked installer fixture erroneously passed")
    print("S901B full OTA synthetic positive/negative tests PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build", action="store_true", help="assemble an OTA ZIP")
    p.add_argument("--installable", action="store_true",
                   help="explicitly omit E3099 in the generated r0s updater")
    p.add_argument("--verify", action="store_true",
                   help="verify selected output ZIP without building")
    p.add_argument("--self-test", action="store_true", help="synthetic CI only")
    args = p.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        output = INSTALLABLE_OUTPUT if args.installable else OUTPUT
        if args.verify:
            require(output.is_file(), "selected OTA output is missing")
            check_ota(output, installable=args.installable)
            unzip = shutil.which("unzip")
            require(unzip is not None, "unzip CLI required for ZIP CRC")
            require(subprocess.run([unzip, "-tq", str(output)],
                                   stdout=subprocess.DEVNULL).returncode == 0,
                    "OTA ZIP CRC failed")
            print("OTA_SHA256=" + digest(output))
            print("OTA_BYTES=" + str(output.stat().st_size))
            return 0
        require(not output.exists(), "output already exists; never overwrite")
        check_source()
        if not args.build:
            print("PRECHECK PASS; --build assembles the selected ZIP without ROM rebuild")
            print("MODE=" + ("INSTALLABLE_UNQUALIFIED" if args.installable else "E3099_LOCKED"))
            return 0
        partial = output.with_name(output.stem + ".partial.zip")
        require(not partial.exists(), "partial output exists; no overwrite")
        command = ("set -eo pipefail; "
                   "source ./buildenv.sh r0s >/dev/null; "
                   '[[ "$TARGET_CODENAME" == "r0s" && "$SOURCE_PLATFORM_SDK_VERSION" == "36" ]] || exit 2; '
                   "scripts/build_flashable_zip.sh --output \"$1\" \"$2\"")
        print("===== UPSTREAM UN1CA FULL OTA BUILDER (NO MAKE_ROM) =====", flush=True)
        try:
            env = dict(os.environ)
            if args.installable:
                env["UN1CA_R0S_INSTALLABLE_OTA"] = "1"
            else:
                env.pop("UN1CA_R0S_INSTALLABLE_OTA", None)
            run = subprocess.run(["bash", "-c", command, "build-full-ota",
                                  str(partial), str(INPUT)], cwd=ROOT, env=env)
            require(run.returncode == 0, "upstream full OTA generation failed")
            require(partial.is_file(), "upstream builder produced no ZIP")
            check_ota(partial, installable=args.installable)
            unzip = shutil.which("unzip")
            require(unzip is not None, "unzip CLI needed for full ZIP CRC")
            check = subprocess.run([unzip, "-tq", str(partial)],
                                   stdout=subprocess.DEVNULL)
            require(check.returncode == 0, "full OTA ZIP CRC check failed")
            # Guard persisted through build and sign.
            locked()
            require(not output.exists(), "output appeared during build; refusing replace")
            os.replace(partial, output)
        finally:
            if partial.is_file():
                partial.unlink()
        print("HOST_OTA_SHA256=" + digest(output))
        print("HOST_OTA_BYTES=" + str(output.stat().st_size))
        print("FULL OTA PACKAGE COMPLETE; " +
              ("INSTALLABLE BUT A16 BOOT/ROLLBACK UNQUALIFIED"
               if args.installable else "E3099 ACTIVE; DO NOT FLASH"))
        return 0
    except (Blocked, OSError, ValueError, zipfile.BadZipFile, UnicodeError) as exc:
        print("r0s FULL OTA BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
