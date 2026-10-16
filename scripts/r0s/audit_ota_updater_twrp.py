#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only ABI/symbol check of the ACTUAL UN1CA OTA updater vs FYI3 TWRP.

Cannot prove runtime execution, dm mapping or GZH3 boot on FYI3 firmware.
Never executes update-binary, writes a partition or changes the phone.
"""
import argparse
import gzip
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
from build_full_ota_guarded import native_rom_output, check_ota
TWRP_PATH = Path.home() / "android/S22-ROM/S901B_twrp_logo_vbmeta.tar"
TWRP_SHA = "f82b9612d92786971609895facb703906744d9a617e673f1cd148e671735d830"
UPDATER_NAME = "META-INF/com/google/android/update-binary"
SCRIPT_NAME = "META-INF/com/google/android/updater-script"
EXPECTED_FUNCTIONS = ("update_dynamic_partitions", "block_image_update", "map_partition")


class Blocked(Exception):
    pass


def require(yes, why):
    if not yes:
        raise Blocked(why)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def elf_metadata(header, program, dynamic):
    require(re.search(r"Class:\s+ELF64\b", header), "updater is not ELF64")
    require(re.search(r"Machine:\s+AArch64\b", header), "updater is not AArch64")
    needed = sorted(set(re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", dynamic)))
    interpreter = re.search(r"Requesting program interpreter:\s*([^\]]+)\]", program)
    return needed, interpreter.group(1) if interpreter else ""


def source_gate(zipfile_path):
    require(zipfile_path.is_file(), "missing existing full OTA ZIP")
    check_ota(zipfile_path)
    with zipfile.ZipFile(zipfile_path) as z:
        all_names = z.namelist()
        require(len(all_names) == len(set(all_names)), "duplicate ZIP member")
        for name in (UPDATER_NAME, SCRIPT_NAME):
            require(name in all_names and 0 < z.getinfo(name).file_size < 64 * 1024 * 1024,
                    "required bounded updater member absent: " + name)
        edify = z.read(SCRIPT_NAME).decode("utf-8")
        return z.read(UPDATER_NAME)


def load_twrp_ramdisk(tar, root):
    require(tar.is_file() and sha(tar) == TWRP_SHA,
            "existing S901B TWRP TAR not present or differs from pinned candidate")
    with tarfile.open(tar, "r:*") as tf:
        entries = [m for m in tf.getmembers() if m.name == "recovery.img"]
        require(len(entries) == 1 and entries[0].isfile()
                and 0 < entries[0].size <= 100_663_296,
                "TWRP archive does not contain one bounded recovery.img")
        member = tf.extractfile(entries[0])
        require(member is not None, "TWRP recovery image unreadable")
        recovery = root / "recovery.img"
        with member, recovery.open("wb") as dest:
            shutil.copyfileobj(member, dest)
    unpacker = ROOT / "out/tools/bin/unpack_bootimg"
    binary = str(unpacker) if unpacker.is_file() else shutil.which("unpack_bootimg")
    require(binary, "missing unpack_bootimg host tool")
    out = root / "unpacked"
    out.mkdir()
    proc = subprocess.run([binary, "--boot_img", str(recovery), "--out", str(out)],
                          capture_output=True)
    require(proc.returncode == 0, "could not unpack pinned TWRP recovery image")
    raw = out / "ramdisk"
    require(raw.is_file() and raw.stat().st_size < 100_663_296,
            "TWRP ramdisk absent/oversized")
    expanded = gzip.decompress(raw.read_bytes())
    require(len(expanded) <= 256 * 1024 * 1024, "TWRP cpio expanded beyond bound")
    spec = importlib.util.spec_from_file_location(
        "r0s_recovery_cpio", ROOT / "scripts/r0s/audit_recovery_runtime_abi.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper.parse_newc(expanded)


def check_files(records, needed, interp):
    basenames = {
        key.rsplit("/", 1)[-1]
        for key, (mode, _) in records.items()
        if stat.S_ISREG(mode) or stat.S_ISLNK(mode)
    }
    missing = sorted(lib for lib in needed if lib not in basenames)
    # Interpreter should be part of recovery ramdisk when the updater is dynamic.
    interp_present = not interp or interp.lstrip("/") in records
    return missing, interp_present


def self_test():
    header = "Class: ELF64\nMachine: AArch64\n"
    segment = "[Requesting program interpreter: /system/bin/linker64]\n"
    dynamic = "0x0001 (NEEDED) Shared library: [libc.so]\n"
    deps, interp = elf_metadata(header, segment, dynamic)
    assert deps == ["libc.so"] and interp == "/system/bin/linker64"
    assert check_files({"system/lib64/libc.so": (stat.S_IFREG, b""),
                        "system/bin/linker64": (stat.S_IFREG, b"")}, deps, interp) == ([], True)
    assert check_files({}, deps, interp) == (["libc.so"], False)
    try:
        elf_metadata(header.replace("AArch64", "Advanced Micro Devices X86-64"),
                     segment, dynamic)
    except Blocked:
        pass
    else:
        raise AssertionError("wrong ELF architecture accepted")
    print("S901B locked-OTA updater/TWRP ABI synthetic tests PASS (4 cases)")


def audit(zip_path, twrp_path):
    for cmd in ("readelf", "strings"):
        require(shutil.which(cmd), "missing required host executable: " + cmd)
    payload = source_gate(zip_path)
    original = ROOT / "prebuilts/bootable/deprecated-ota/updater"
    require(original.is_file(), "upstream UN1CA OTA updater absent")
    require(hashlib.sha256(payload).hexdigest() == sha(original),
            "actual ZIP updater differs from original UN1CA prebuilt")
    print("ACTUAL OTA SHA256=" + hashlib.sha256(payload).hexdigest())
    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        exe = tmp / "updater"
        exe.write_bytes(payload)
        def call(*args):
            result = subprocess.run(args, capture_output=True, text=True)
            require(result.returncode == 0, "host ELF inspection failed: " + args[0])
            return result.stdout
        head = call("readelf", "-h", str(exe))
        programs = call("readelf", "-l", str(exe))
        dyn = subprocess.run(["readelf", "-d", str(exe)], capture_output=True, text=True)
        require(dyn.returncode == 0, "updater ELF dynamic section unreadable")
        needed, interp = elf_metadata(head, programs, dyn.stdout)
        hints = call("strings", "-a", str(exe))
        found = [s for s in EXPECTED_FUNCTIONS if s in hints]
        print("updater_elf=ELF64/AArch64")
        print("updater_interpreter=" + (interp or "none"))
        print("updater_direct_libraries=" + (",".join(needed) if needed else "none (static/self-contained)"))
        print("updater_edify_symbol_hints=" + ",".join(found))
        if set(found) != set(EXPECTED_FUNCTIONS):
            print("WARNING: absent function-name strings do not alone disprove support")
        records = load_twrp_ramdisk(twrp_path, tmp)
        missing, interp_found = check_files(records, needed, interp)
        print("TWRP_OTA_LINKER_PATH_PRESENT=" + str(interp_found).lower())
        print("TWRP_MISSING_DIRECT_LIB_NAMES=" + (",".join(missing) if missing else "none"))
        if missing or not interp_found:
            print("TWRP RAMDISK DEPENDENCY GAP — may need verified external mounts/new recovery")
        else:
            print("TWRP DIRECT ABI FILE INVENTORY PASS (static presence only)")
    print("NO BL/CP/RECOVERY WRITES BY THIS AUDIT")
    print("UPDATE-BINARY EXECUTION / DYNAMIC PARTITION IO / BOARD STILL UNVERIFIED")
    print("NO FLASH / NO REBOOT / NO DEVICE CHANGES")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--zip", type=Path, help="existing full UN1CA ROM ZIP")
    p.add_argument("--twrp", type=Path, default=TWRP_PATH)
    args = p.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            audit((args.zip or native_rom_output()).expanduser(), args.twrp.expanduser())
    except (Blocked, OSError, RuntimeError, ValueError, zipfile.BadZipFile,
            tarfile.TarError, EOFError) as exc:
        print("S901B OTA UPDATER/TWRP INSPECTION BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
