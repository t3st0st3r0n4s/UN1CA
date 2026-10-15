#!/usr/bin/env python3
"""Produce isolated hybrid S901B A16 boot images; never modify ROM workdir.

Preserve UN1CA GZH3 native boot ramdisk, vendor ramdisk00 (fstab,
encryption and AVB configuration), bootconfig and boot header metadata.
Use ExtremeKRNL kernel/DTB, module ramdisk01, dtbo and five .ko files.
The output remains HOST-ONLY and is never installed or flashed here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "out/kernel_tmp-exynos2200"
ART = SRC / "build/out/r0s"
WORK = ROOT / "out/target/r0s/work_dir"
FW = ROOT / "out/fw/SM-S901B_EUX"
DEST = ROOT / "out/r0s_A16_ExtremeKRNL_KSU_hybrid_candidate"
KERNEL_PIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU_PIN = "8f902aeb16033024143ae36cf711df902cf02fae"
MODULES = ("fingerprint", "fingerprint_sysfs", "input_booster_lkm",
           "sec_debug_coredump", "wlan")
FIRMWARE = "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"


def hold(message):
    raise SystemExit("A16 HYBRID REPACK HOLD: " + str(message))


def require(path):
    if not path.is_file() or path.stat().st_size == 0:
        hold("missing or empty: " + str(path))
    return path


def call(*args):
    argv = [str(x) for x in args]
    proc = subprocess.run(argv, capture_output=True)
    if proc.returncode:
        hold("command " + " ".join(argv[:7]) + " failed: "
             + proc.stderr.decode(errors="replace")[-1500:])
    return proc.stdout


def same(a, b, what):
    # A valid vendor_boot v4 may carry a zero-byte bootconfig; comparing it
    # must not incorrectly require nonempty content.
    if not a.is_file() or not b.is_file() or sha256(a) != sha256(b):
        hold(what + " altered")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def extract(image, folder):
    folder.mkdir()
    # Use unpack_bootimg's canonical mkbootimg arguments, retaining
    # native address offsets, page size, board ids and fragment ordering.
    args = shlex.split(call("unpack_bootimg", "--boot_img", require(image),
                            "--out", folder, "--format=mkbootimg").decode())
    if not args:
        hold("unpack_bootimg produced no rebuild args for " + str(image))
    return args


def vals(args, name):
    return [args[index + 1] for index in range(len(args) - 1)
            if args[index] == name]


def substitute(args, name, replacement):
    result = args[:]
    positions = [i for i, token in enumerate(result) if token == name]
    if len(positions) != 1:
        hold("expected one " + name)
    result[positions[0] + 1] = str(replacement)
    return result


def assert_native_erofs(fragment):
    archive = call("lz4", "-dc", fragment)
    listing = subprocess.run(["cpio", "-it", "--quiet"],
                             input=archive, capture_output=True)
    if listing.returncode:
        hold("GZH3 vendor_ramdisk00 invalid cpio")
    names = {x.removeprefix("./") for x in listing.stdout.decode().splitlines()}
    for fstab in ("first_stage_ramdisk/fstab.s5e9925", "fstab.s5e9925",
                  "etc/recovery.fstab"):
        if fstab not in names:
            hold("GZH3 missing native " + fstab)
        raw = subprocess.run(["cpio", "-i", "--quiet", "--to-stdout",
                              fstab, "./" + fstab],
                             input=archive, capture_output=True)
        if raw.returncode or not raw.stdout:
            hold("unreadable native " + fstab)
        if fstab == "etc/recovery.fstab":
            continue
        mapping = {}
        for line in raw.stdout.decode(errors="replace").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = line.split()
            if len(fields) >= 3:
                mapping.setdefault(fields[1], set()).add(fields[2])
        for mount in ("/system", "/vendor", "/vendor_dlkm", "/odm", "/product"):
            if mapping.get(mount) != {"erofs"}:
                hold(f"{fstab} {mount} is not native GZH3 EROFS-only: "
                     + repr(mapping.get(mount)))


def fixture():
    example = ["--header_version", "4", "--dtb", "old",
               "--vendor_ramdisk_fragment", "f0",
               "--ramdisk_type", "3", "--vendor_ramdisk_fragment", "f1"]
    assert vals(example, "--vendor_ramdisk_fragment") == ["f0", "f1"]
    assert vals(substitute(example, "--dtb", "new"), "--dtb") == ["new"]
    assert len(KERNEL_PIN) == len(KSU_PIN) == 40
    print("S901B A16 GZH3/custom kernel hybrid repack self-test PASS")


def main():
    if sys.argv[1:] == ["--self-test"]:
        fixture()
        return
    ci_donors = sys.argv[1:] == ["--ci-donors"]
    if sys.argv[1:] and not ci_donors:
        hold("usage: reconcile_extremekrnl_gzh3_a16.py [--self-test|--ci-donors]")
    for binary in ("unpack_bootimg", "lz4", "cpio", "modinfo"):
        if not shutil.which(binary):
            hold("host tool missing: " + binary)
    if DEST.exists():
        hold("candidate exists and will never be overwritten: " + str(DEST))
    if ci_donors:
        # Same trusted GZH3 images as the October 13 workdir; without
        # claiming the ephemeral CI workspace is a completed ROM workdir.
        sums = ROOT / "ci_inputs/r0s_a16_gzh3_donors.sha256"
        if not sums.is_file():
            hold("pinned CI GZH3 donor SHA256 manifest missing")
        records = dict(line.strip().split("  ", 1)[::-1]
                       for line in sums.read_text().splitlines() if line.strip())
        if set(records) != {"boot.img", "vendor_boot.img"}:
            hold("unexpected A16 CI donor manifest")
        for name, expected in records.items():
            item = require(WORK / "kernel" / name)
            if sha256(item) != expected:
                hold("CI donor SHA256 differs: " + name)
        if not require(ART / "boot.img").is_file():
            hold("no newly compiled ExtremeKRNL boot image")
        print("PINNED CI A16 GZH3 BOOT DONORS PASS (not a ROM workdir)")
    else:
        if require(FW / ".extracted").read_text().strip() != FIRMWARE:
            hold("native GZH3 firmware marker mismatch")
        require(WORK / ".completed")
        require(ART / ".r0s_a16_kernel_host_pass")
    assertions = (ROOT / "target/r0s/installer/assertions.edify").read_text()
    if 'abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");' not in assertions:
        hold("E3099 installer lock missing")
    if call("git", "-C", SRC, "rev-parse", "HEAD").decode().strip() != KERNEL_PIN:
        hold("kernel pin mismatch")
    if call("git", "-C", SRC / "KernelSU-Next", "rev-parse", "HEAD").decode().strip() != KSU_PIN:
        hold("KernelSU Next pin mismatch")
    config = "\n" + require(SRC / "out/.config").read_text()
    for symbol in ("CONFIG_KSU=y", "CONFIG_MODVERSIONS=y"):
        if "\n" + symbol + "\n" not in config:
            hold(symbol + " absent from compiled kernel")
    mkbootimg = require(SRC / "toolchain/mkbootimg/mkbootimg.py")

    with tempfile.TemporaryDirectory(prefix=".r0s_a16_hybrid_", dir=ROOT / "out") as tmp:
        scratch = Path(tmp)
        wb, cb, wv, cv = (scratch / name for name in
                           ("work_boot", "custom_boot", "work_vendor", "custom_vendor"))
        boot_args = extract(WORK / "kernel/boot.img", wb)
        extract(ART / "boot.img", cb)
        vendor_args = extract(WORK / "kernel/vendor_boot.img", wv)
        extract(ART / "vendor_boot.img", cv)

        if vals(boot_args, "--header_version") != ["4"] or vals(vendor_args, "--header_version") != ["4"]:
            hold("native boot/vendor_boot not v4")
        if len(vals(vendor_args, "--vendor_ramdisk_fragment")) != 2:
            hold("native vendor_boot does not have two fragments")
        if vals(vendor_args, "--ramdisk_type") != ["1", "3"]:
            hold("native vendor_boot ramdisk type/order differs from 1/3")
        if len(vals(vendor_args, "--ramdisk_name")) != 2:
            hold("native vendor_boot ramdisk names count differs")
        if not vals(boot_args, "--kernel") or not vals(boot_args, "--ramdisk"):
            hold("native boot header missing ramdisk/kernel")
        for key in ("--vendor_bootconfig", "--dtb", "--vendor_cmdline"):
            if not vals(vendor_args, key):
                hold("native vendor_boot missing " + key)
        same(cv / "dtb", require(ART / "dtb.img"), "upstream custom DTB provenance")
        assert_native_erofs(require(wv / "vendor_ramdisk00"))
        print("NATIVE GZH3 FSTAB EROFS CONFIG PASS")

        out = scratch / "candidate"
        out.mkdir()
        # The native workdir header/ramdisk remains byte-for-byte unchanged;
        # only the kernel binary is substituted.
        boot_args = substitute(boot_args, "--kernel", require(cb / "kernel"))
        call(sys.executable, mkbootimg, *boot_args, "--output", out / "boot.img")
        # Native GZH3 fstab, userdata/AVB flags, bootconfig and cmdline are
        # inherited. Only custom DTB and the matching module ramdisk change.
        frag = [i for i, token in enumerate(vendor_args)
                if token == "--vendor_ramdisk_fragment"]
        vendor_args[frag[1] + 1] = str(require(cv / "vendor_ramdisk01"))
        vendor_args = substitute(vendor_args, "--dtb", require(cv / "dtb"))
        call(sys.executable, mkbootimg, *vendor_args,
             "--vendor_boot", out / "vendor_boot.img")
        shutil.copyfile(require(ART / "dtbo.img"), out / "dtbo.img")
        for mod in MODULES:
            source = require(ART / "modules/lib/modules" / (mod + ".ko"))
            vermagic = call("modinfo", "-F", "vermagic", source).decode().strip()
            if not vermagic.startswith("5.10.269-ExtremeKRNL-v2.5+ "):
                hold(mod + ": mismatched version magic " + vermagic)
            target = out / "vendor_dlkm/lib/modules" / (mod + ".ko")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

        vb, vv = scratch / "verified_boot", scratch / "verified_vendor"
        extract(out / "boot.img", vb)
        verified_args = extract(out / "vendor_boot.img", vv)
        same(vb / "kernel", cb / "kernel", "hybrid kernel")
        same(vb / "ramdisk", wb / "ramdisk", "native boot ramdisk")
        same(vv / "dtb", cv / "dtb", "custom DTB")
        same(vv / "bootconfig", wv / "bootconfig", "native vendor bootconfig")
        same(vv / "vendor_ramdisk00", wv / "vendor_ramdisk00", "native GZH3 fstab")
        same(vv / "vendor_ramdisk01", cv / "vendor_ramdisk01", "custom module ramdisk")
        for key in ("--vendor_cmdline", "--board", "--pagesize",
                    "--base", "--kernel_offset", "--ramdisk_offset",
                    "--tags_offset", "--dtb_offset",
                    "--ramdisk_type", "--ramdisk_name"):
            if vals(vendor_args, key) != vals(verified_args, key):
                hold("native vendor_boot metadata changed: " + key)

        for name, cap in (("boot", 67108864), ("vendor_boot", 33554432), ("dtbo", 8388608)):
            item = require(out / (name + ".img"))
            if item.stat().st_size > cap:
                hold(name + ".img exceeds physical partition size")
            print(f"{item.name}: bytes={item.stat().st_size} sha256={sha256(item)}")
        for mod in MODULES:
            item = out / "vendor_dlkm/lib/modules" / (mod + ".ko")
            print(f"{mod}.ko sha256={sha256(item)}")
        (out / "NOT_FLASHABLE.txt").write_text(
            "HOST-ONLY A16 custom kernel/GZH3 hybrid. NOT a ROM, OTA, verified "
            "BL/AVB, userdata migration, device test or flashing package. "
            "Existing UN1CA workdir, firmware and E3099 lock remain unchanged.\n"
        )
        if DEST.exists():
            hold("output path appeared during packaging, refusing overwrite")
        out.rename(DEST)
    print("HYBRID A16 BOOT-CHAIN REPACK HOST CANDIDATE PASS")
    print("output: " + str(DEST))
    print("NOT ROM-INTEGRATED / NOT BOARD-QUALIFIED / E3099 ACTIVE")


if __name__ == "__main__":
    main()
