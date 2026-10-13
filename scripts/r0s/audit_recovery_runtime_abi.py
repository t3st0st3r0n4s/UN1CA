#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only stock GZH3 vs existing S901B TWRP recovery ELF dependency inventory.

Parses ramdisk cpio archives in memory: no files from the ramdisk are installed.
Direct NEEDED libraries in a ramdisk are not proof of runtime ABI compatibility.
"""
import argparse
import gzip
import hashlib
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GZH3 = "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"
STOCK_SHA = "b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688"
TWRP_SHA = "f82b9612d92786971609895facb703906744d9a617e673f1cd148e671735d830"
MAX_UNPACKED = 350 * 1024 * 1024


class Blocked(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_newc(payload):
    """Parse Android newc/CRC cpio into path -> (mode, memoryview)."""
    pos, records = 0, {}
    for _ in range(16000):
        require(pos + 110 <= len(payload), "truncated cpio header")
        header = payload[pos:pos+110]
        require(header[:6] in (b"070701", b"070702"), "unexpected cpio archive format")
        try:
            nums = [int(header[6+8*i:14+8*i], 16) for i in range(13)]
        except ValueError as exc:
            raise Blocked("malformed cpio header") from exc
        mode, size, namesize = nums[1], nums[6], nums[11]
        require(1 <= namesize <= 4096 and size <= MAX_UNPACKED,
                "unsafe cpio entry length")
        endname = pos + 110 + namesize
        require(endname <= len(payload), "truncated cpio name")
        rawname = payload[pos+110:endname]
        require(rawname.endswith(b"\0"), "cpio name not null terminated")
        name = rawname[:-1].decode("utf-8", "surrogateescape").removeprefix("./")
        start = (endname + 3) & ~3
        end = start + size
        require(end <= len(payload), "truncated cpio data")
        if name == "TRAILER!!!":
            return records
        require(not name.startswith("/") and ".." not in name.split("/"),
                "unsafe cpio path")
        require(name not in records, "duplicate cpio entry: " + name)
        records[name] = (mode, memoryview(payload)[start:end])
        pos = (end + 3) & ~3
    raise Blocked("too many cpio entries")


def make_newc(name, data, mode=0o100644):
    """Synthetic test helper, never used for image construction."""
    label = name.encode() + b"\0"
    values = (1, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(label), 0)
    part = b"070701" + b"".join(f"{v:08x}".encode() for v in values) + label
    part += b"\0" * (-len(part) % 4)
    return part + data + b"\0" * (-len(data) % 4)


def self_test():
    fixture = make_newc("system/lib64/libexample.so", b"TEST") + make_newc("TRAILER!!!", b"")
    found = parse_newc(fixture)
    assert bytes(found["system/lib64/libexample.so"][1]) == b"TEST"
    assert locations(found, "libexample.so") == ["system/lib64/libexample.so"]
    cases = 2
    for bad in (make_newc("../escape", b"X") + make_newc("TRAILER!!!", b""),
                make_newc("duplicate", b"X") + make_newc("duplicate", b"Y")
                + make_newc("TRAILER!!!", b""),
                b"wrongarchive"):
        try:
            parse_newc(bad)
        except Blocked:
            cases += 1
        else:
            raise AssertionError("unexpectedly accepted malformed cpio fixture")
    assert cases == 5
    print("r0s native/TWRP ELF ramdisk fixtures PASS (5 cases)")


def unpack_recovery(image, dest, unpack_tool):
    dest.mkdir()
    run = subprocess.run([unpack_tool, "--boot_img", str(image), "--out", str(dest)],
                         capture_output=True)
    require(run.returncode == 0, "unpack_bootimg failed for " + image.name)
    ramdisk = dest / "ramdisk"
    require(ramdisk.is_file(), "unpacked recovery ramdisk absent")
    return ramdisk.read_bytes()


def run_lz4(payload):
    process = subprocess.Popen(["lz4", "-dc"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        data, error = process.communicate(input=payload, timeout=90)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.communicate()
        raise Blocked("stock LZ4 decompression timeout") from exc
    require(process.returncode == 0 and len(data) <= MAX_UNPACKED,
            "stock LZ4 recovery ramdisk decode failed/too large: "
            + error.decode(errors="replace")[:120])
    return data


def locations(records, basename):
    return sorted(path for path, (mode, _) in records.items()
                  if path.rsplit("/", 1)[-1] == basename
                  and (stat.S_ISREG(mode) or stat.S_ISLNK(mode)))


def elf_dependencies(records, binary, prefix, temp):
    entry = records.get(binary)
    require(entry is not None and stat.S_ISREG(entry[0]),
            "required recovery binary missing: " + binary)
    filename = temp / (prefix + ".elf")
    filename.write_bytes(entry[1])
    header = subprocess.run(["readelf", "-h", str(filename)], capture_output=True, text=True)
    dynamic = subprocess.run(["readelf", "-d", str(filename)], capture_output=True, text=True)
    programs = subprocess.run(["readelf", "-l", str(filename)], capture_output=True, text=True)
    require(header.returncode == 0 and dynamic.returncode == 0,
            "cannot parse " + prefix + " ELF")
    machine = re.search(r"Machine:\s*(\S+)", header.stdout)
    elf_class = re.search(r"Class:\s*(\S+)", header.stdout)
    require(machine and machine.group(1) == "AArch64" and
            elf_class and elf_class.group(1) == "ELF64",
            "non-64-bit-AArch64 recovery executable: " + prefix)
    need = re.findall(r"Shared library: \[(.*?)\]", dynamic.stdout)
    interp = re.findall(r"Requesting program interpreter: (.*?)\]", programs.stdout)
    print("===== " + prefix.upper() + " RECOVERY ELF DIRECT DEPENDENCIES =====")
    print(prefix + "_elf_sha256=" + hashlib.sha256(entry[1]).hexdigest())
    print(prefix + "_ramdisk_entry_count=" + str(len(records)))
    print(prefix + "_needed_count=" + str(len(need)))
    print(prefix + "_interpreter=" + (",".join(interp) if interp else "NONE"))
    absent = []
    for lib in need:
        found = locations(records, lib)
        if not found:
            absent.append(lib)
        print(prefix + "_needed=" + lib
              + " in_ramdisk=" + str(bool(found)).lower()
              + " paths=" + (",".join(found) or "-"))
    for p in interp:
        print(prefix + "_linker_path_in_ramdisk="
              + str(p.lstrip("/") in records).lower())
    print(prefix + "_direct_libraries_absent_from_ramdisk=" +
          (",".join(absent) if absent else "NONE"))
    return absent


def audit(tarpath):
    fw = ROOT / "out/fw/SM-S901B_EUX"
    stock = fw / "kernel/recovery.img"
    marker = fw / ".extracted"
    lock = ROOT / "target/r0s/installer/assertions.edify"
    require(marker.is_file() and marker.read_text().strip() == GZH3,
            "GZH3 firmware release pin mismatch")
    require(lock.is_file() and re.search(r'^\s*abort\("E3099:.*NOT qualified for flashing',
                                        lock.read_text(), re.M), "E3099 lock removed")
    require(stock.is_file() and sha256(stock) == STOCK_SHA, "stock recovery hash mismatch")
    require(tarpath.is_file() and sha256(tarpath) == TWRP_SHA, "TWRP TAR hash mismatch")
    tool = ROOT / "out/tools/bin/unpack_bootimg"
    unpack_tool = str(tool) if tool.is_file() else shutil.which("unpack_bootimg")
    require(unpack_tool is not None, "unpack_bootimg missing")
    for name in ("readelf", "lz4"):
        require(shutil.which(name) is not None, "required host tool missing: " + name)
    with tempfile.TemporaryDirectory() as dirname:
        tmp = Path(dirname)
        with tarfile.open(tarpath, "r:*") as archive:
            members = [m for m in archive.getmembers() if m.name == "recovery.img"]
            require(len(members) == 1 and members[0].isfile()
                    and 0 < members[0].size <= 100663296,
                    "expected exactly one bounded TWRP recovery.img member")
            stream = archive.extractfile(members[0])
            require(stream is not None, "cannot stream TWRP recovery member")
            image = tmp / "twrp.img"
            with stream, image.open("wb") as target:
                shutil.copyfileobj(stream, target)
        native = run_lz4(unpack_recovery(stock, tmp / "stock", unpack_tool))
        try:
            old = gzip.decompress(unpack_recovery(image, tmp / "twrp", unpack_tool))
        except (OSError, EOFError) as exc:
            raise Blocked("TWRP ramdisk gzip decode failed") from exc
        require(len(old) <= MAX_UNPACKED, "TWRP expanded ramdisk exceeds audit bound")
        stock_files = parse_newc(native)
        twrp_files = parse_newc(old)
        elf_dependencies(stock_files, "system/bin/recovery", "stock", tmp)
        elf_dependencies(twrp_files, "system/bin/twrp", "twrp", tmp)
        print("HOST RECOVERY RUNTIME DIRECT-DEPENDENCY INVENTORY COMPLETE")
        print("Absent from ramdisk does NOT prove runtime absence; other mounts may supply files.")
        print("No runtime execution, repacking or flashing. E3099 ACTIVE.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("twrp_tar", nargs="?", type=Path,
                        default=Path.home() / "android/S22-ROM/S901B_twrp_logo_vbmeta.tar")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            audit(args.twrp_tar.expanduser().resolve())
    except (Blocked, OSError, tarfile.TarError, ValueError) as exc:
        print("r0s RECOVERY ELF DEPENDENCY AUDIT BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
