#!/usr/bin/env python3
"""Reuse TachyonOS/ExtremeKRNL's proven 3-image recovery ZIP for UN1CA A16.

Proven A15 pattern: META-INF/com/google/android/{update-binary,updater-script}
plus files/{boot.img,vendor_boot.img,dtbo.img}. Never touch vendor_dlkm from
the kernel-only recovery update; matching modules must ALREADY be deployed
and remain ABI-compatible. This is maintenance of installed UN1CA A16, not
a first A15->A16 ROM installation.

The official ExtremeKRNL update-binary Git blob 0a6085... is identical at
A15 ExtremeXT/9ac30b43 and A16 milxnaq/78f891e1. Reuse that local binary
and source updater-script, changing only the *three images* to the signed,
reconciled GZH3 UN1CA target-files versions. The updater-script is reused
unchanged, as in the working TachyonOS A15 kernel ZIP. No device is accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "out/r0s_A16_GZH3_HOST_ONLY-target_files.zip"
KERNEL = ROOT / "out/kernel_tmp-exynos2200"
WORK = ROOT / "out/target/r0s/work_dir"
UPDATE_BINARY = KERNEL / "build/update-binary"
UPDATER_SOURCE = KERNEL / "build/updater-script"
KERNEL_PIN = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU_PIN = "8f902aeb16033024143ae36cf711df902cf02fae"
A15_A16_UPDATER_GIT_BLOB = "0a6085a9251b664ed0b591d8457ca2c01afaaa8e"
A16_SCRIPT_GIT_BLOB = "3973dff6043769d063b792c78739c5236a8e808a"
BOOTS = ("boot", "vendor_boot", "dtbo")
MODULES = ("fingerprint.ko", "fingerprint_sysfs.ko", "input_booster_lkm.ko",
           "sec_debug_coredump.ko", "wlan.ko")
CAPS = {"boot": 67108864, "vendor_boot": 33554432, "dtbo": 8388608}
BINARY = "META-INF/com/google/android/update-binary"
SCRIPT = "META-INF/com/google/android/updater-script"
MEMBERS = {BINARY, SCRIPT} | {"files/" + part + ".img" for part in BOOTS}
FIRMWARE = "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"


class Blocked(Exception):
    pass


def need(ok, text):
    if not ok:
        raise Blocked(text)


def digest_stream(stream):
    h = hashlib.sha256()
    for b in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(b)
    return h.hexdigest()


def digest(path):
    with path.open("rb") as f:
        return digest_stream(f)


def blob(path):
    need(path.is_file(), "source missing: " + str(path))
    h = hashlib.sha1()
    h.update(("blob " + str(path.stat().st_size) + "\0").encode())
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def native_name_with_ksu_version(name, release):
    """Preserve upstream kernel/version/date, with a source-derived KSU tag."""
    need(re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", release)
         is not None, "invalid KernelSU Next release tag")
    match = re.fullmatch(
        r"(ExtremeKRNL-[A-Za-z0-9.+-]+)_r0s_KSU_"
        r"(\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2})\.zip", name)
    need(match is not None, "unexpected upstream ExtremeKRNL ZIP name")
    return (match.group(1) + "_r0s_KSUNext-" + release + "_" +
            match.group(2) + ".zip")


def ksu_release():
    """Discover the release tag at the exact KSU commit used by this build."""
    record = KERNEL / "build/out/r0s/.r0s_a16_kernel_host_pass"
    need(record.is_file(), "A16 kernel build provenance record missing")
    entries = dict(re.findall(r"^([a-z_]+)=([^\r\n]*)$", record.read_text(), re.M))
    need(entries.get("ksunext") == KSU_PIN,
         "built kernel KernelSU commit differs from package source pin")
    checkout = KERNEL / "KernelSU-Next"
    head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    need(head.returncode == 0 and head.stdout.strip() == KSU_PIN,
         "KernelSU Next source checkout differs from the compiled build")
    tags = subprocess.run(["git", "-C", str(checkout), "tag", "--points-at", "HEAD"],
                          capture_output=True, text=True)
    need(tags.returncode == 0, "cannot inspect KernelSU Next release tags")
    releases = [tag for tag in tags.stdout.splitlines()
                if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?",
                                tag)]
    need(len(releases) == 1,
         "the built KernelSU commit must have exactly one release tag")
    return releases[0]


def output_path():
    # Use the original kernel build ZIP name; obtain KSU version from its
    # pinned source tag, not a hard-coded string or manager APK name.
    directory = KERNEL / "build/out/r0s"
    matches = sorted(directory.glob("ExtremeKRNL-*_r0s_KSU_*.zip"))
    need(len(matches) == 1, "need exactly one upstream A16 ExtremeKRNL KSU ZIP")
    return ROOT / "out" / native_name_with_ksu_version(
        matches[0].name, ksu_release())


def source_script():
    need(blob(UPDATER_SOURCE) == A16_SCRIPT_GIT_BLOB,
         "A16 upstream recovery updater-script changed")
    text = UPDATER_SOURCE.read_text()
    lines = [s.strip() for s in text.splitlines()
             if not s.lstrip().startswith("#")]
    writes = [line for line in lines if line.startswith('package_extract_file(')]
    expected = {
        f'package_extract_file("files/{part}.img", "/dev/block/by-name/{part}");'
        for part in BOOTS
    }
    need(len(writes) == 3 and set(writes) == expected,
         "upstream ExtremeKRNL 3-image updater no longer matches TachyonOS pattern")
    need(not any(("block_image_update(" in line or
                  "update_dynamic_partitions(" in line or
                  "remove_all_groups" in line) for line in lines),
         "upstream kernel ZIP attempts dynamic-partition operations")
    need("E3099" not in text, "upstream script has unexpected development abort")
    return text.encode()


def check(expected):
    need(re.fullmatch("[0-9a-f]{64}", expected or ""),
         "specify SHA256 for the existing GZH3 target-files archive")
    need(SOURCE.is_file() and digest(SOURCE) == expected,
         "target-files archive SHA256 mismatch")
    need((WORK / "kernel/.r0s_extremekrnl_a16_integrated").is_file(),
         "signed A16 workdir does not have reconciled custom kernel")
    need((ROOT / "out/fw/SM-S901B_EUX/.extracted").read_text().strip() == FIRMWARE,
         "GZH3 source firmware marker missing or changed")
    need(blob(UPDATE_BINARY) == A15_A16_UPDATER_GIT_BLOB,
         "not the proven A15/A16 ExtremeKRNL update-binary")
    source_script()
    for part in BOOTS:
        need((WORK / "kernel" / (part + ".img")).is_file(),
             "reconciled ROM boot-chain missing: " + part)
    for module in MODULES:
        need((WORK / "vendor_dlkm/lib/modules" / module).is_file(),
             "matching module missing from A16 ROM workdir: " + module)
    with zipfile.ZipFile(SOURCE) as z:
        need(len(z.namelist()) == len(set(z.namelist())),
             "target-files duplicate entries")
        for part in BOOTS:
            name = part + ".img"
            need(name in z.namelist() and z.getinfo(name).file_size == CAPS[part],
                 "signed GZH3 " + name + " wrong physical partition size")
        need("vendor_dlkm.img" in z.namelist(),
             "A16 ROM needs existing vendor_dlkm; kernel-only ZIP will NOT include it")
    print("TACHYONOS-PARITY EXTREMEKRNL A16 THREE-IMAGE SOURCE CHECK PASS")
    print("Original ExtremeKRNL updater binary (byte-identical Git blob to A15)")
    print("vendor_dlkm stays in installed ROM; NOT updated by recovery ZIP")
    print("Kernel updater-script kept byte-identical to original ExtremeKRNL")


def audit(expected):
    env = {**os.environ, "PATH": str(ROOT / "out/tools/bin")
           + os.pathsep + os.environ.get("PATH", "")}
    for name in ("audit_target_files_host.sh", "audit_packaged_kernel_modules.sh"):
        print("===== A16 HOST AUDIT: " + name + " =====", flush=True)
        r = subprocess.run(["bash", str(ROOT / "scripts/r0s" / name),
                            str(SOURCE), expected], env=env)
        need(r.returncode == 0, "current A16 target-files/modules gate failed: " + name)


def package_verify(path, expected=None):
    need(path.is_file() and path.stat().st_size > 0, "kernel ZIP not present")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and set(names) == MEMBERS,
             "kernel ZIP must have *only* TachyonOS-style updater + 3 images")
        need(z.testzip() is None, "kernel ZIP CRC failed")
        need(hashlib.sha1(b"blob " + str(z.getinfo(BINARY).file_size).encode()
                          + b"\0" + z.read(BINARY)).hexdigest()
             == A15_A16_UPDATER_GIT_BLOB,
             "kernel ZIP update-binary is not original ExtremeKRNL")
        text = z.read(SCRIPT)
        need(text == source_script(), "updater-script differs from original ExtremeKRNL")
        need(b"E3099" not in text, "unexpected E3099 development abort")
        need(not any("vendor_dlkm" in name for name in names),
             "kernel-only ZIP must not update vendor_dlkm")
        if expected is not None:
            need(SOURCE.is_file() and digest(SOURCE) == expected,
                 "source GZH3 archive changed since kernel ZIP built")
            with zipfile.ZipFile(SOURCE) as src:
                for part in BOOTS:
                    key = part + ".img"
                    with src.open(key) as f:
                        h = digest_stream(f)
                    with z.open("files/" + key) as f:
                        need(digest_stream(f) == h,
                             "recovery " + key + " differs from signed GZH3 source")
        else:
            for part in BOOTS:
                need(z.getinfo("files/" + part + ".img").file_size == CAPS[part],
                     "kernel ZIP image exceeds/undershoots reference partition cap")
    print("A16 EXTREMEKRNL TWRP 3-IMAGE ZIP STRUCTURE VERIFY PASS")
    print("TachyonOS updater pattern retained; no vendor_dlkm payload")


def build(expected):
    output = output_path()
    report_path = output.with_suffix(".provenance.json")
    need(not output.exists() and not report_path.exists(),
         "prior output exists; refusing overwrite")
    check(expected)
    audit(expected)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Same five recovery ZIP members as TachyonOS/ExtremeKRNL:
    # update-binary, updater-script, and boot/vendor_boot/dtbo images.
    with tempfile.TemporaryDirectory(prefix=".r0s_extremekrnl_twrp_",
                                     dir=output.parent) as folder:
        staging = Path(folder) / "kernel.zip"
        with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(
            staging, "w", allowZip64=True
        ) as out:
            out.write(UPDATE_BINARY, BINARY, compress_type=zipfile.ZIP_STORED)
            out.writestr(SCRIPT, source_script())
            for part in BOOTS:
                with source.open(part + ".img") as f, out.open(
                    "files/" + part + ".img", "w", force_zip64=True
                ) as writer:
                    for b in iter(lambda: f.read(1024 * 1024), b""):
                        writer.write(b)
        package_verify(staging, expected)
        need(not output.exists() and not report_path.exists(),
             "output appeared while generating")
        staging.replace(output)
    report = {
        "status": "PACKAGED",
        "device": "SM-S901B", "android_api": 36,
        "kernel_source": KERNEL_PIN, "ksunext_source": KSU_PIN,
        "ksunext_release": ksu_release(),
        "target_files_sha256": expected,
        "kernel_zip_sha256": digest(output),
        "format": "original_TachyonOS_ExtremeKRNL_three_image_updater",
        "module_update": "none; verify unchanged ABI compatibility",
        "a16_device_qualified": False,
    }
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("A16 EXTREMEKRNL / KSU NEXT 3-IMAGE ZIP HOST PACKAGE PASS")
    print("ZIP: " + str(output))
    print("SHA256: " + report["kernel_zip_sha256"])
    print("Original kernel ZIP layout and updater-script preserved")



def ci_build():
    """Package newly built A16 GZH3 hybrid using the canonical ZIP contract.

    This mode avoids a synthetic full ROM workdir and full target-files ZIP.
    The same reconciler has already verified native GZH3 donor metadata.
    Sign the three candidate images using the *same* AVB test key and
    add_hash_footer settings as scripts/utils/install_utils.sh.
    """
    from integrate_extremekrnl_a16 import MODULES as INSTALLED_MODULES
    out = output_path()  # Reuses the actual upstream filename + pinned KSU tag.
    report_path = out.with_suffix(".provenance.json")
    need(not out.exists() and not report_path.exists(),
         "existing kernel ZIP/provenance cannot be overwritten")
    need(blob(UPDATE_BINARY) == A15_A16_UPDATER_GIT_BLOB,
         "original ExtremeKRNL updater binary differs from canonical")
    source_script()
    candidate = ROOT / "out/r0s_A16_ExtremeKRNL_KSU_hybrid_candidate"
    need((candidate / "NOT_FLASHABLE.txt").is_file(),
         "existing A16 reconciler did not produce a verified hybrid")
    need((ROOT / "ci_inputs/r0s_a16_gzh3_donors.sha256").is_file(),
         "A16 donor SHA256 manifest missing")

    # This ZIP intentionally does NOT carry vendor_dlkm; don't silently
    # ship a kernel whose modules differ from the installed A16 baseline.
    modules = {}
    for name, baseline_hash in INSTALLED_MODULES.items():
        item = candidate / "vendor_dlkm/lib/modules" / name
        need(item.is_file() and digest(item) == baseline_hash,
             "installed vendor_dlkm module differs from cloud build: " + name)
        modules[name] = baseline_hash

    key = ROOT / "security/avb/testkey_rsa4096.pem"
    need(key.is_file(), "canonical UN1CA AVB test key missing")
    need(shutil.which("avbtool") is not None, "avbtool missing")
    need(shutil.which("unpack_bootimg") is not None, "unpack_bootimg missing")
    out.parent.mkdir(parents=True, exist_ok=True)
    signed_hashes = {}
    with tempfile.TemporaryDirectory(prefix=".r0s_ci_signed_",
                                     dir=out.parent) as temp:
        tempdir = Path(temp)
        for part in BOOTS:
            raw = candidate / (part + ".img")
            need(raw.is_file() and 0 < raw.stat().st_size < CAPS[part],
                 "missing or oversized reconciled " + part)
            signed = tempdir / (part + ".img")
            shutil.copyfile(raw, signed)
            # The host's original SIGN_IMAGE_WITH_AVB logic:
            # add_hash_footer, SHA256_RSA4096, SHA256, partition size/name.
            result = subprocess.run(["avbtool", "info_image", "--image", str(signed)],
                                    capture_output=True)
            need(result.returncode != 0, "hybrid input already carries AVB: " + part)
            cmd = ["avbtool", "add_hash_footer",
                   "--image", str(signed),
                   "--partition_size", str(CAPS[part]),
                   "--partition_name", part,
                   "--hash_algorithm", "sha256",
                   "--algorithm", "SHA256_RSA4096",
                   "--key", str(key)]
            need(subprocess.run(cmd, capture_output=True).returncode == 0,
                 "canonical A16 AVB hash footer signing failed: " + part)
            check = subprocess.run(["avbtool", "info_image", "--image", str(signed)],
                                   capture_output=True, text=True)
            need(check.returncode == 0 and signed.stat().st_size == CAPS[part],
                 "invalid signed A16 image/partition length: " + part)
            need(re.search(r"Partition Name:\s+" + re.escape(part) + r"(?:\s|$)",
                           check.stdout, re.M) is not None,
                 "signed image partition name mismatch: " + part)
            signed_hashes[part] = digest(signed)

        # Same original FIVE-MEMBER recovery ZIP as build() and host reference.
        with zipfile.ZipFile(tempdir / "kernel.zip", "w", allowZip64=True) as archive:
            archive.write(UPDATE_BINARY, BINARY, compress_type=zipfile.ZIP_STORED)
            archive.writestr(SCRIPT, source_script())
            for part in BOOTS:
                with (tempdir / (part + ".img")).open("rb") as inp:
                    with archive.open("files/" + part + ".img",
                                      "w", force_zip64=True) as writer:
                        for chunk in iter(lambda: inp.read(1048576), b""):
                            writer.write(chunk)
        package_verify(tempdir / "kernel.zip")
        need(not out.exists(), "kernel ZIP destination occupied")
        (tempdir / "kernel.zip").replace(out)

    report = {
        "status": "A16_GZH3_CLOUD_PACKAGE_HOST_PASS_BOARD_DEFERRED",
        "device": "SM-S901B", "android_api": 36,
        "kernel_source": KERNEL_PIN, "ksunext_source": KSU_PIN,
        "ksunext_release": ksu_release(),
        "donor_release": "r0s-a16-gzh3-donors-v1",
        "avb_method": "UN1CA_SIGN_IMAGE_WITH_AVB_SHA256_RSA4096_TESTKEY",
        "signed_images_sha256": signed_hashes,
        "installed_vendor_dlkm_sha256": modules,
        "kernel_zip_sha256": digest(out),
        "a16_device_qualified": False,
    }
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("A16 GZH3 RECONCILED AVB-SIGNED CLOUD KERNEL ZIP HOST PACKAGE PASS")
    print("BOARD DEFERRED; vendor_dlkm SHA256 parity PASS")
    print("ZIP: " + str(out))
    print("SHA256: " + report["kernel_zip_sha256"])

def ci_verify():
    out = output_path()
    report = json.loads(out.with_suffix(".provenance.json").read_text())
    need(report.get("status") == "A16_GZH3_CLOUD_PACKAGE_HOST_PASS_BOARD_DEFERRED",
         "no CI A16 signed package provenance")
    need(report.get("kernel_zip_sha256") == digest(out), "CI ZIP hash drift")
    package_verify(out)
    with zipfile.ZipFile(out) as z:
        for part, expected in report["signed_images_sha256"].items():
            with z.open("files/" + part + ".img") as stream:
                need(digest_stream(stream) == expected, "signed image drift: " + part)
    print("A16 GZH3 SIGNED CLOUD KERNEL ZIP HOST VERIFY PASS — BOARD DEFERRED")

def self_test():
    source_script() if UPDATE_BINARY.is_file() and UPDATER_SOURCE.is_file() else None
    need(len(BOOTS) == 3 and len(MEMBERS) == 5,
         "unexpected kernel ZIP layout")
    need(set(BOOTS) == {"boot", "vendor_boot", "dtbo"},
         "A15-to-A16 ZIP image list drift")
    need(len(KERNEL_PIN) == len(KSU_PIN) == 40 and len(A15_A16_UPDATER_GIT_BLOB) == 40,
         "bad provenance pin")
    need(b"E3099" not in source_script() if UPDATER_SOURCE.is_file()
         else True, "E3099 was added to the kernel updater")
    # Pure naming fixtures: CI must not need an actual kernel checkout.
    need(native_name_with_ksu_version(
        "ExtremeKRNL-v2.5_r0s_KSU_13-10-2026_21-00-00.zip",
        "v3.4.1") ==
        "ExtremeKRNL-v2.5_r0s_KSUNext-v3.4.1_13-10-2026_21-00-00.zip",
        "source-version filename formatting failed")
    need(native_name_with_ksu_version(
        "ExtremeKRNL-v3.0_r0s_KSU_14-10-2026_02-03-04.zip",
        "v4.0.0") ==
        "ExtremeKRNL-v3.0_r0s_KSUNext-v4.0.0_14-10-2026_02-03-04.zip",
        "filename was incorrectly pinned to a specific KSU version")
    for bad in ("v3.4.1/other", "3.4.1", ""):
        try:
            native_name_with_ksu_version(
                "ExtremeKRNL-v2.5_r0s_KSU_13-10-2026_21-00-00.zip", bad)
        except Blocked:
            pass
        else:
            raise AssertionError("invalid KernelSU tag accepted: " + bad)
    print("TachyonOS parity ZIP fixture PASS — 3 images, same recovery installer")
    print("No kernel source/ROM/recovery build or device writes")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("self-test", "check", "build", "verify", "ci-build", "ci-verify"))
    p.add_argument("sha256", nargs="?", help="existing signed A16 target-files SHA256")
    args = p.parse_args()
    if args.mode == "self-test":
        self_test()
    elif args.mode == "check":
        check(args.sha256)
    elif args.mode == "ci-build":
        ci_build()
    elif args.mode == "ci-verify":
        ci_verify()
    elif args.mode == "build":
        build(args.sha256)
    else:
        output = output_path()
        report_path = output.with_suffix(".provenance.json")
        need(report_path.is_file(), "kernel ZIP provenance record absent")
        report = json.loads(report_path.read_text())
        need(report["kernel_zip_sha256"] == digest(output),
             "kernel ZIP SHA256 differs from build report")
        package_verify(output, report["target_files_sha256"])


if __name__ == "__main__":
    try:
        main()
    except (Blocked, OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        print("A16 EXTREMEKRNL RECOVERY ZIP HOLD: " + str(exc), file=sys.stderr)
        sys.exit(2)
