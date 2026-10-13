#!/usr/bin/env python3
"""Read-only reconciliation gate: native UN1CA GZH3 vendor_boot vs custom ExtremeKRNL.

Never overlays the ROM workdir. A difference is a HOLD for design review,
not a suggestion to copy vendor_boot over the GZH3-derived image.
"""
import difflib
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CUSTOM = ROOT / "out/kernel_tmp-exynos2200/build/out/r0s"
WORK = ROOT / "out/target/r0s/work_dir"
FW = ROOT / "out/fw/SM-S901B_EUX"
FIVE = ("system", "odm", "product", "vendor", "vendor_dlkm")
DLKM = ("fingerprint", "fingerprint_sysfs", "input_booster_lkm", "sec_debug_coredump", "wlan")


def fail(msg):
    print("A16 EXTREMEKRNL INTEGRATION HOLD: " + msg, file=sys.stderr)
    raise SystemExit(2)


def run(args, *, input_data=None):
    result = subprocess.run(args, input=input_data, capture_output=True, check=False)
    if result.returncode:
        fail(f"command failed: {' '.join(map(str, args))}: "
             + result.stderr.decode("utf-8", errors="replace")[-1200:])
    return result.stdout


def lines(data):
    return data.decode("utf-8", errors="replace").splitlines()


def unpack(image, dest):
    dest.mkdir(parents=True)
    run(["unpack_bootimg", "--boot_img", str(image), "--out", str(dest)])
    return dest


def archive_data(path):
    # Both fragments have been independently identified as LZ4 in the host audit.
    return run(["lz4", "-dc", str(path)])


def cpio_names(archive):
    return tuple(s.removeprefix("./") for s in lines(run(["cpio", "-it", "--quiet"], input_data=archive)))


def cpio_read(archive, entry):
    # Exact file reads only; no extraction into the original workdir or host.
    return run(["cpio", "-i", "--quiet", "--to-stdout", entry], input_data=archive)


def fstab_types(data):
    found = {}
    for line in lines(data):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        tok = s.split()
        if len(tok) < 3:
            continue
        mount = tok[1].removeprefix("/")
        if mount in FIVE:
            found.setdefault(mount, set()).add(tok[2])
    return found


def test_self():
    assert fstab_types(b"system /system erofs ro wait\n") == {"system": {"erofs"}}
    assert fstab_types(b"#skip\nvendor /vendor ext4 ro wait\n") == {"vendor": {"ext4"}}
    assert fstab_types(b"bad\n") == {}
    print("GZH3/custom fstab parsing self-test PASS")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        test_self()
        return
    if len(sys.argv) != 1:
        fail("usage: python3 scripts/r0s/compare_extremekrnl_gzh3_a16.py [--self-test]")
    if not (FW / ".extracted").exists() or not (WORK / ".completed").exists():
        fail("native firmware extraction or completed workdir absent")
    if (FW / ".extracted").read_text().strip() != (
        "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"
    ):
        fail("GZH3 source marker mismatch")
    assertions = (ROOT / "target/r0s/installer/assertions.edify").read_text()
    if 'abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");' not in assertions:
        fail("E3099 installation lock missing")
    if not (CUSTOM / ".r0s_a16_kernel_host_pass").is_file():
        fail("custom kernel HOST PASS marker absent")

    for cmd in ("unpack_bootimg", "lz4", "cpio"):
        from shutil import which
        if not which(cmd):
            fail(f"required command missing: {cmd}; add out/tools/bin to PATH")

    with tempfile.TemporaryDirectory(prefix="r0s-a16-vendor-boot-") as temp:
        temp = Path(temp)
        work_img = WORK / "kernel/vendor_boot.img"
        custom_img = CUSTOM / "vendor_boot.img"
        if not work_img.is_file() or not custom_img.is_file():
            fail("work and custom vendor_boot.img both required")
        work = unpack(work_img, temp / "gzh3_work")
        custom = unpack(custom_img, temp / "extremekrnl")

        data = {}
        for side, directory in (("work", work), ("candidate", custom)):
            for index in ("00", "01"):
                fragment = directory / f"vendor_ramdisk{index}"
                if not fragment.is_file():
                    fail(f"{side}: missing vendor_ramdisk{index}")
                raw = archive_data(fragment)
                data[(side, index)] = raw
                members = cpio_names(raw)
                print(f"{side} vendor_ramdisk{index}: {len(members)} entries")
                if index == "00":
                    names = sorted(m for m in members if "fstab" in Path(m).name)
                    if not names:
                        fail(f"{side}: no fstab in vendor_ramdisk00")
                    data[(side, "fstab_names")] = names
                    data[(side, "fstab")] = {
                        name: cpio_read(raw, name) for name in names
                    }

        print("\n===== GZH3 WORKDIR vs CUSTOM EARLY-MOUNT CONFIG =====")
        a, b = data[("work", "fstab")], data[("candidate", "fstab")]
        print("work fstab paths: " + ", ".join(a))
        print("candidate fstab paths: " + ", ".join(b))
        issues = []
        if set(a) != set(b):
            issues.append("fstab paths differ")
        for name in sorted(set(a) | set(b)):
            if name not in a or name not in b:
                continue
            left, right = a[name], b[name]
            leftfs, rightfs = fstab_types(left), fstab_types(right)
            print(f"\n{name}:")
            print("  GZH3 fs map:", {k: sorted(v) for k, v in sorted(leftfs.items())})
            print("  Extreme fs map:", {k: sorted(v) for k, v in sorted(rightfs.items())})
            absent = [n for n in FIVE if "erofs" in leftfs.get(n, set())
                      and "erofs" not in rightfs.get(n, set())]
            if absent:
                issues.append(f"{name}: missing GZH3 EROFS for {','.join(absent)}")
            if left != right:
                issues.append(f"{name}: fstab byte difference; merge/rebuild needed")
                diff = difflib.unified_diff(
                    lines(left), lines(right),
                    fromfile=f"work/{name}", tofile=f"candidate/{name}", lineterm=""
                )
                for line in list(diff)[:90]:
                    print(line)
            else:
                print("  EXACT BYTE MATCH")

        print("\n===== CUSTOM VENDOR RAMDISK01 MATCHES COMPILED MODULES =====")
        cpio01 = data[("candidate", "01")]
        names01 = set(cpio_names(cpio01))
        mods = CUSTOM / "modules/lib/modules"
        for name in DLKM:
            member = f"lib/modules/{name}.ko"
            compiled = mods / f"{name}.ko"
            if member not in names01 or not compiled.is_file():
                issues.append(f"required module absent from custom ramdisk: {member}")
                continue
            blob = cpio_read(cpio01, member)
            digest = hashlib.sha256(blob).hexdigest()
            same = hashlib.sha256(compiled.read_bytes()).hexdigest() == digest
            print(f"{name}.ko: {'MATCH' if same else 'DIFFERENT'} sha256={digest}")
            if not same:
                issues.append(f"{name}.ko differs between vendor_boot and compiled modules")
        load = cpio_read(cpio01, "lib/modules/modules.load")
        compiled_names = {f.name for f in mods.glob("*.ko")}
        missing_load = sorted(
            {Path(n.strip()).name for n in lines(load) if n.strip() and not n.startswith("#")}
            - compiled_names
        )
        print(f"custom modules.load: {len(lines(load))} entries; "
              f"unresolved filenames: {len(missing_load)}")
        if missing_load:
            print("Unresolved module files (first 25):", ", ".join(missing_load[:25]))
            issues.append("modules.load has unresolved names")
        if issues:
            print("\nREQUIRES RECONCILIATION — no active patch or ROM image modified")
            for item in dict.fromkeys(issues):
                print("HOLD:", item)
            raise SystemExit(2)
        print("\nRECONCILIATION PREFLIGHT PASS — NOT ROM INTEGRATED, NOT BOARD QUALIFIED")
        print("E3099 remains active; GZH3 workdir and existing firmware unchanged.")


if __name__ == "__main__":
    main()
