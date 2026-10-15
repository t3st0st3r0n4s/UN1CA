#!/usr/bin/env python3
"""Pin and apply a HOST-ONLY A16 hybrid r0s kernel to a UN1CA workdir.

--check never writes. --apply may run ONLY inside r0s late-patch phase,
after upstream ROM fs/proca modifications. No firmware, zip or device writes.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "out/fw/SM-S901B_EUX"
WORK = ROOT / "out/target/r0s/work_dir"
SRC = ROOT / "out/kernel_tmp-exynos2200"
ART = SRC / "build/out/r0s"
CAND = ROOT / "out/r0s_A16_ExtremeKRNL_KSU_hybrid_candidate"
MARK = WORK / "kernel/.r0s_extremekrnl_a16_integrated"
KPIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"


def selected_ksu_pin(required=True):
    """Use the exact compiled source pin, or CI's explicit pin; no old fallback."""
    pin = os.environ.get("KSU_PIN")
    if not pin:
        marker = ART / ".r0s_a16_kernel_host_pass"
        if marker.is_file():
            matches = [line.removeprefix("ksunext=")
                       for line in marker.read_text().splitlines()
                       if line.startswith("ksunext=")]
            if len(matches) != 1:
                raise ValueError("compiled KernelSU Next provenance ambiguous")
            pin = matches[0]
    if not pin:
        if required:
            raise ValueError("KernelSU Next build provenance missing")
        return None
    if len(pin) != 40 or any(c not in "0123456789abcdef" for c in pin):
        raise ValueError("invalid KernelSU Next source pin")
    return pin


SPIN = selected_ksu_pin(required=False)
FOTA = "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"
IMAGES = ("boot.img", "vendor_boot.img", "dtbo.img")
MODULES = ("fingerprint.ko", "fingerprint_sysfs.ko",
           "input_booster_lkm.ko", "sec_debug_coredump.ko", "wlan.ko")
CAP = {"boot.img": 67108864, "vendor_boot.img": 33554432, "dtbo.img": 8388608}


class Hold(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise Hold(message)


def digest(path):
    need(path.is_file() and path.stat().st_size > 0, "missing or empty: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(*command):
    proc = subprocess.run([str(x) for x in command], capture_output=True)
    if proc.returncode:
        raise Hold("failed: " + " ".join(map(str, command[:5]))
                   + ": " + proc.stderr.decode(errors="replace")[-800:])
    return proc.stdout


def unpack(image, destination):
    destination.mkdir()
    run("unpack_bootimg", "--boot_img", image, "--out", destination)


def verify_cpio_integrity(source, what):
    compressed = run("lz4", "-dc", source)
    test = subprocess.run(["cpio", "-it", "--quiet"], input=compressed, capture_output=True)
    need(test.returncode == 0, "broken " + what)
    return tuple(s.removeprefix("./") for s in test.stdout.decode().splitlines())


def inspect_inputs():
    need((FW / ".extracted").is_file()
         and (FW / ".extracted").read_text().strip() == FOTA,
         "native GZH3 extraction missing/mismatched")
    need((WORK / "system/system/build.prop").is_file(),
         "UN1CA workdir missing")
    props = (WORK / "system/system/build.prop").read_text()
    for prop in ("ro.build.version.sdk=36", "ro.product.device=r0s",
                 "ro.unica.device=r0s"):
        need(prop in props.splitlines(), "not Android 16 r0s workdir: " + prop)
    assertions = (ROOT / "target/r0s/installer/assertions.edify").read_text()
    need('abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");'
         in assertions, "mandatory E3099 installer abort removed")
    need((ART / ".r0s_a16_kernel_host_pass").is_file(),
         "compiled A16 host-pass marker absent")
    need(SPIN is not None, "KernelSU Next build provenance missing")
    need(run("git", "-C", SRC, "rev-parse", "HEAD").decode().strip() == KPIN,
         "kernel source pin changed")
    need(run("git", "-C", SRC / "KernelSU-Next", "rev-parse", "HEAD").decode().strip() == SPIN,
         "KernelSU Next pin changed")
    config = (SRC / "out/.config").read_text().splitlines()
    need("CONFIG_KSU=y" in config and "CONFIG_MODVERSIONS=y" in config,
         "compiled kernel KSU/modversion requirements missing")
    need((CAND / "NOT_FLASHABLE.txt").is_file(), "isolated hybrid candidate absent")
    need(not MARK.exists(), "custom kernel already installed in workdir")
    for name in IMAGES:
        file = CAND / name
        digest(file)
        need(file.stat().st_size <= CAP[name], "image over physical cap: " + name)
        need((WORK / "kernel" / name).is_file(), "missing native work image: " + name)
    need(digest(CAND / "dtbo.img") == digest(ART / "dtbo.img"),
         "candidate DTBO differs from current compilation")
    for name in MODULES:
        path = CAND / "vendor_dlkm/lib/modules" / name
        need(digest(path) == digest(ART / "modules/lib/modules" / name),
             "hybrid module differs from current compilation: " + name)
        need(digest(FW / "vendor_dlkm/lib/modules" / name) ==
             digest(WORK / "vendor_dlkm/lib/modules" / name),
             "native work module already modified: " + name)
        magic = run("modinfo", "-F", "vermagic", path).decode().strip()
        need(magic.startswith("5.10.269-ExtremeKRNL-v2.5+ "),
             "module vermagic differs: " + name)
    return True


def ramdisk_gate():
    # Refuse a hybrid candidate if rebuilt UN1CA workramdisks differ
    # from the originals used when that candidate was constructed.
    with tempfile.TemporaryDirectory(prefix="r0s-integrate-") as t:
        tmp = Path(t)
        for name in ("boot", "vendor_boot"):
            unpack(WORK / "kernel" / (name + ".img"), tmp / ("native_" + name))
            unpack(CAND / (name + ".img"), tmp / ("candidate_" + name))
        checks = (
            ("native_boot/ramdisk", "candidate_boot/ramdisk",
             "native boot ramdisk"),
            ("native_vendor_boot/vendor_ramdisk00",
             "candidate_vendor_boot/vendor_ramdisk00", "GZH3 fstab and encryption ramdisk"),
            ("native_vendor_boot/bootconfig",
             "candidate_vendor_boot/bootconfig", "GZH3 vendor bootconfig"),
        )
        for src, dst, label in checks:
            a, b = tmp / src, tmp / dst
            need(a.is_file() and b.is_file(), label + " missing")
            # Empty vendor bootconfig is permitted in v4, compare bytes exactly.
            need(a.read_bytes() == b.read_bytes(), label + " differs from candidate")
        members = verify_cpio_integrity(
            tmp / "candidate_vendor_boot/vendor_ramdisk01", "custom module ramdisk")
        for name in MODULES:
            need("lib/modules/" + name in members, "custom ramdisk lacks " + name)
        need("lib/modules/modules.load" in members, "custom module load list absent")
    print("Native boot/early mount/bootconfig preserved; module ramdisk present")


def dryrun():
    for tool in ("unpack_bootimg", "modinfo", "lz4", "cpio"):
        need(shutil.which(tool), "missing tool " + tool + " (set out/tools/bin in PATH)")
    inspect_inputs()
    ramdisk_gate()
    print("A16 EXTREMEKRNL R0S LATE-INTEGRATION CHECK PASS — no writes")
    print("current candidate and compiled module integrity PASS")
    print("Not ROM-integrated / no device access / E3099 ACTIVE")


def apply():
    need(os.environ.get("UN1CA_R0S_LATE_PATCH") == "1",
         "--apply only permitted from explicit r0s late patch stage")
    dryrun()
    # All source verification occurs before the first workdir mutation.
    changes = [(CAND / name, WORK / "kernel" / name) for name in IMAGES]
    changes.extend(
        (CAND / "vendor_dlkm/lib/modules" / name, WORK / "vendor_dlkm/lib/modules" / name)
        for name in MODULES
    )
    # Stage all inputs in their destination directories before replacing;
    # original workdir is rebuildable from preserved stock images.
    prepared = []
    try:
        for source, dest in changes:
            fd, path = tempfile.mkstemp(prefix="." + dest.name + ".a16.", dir=dest.parent)
            os.close(fd)
            stage = Path(path)
            prepared.append(stage)
            shutil.copyfile(source, stage)
            need(digest(stage) == digest(source), "staged file differs: " + dest.name)
            stage.chmod(dest.stat().st_mode & 0o777)
        for (_, dest), staged in zip(changes, prepared):
            staged.replace(dest)
        MARK.write_text(
            "source=" + KPIN + "\nksu=" + SPIN
            + "\nmode=GZH3_EARLY_MOUNT_PLUS_EXTREMEKRNL_5.10.269"
            + "\nhost_only=true\nboard_pass=false\n")
    finally:
        for f in prepared:
            if f.exists():
                f.unlink()
    for _, dest in changes:
        source = (CAND / dest.name if dest.name in IMAGES
                  else CAND / "vendor_dlkm/lib/modules" / dest.name)
        need(digest(dest) == digest(source), "postinstall hash mismatch: " + dest.name)
    print("A16 EXTREMEKRNL R0S WORKDIR LATE-INTEGRATION PASS — HOST ONLY")
    print("No OTA or device operation. E3099 remains active.")


def verify_integrated():
    # Read-only validation for the final patched workdir and target-files gates.
    need(MARK.is_file(), "custom integration marker missing")
    marker = MARK.read_text().splitlines()
    for entry in ("source=" + KPIN, "ksu=" + SPIN,
                  "mode=GZH3_EARLY_MOUNT_PLUS_EXTREMEKRNL_5.10.269",
                  "host_only=true", "board_pass=false"):
        need(entry in marker, "integration marker incomplete: " + entry)
    need((FW / ".extracted").is_file() and
         (FW / ".extracted").read_text().strip() == FOTA,
         "GZH3 firmware missing")
    lock = (ROOT / "target/r0s/installer/assertions.edify").read_text()
    need('abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");'
         in lock, "E3099 removed")
    for name in IMAGES:
        need(digest(WORK / "kernel" / name) == digest(CAND / name),
             "workdir image differs from current candidate: " + name)
    for name in MODULES:
        compiled = digest(ART / "modules/lib/modules" / name)
        need(digest(CAND / "vendor_dlkm/lib/modules" / name) == compiled,
             "candidate module differs from current compilation: " + name)
        need(digest(WORK / "vendor_dlkm/lib/modules" / name) == compiled,
             "workdir module differs from current compilation: " + name)
    for tool in ("unpack_bootimg", "lz4", "cpio"):
        need(shutil.which(tool), "missing validation host tool " + tool)
    ramdisk_gate()
    print("A16 EXTREMEKRNL R0S INTEGRATED WORKDIR VERIFY PASS — HOST ONLY")
    print("Kernel/KSU current candidate matched; E3099 ACTIVE")


def fixture():
    need(set(CAP) == set(IMAGES), "image list mismatch")
    need(len(MODULES) == 5, "required vendor_dlkm list incomplete")
    need(len(KPIN) == 40 and (SPIN is None or len(SPIN) == 40),
         "malformed source pin")
    print("A16 custom r0s late-integration schema self-test PASS")


def main():
    if sys.argv[1:] == ["--self-test"]:
        fixture()
    elif SPIN is None:
        raise Hold("KernelSU Next compiled provenance missing")
    elif sys.argv[1:] in ([], ["--check"]):
        dryrun()
    elif sys.argv[1:] == ["--apply"]:
        apply()
    elif sys.argv[1:] == ["--verify"]:
        verify_integrated()
    else:
        raise Hold("usage: integrate_extremekrnl_a16.py [--check|--apply|--verify|--self-test]")


if __name__ == "__main__":
    try:
        main()
    except (Hold, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("A16 EXTREMEKRNL INTEGRATION BLOCKED: " + str(exc), file=sys.stderr)
        sys.exit(2)
