#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only GZH3 TWRP recovery-fstab / executable compatibility inventory."""
import argparse
import gzip
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TAR = "f82b9612d92786971609895facb703906744d9a617e673f1cd148e671735d830"
GZH3 = "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"
PARTS = ("system", "odm", "product", "vendor", "vendor_dlkm")


class Blocked(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fstab_coverage(text):
    rows = {part: [] for part in PARTS}
    extras = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("#", 1)[0].split()
        if len(fields) < 3:
            continue
        dev, mount, fs = fields[:3]
        for part in PARTS:
            if mount == "/" + part:
                rows[part].append((dev, fs))
        if mount == "/system_ext":
            extras.append((dev, fs))
    return rows, extras


def test():
    healthy = "\n".join(p + " /" + p + " erofs ro logical" for p in PARTS)
    rows, extra = fstab_coverage(healthy)
    assert not extra and all((p, "erofs") in rows[p] for p in PARTS)
    old = healthy.replace("vendor /vendor erofs", "vendor /vendor f2fs")
    assert ("vendor", "erofs") not in fstab_coverage(old)[0]["vendor"]
    old = healthy.replace("vendor_dlkm /vendor_dlkm erofs",
                          "#vendor_dlkm /vendor_dlkm f2fs")
    assert not fstab_coverage(old)[0]["vendor_dlkm"]
    old = healthy + "\nsystem_ext /system_ext f2fs ro logical"
    assert fstab_coverage(old)[1]
    old = healthy + "\n#system_ext /system_ext f2fs ro logical"
    assert not fstab_coverage(old)[1]
    print("r0s TWRP GZH3 recovery fstab fixture tests PASS (5 cases)")


def run_command(args, data=None):
    return subprocess.run(args, input=data, capture_output=True)


def cpio_entry(archive, entry):
    result = run_command(["cpio", "-i", "--quiet", "--to-stdout", entry], archive)
    require(result.returncode == 0 and result.stdout,
            "ramdisk entry unavailable: " + entry)
    return result.stdout


def audit(tarpath):
    marker = ROOT / "out/fw/SM-S901B_EUX/.extracted"
    assert_file = ROOT / "target/r0s/installer/assertions.edify"
    require(marker.is_file() and marker.read_text().strip() == GZH3,
            "GZH3 stock extraction pin mismatch")
    require(assert_file.is_file() and
            re.search(r'^\s*abort\("E3099:.*NOT qualified for flashing',
                      assert_file.read_text(), re.M), "E3099 lock missing")
    require(tarpath.is_file() and sha256(tarpath) == EXPECTED_TAR,
            "candidate TAR changed from vetted inventory")
    for tool in ("unpack_bootimg", "cpio", "readelf", "file", "strings"):
        require(shutil.which(tool) is not None, "host tool missing: " + tool)
    with tempfile.TemporaryDirectory() as dirname:
        temp = Path(dirname)
        image = temp / "recovery.img"
        with tarfile.open(tarpath) as tf:
            matches = [m for m in tf.getmembers() if m.name == "recovery.img"]
            require(len(matches) == 1 and matches[0].isfile()
                    and 0 < matches[0].size <= 100_663_296,
                    "exactly one bounded recovery.img TAR member required")
            input_file = tf.extractfile(matches[0])
            require(input_file is not None, "TAR member unreadable")
            with input_file, image.open("wb") as dst:
                shutil.copyfileobj(input_file, dst)
        unpack = temp / "out"
        unpack.mkdir()
        envtool = str(ROOT / "out/tools/bin/unpack_bootimg")
        tool = envtool if Path(envtool).is_file() else shutil.which("unpack_bootimg")
        result = run_command([tool, "--boot_img", str(image), "--out", str(unpack)])
        require(result.returncode == 0, "TWRP boot header unpack failed")
        ramdisk = unpack / "ramdisk"
        require(ramdisk.is_file(), "TWRP ramdisk not found")
        try:
            raw = gzip.decompress(ramdisk.read_bytes())
        except (OSError, EOFError) as exc:
            raise Blocked("candidate gzip ramdisk unreadable: " + str(exc))
        require(len(raw) <= 256 * 1024 * 1024, "expanded TWRP ramdisk unusually large")
        fstab = cpio_entry(raw, "system/etc/recovery.fstab").decode(errors="replace")
        entries, system_ext = fstab_coverage(fstab)
        print("===== TWRP RECOVERY FSTAB vs GZH3 EROFS =====")
        passed = 0
        for p in PARTS:
            good = (p, "erofs") in entries[p]
            passed += good
            print(p + " erofs=" + str(good).lower() +
                  " entries=" + (str(entries[p]) if entries[p] else "NONE"))
        print("native_five_partition_erofs_coverage=" + str(passed) + "/5")
        print("separate_system_ext_active=" + str(bool(system_ext)).lower())
        twrp = temp / "twrp"
        twrp.write_bytes(cpio_entry(raw, "system/bin/twrp"))
        print("===== TWRP USERSPACE BINARY =====")
        print("twrp_sha256=" + sha256(twrp))
        for name, command in (
            ("file", ["file", "-b", str(twrp)]),
            ("elf", ["readelf", "-h", str(twrp)]),
        ):
            result = run_command(command)
            require(result.returncode == 0, "cannot inspect TWRP " + name)
            lines = result.stdout.decode(errors="replace").splitlines()
            for line in lines:
                if name == "file" or re.search(r"Class:|Machine:|Type:", line):
                    print(line)
        result = run_command(["strings", "-a", str(twrp)])
        if result.returncode == 0:
            found = sorted({line for line in result.stdout.decode(errors="replace").splitlines()
                            if any(token in line.lower() for token in
                                   ("vendor_dlkm", "erofs", "map_partition",
                                    "update_dynamic_partitions", "block_image_update"))})
            for s in found[:20]:
                print("static_binary_hint=" + s[:160])
        if passed != 5 or system_ext:
            print("TWRP GZH3 RECOVERY.FSTAB COVERAGE BLOCKED — adaptation required.")
        else:
            print("TWRP FSTAB COVERAGE PASS ONLY — no runtime qualification.")
        print("HOST-ONLY INSPECTION COMPLETE. NO IMAGE CREATED; E3099 ACTIVE.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("twrp_tar", nargs="?", type=Path,
                        default=Path.home() / "android/S22-ROM/S901B_twrp_logo_vbmeta.tar")
    args = parser.parse_args()
    try:
        if args.self_test:
            test()
        else:
            audit(args.twrp_tar.expanduser().resolve())
    except (Blocked, OSError, tarfile.TarError, AssertionError) as exc:
        print("r0s TWRP GZH3 INSPECTION BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
