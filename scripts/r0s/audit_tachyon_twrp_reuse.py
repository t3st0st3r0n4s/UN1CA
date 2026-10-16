#!/usr/bin/env python3
"""Unify UN1CA A16's updater contract with the *existing* TachyonOS TWRP.

No TWRP source checkout, recovery image repack, flash, ROM build, or mount.
Compare the recovery.img bytes inside both extant TARs, not their TAR hashes:
TachyonOS's repo TAR is vbmeta_only; the previously device-tested candidate
is logo_vbmeta. Only equal embedded recovery bytes prove binary reuse.
Also check the GZH3 installer maps the five native EROFS logical partitions
through the unchanged legacy block updater.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REPO_TAR = Path.home() / "android/tachyonos_s901b/TWRP/S901B_twrp_vbmeta_only.tar"
TESTED_TAR = Path.home() / "android/S22-ROM/S901B_twrp_logo_vbmeta.tar"
REPO_BLOB_SHA1 = "9a164f92b09cd7975e8c1341b11ea5e01abd3b94"
REPO_TAR_SIZE = 67_174_400
TESTED_TAR_SHA256 = "f82b9612d92786971609895facb703906744d9a617e673f1cd148e671735d830"
LOGICAL = ("system", "vendor", "product", "odm", "vendor_dlkm")
RAW = ("boot", "vendor_boot", "dtbo")


class Hold(Exception):
    pass


def need(yes, why):
    if not yes:
        raise Hold(why)


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha(path):
    h = hashlib.sha1()
    h.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_identity(path):
    """Bounded TAR member inventory and streaming recovery.img digest only."""
    need(path.is_file(), "TWRP archive not found: " + str(path))
    names = []
    with tarfile.open(path, "r:*") as archive:
        for item in archive.getmembers():
            need(item.isfile() and item.name in
                 ("recovery.img", "vbmeta.img", "up_param.bin"),
                 "unrecognized or unsafe TAR member: " + item.name)
            need(item.name not in names, "duplicate TAR member")
            names.append(item.name)
        need("recovery.img" in names, "TWRP TAR has no recovery.img")
        entry = archive.getmember("recovery.img")
        need(0 < entry.size <= 100_663_296, "recovery image exceeds bounded size")
        member = archive.extractfile(entry)
        need(member is not None, "recovery image cannot be streamed")
        with member:
            h = hashlib.sha256()
            amount = 0
            for chunk in iter(lambda: member.read(1024 * 1024), b""):
                amount += len(chunk)
                h.update(chunk)
            need(amount == entry.size, "TWRP recovery image stream truncated")
        return {"files": names, "recovery_bytes": amount, "recovery_sha256": h.hexdigest()}


def check_un1ca_updater():
    fstab = ROOT / "target/r0s/installer/recovery.fstab"
    text = fstab.read_text()
    logical = {}
    raw = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        need(len(fields) >= 4, "malformed block locator map line: " + line)
        device, mount, fstype = fields[:3]
        if mount.startswith("/") and mount[1:] in LOGICAL:
            need(mount not in logical, "duplicate logical mapping " + mount)
            logical[mount] = (device, fstype)
        elif mount in ("/boot", "/vendor_boot", "/dtbo"):
            need(mount not in raw, "duplicate boot-chain mapping " + mount)
            raw[mount] = (device, fstype)
        elif mount == "/system_ext":
            raise Hold("GZH3 must not invent a separate system_ext logical partition")
    for p in LOGICAL:
        need(logical.get("/" + p) == (p, "erofs") or
             (p == "odm" and logical.get("/odm") == ("odm", "auto")),
             "UN1CA logical map mismatches native GZH3: " + p)
    for p in RAW:
        need(raw.get("/" + p) == ("/dev/block/by-name/" + p, "emmc"),
             "UN1CA raw boot-chain locator drift: " + p)
    updater = (ROOT / "scripts/internal/build_full_ota_zip.sh").read_text()
    need('update_dynamic_partitions(package_extract_file("dynamic_partitions_op_list")'
         in updater, "legacy updater no longer generates dynamic partition metadata")
    need('block_image_update(' in updater and
         'GET_DEVICE_FROM_MOUNTPOINT "/$p"' in updater,
         "legacy updater no longer updates mapped logical partitions")
    util = (ROOT / "scripts/utils/install_utils.sh").read_text()
    need('map_partition(' in util, "updater no longer maps dynamic logical devices")
    need((ROOT / "scripts/r0s/build_full_ota_guarded.py").is_file(),
         "guarded UN1CA OTA builder absent")
    need((ROOT / "scripts/r0s/audit_ota_updater_twrp.py").is_file(),
         "existing physical-probe updater ABI validation script absent")
    print("UN1CA GZH3 LEGACY TWRP BLOCK-UPDATER CONTRACT PASS (SOURCE ONLY)")
    print("Exactly five native logical partitions; EROFS preserved; no system_ext")
    print("BOARD remains unverified; the existing recovery is not replaced")
    print("Physical TWRP updater-launch PASS is retained separately in project records")
    print("Dynamic partition writing and A16 normal boot remain BOARD DEFERRED")


def self_test():
    with tempfile.TemporaryDirectory() as d:
        tarpath = Path(d) / "example.tar"
        with tarfile.open(tarpath, "w") as archive:
            import io
            payload = b"SAFE-RECOVERY-IDENTITY-FIXTURE"
            meta = tarfile.TarInfo("recovery.img")
            meta.size = len(payload)
            archive.addfile(meta, io.BytesIO(payload))
        a = extract_identity(tarpath)
        need(a["recovery_sha256"] == hashlib.sha256(payload).hexdigest(),
             "streaming fixture hash failed")
        need(a["recovery_bytes"] == len(payload), "streaming fixture size failed")
        need("recovery.img" in a["files"], "TAR member inventory failed")
        test = Path(d) / "blob"
        test.write_bytes(payload)
        expected = hashlib.sha1(b"blob " + str(len(payload)).encode()
                                 + b"\0" + payload).hexdigest()
        need(git_blob_sha(test) == expected, "Git blob fingerprint algorithm failed")
    print("TachyonOS TWRP existing-binary reuse fixtures PASS (no ROM/device writes)")


def compare(repo, tested):
    need(repo.is_file(), "TachyonOS TWRP TAR not local. Supply --tachyon-tar "
         "from its existing clone; do not rebuild recovery.")
    need(tested.is_file(), "previously tested TWRP TAR absent; supply --tested-tar")
    need(repo.stat().st_size == REPO_TAR_SIZE and
         git_blob_sha(repo) == REPO_BLOB_SHA1,
         "TachyonOS TAR differs from GitHub r0s-fyi3 pinned Git blob")
    need(sha256_file(tested) == TESTED_TAR_SHA256,
         "installed/recovery-audited TWRP reference TAR differs from prior pin")
    a, b = extract_identity(repo), extract_identity(tested)
    print("TachyonOS GitHub TAR files: " + ", ".join(a["files"]))
    print("Prior physically tested TAR files: " + ", ".join(b["files"]))
    print("TachyonOS embedded recovery.img SHA256: " + a["recovery_sha256"])
    print("Tested candidate embedded recovery.img SHA256: " + b["recovery_sha256"])
    need(a["recovery_sha256"] == b["recovery_sha256"] and
         a["recovery_bytes"] == b["recovery_bytes"],
         "TWRP binaries DIFFER. Do not assume GitHub TAR is the same recovery "
         "as the installed one; keep the proven installed TWRP unchanged.")
    print("TACHYONOS TWRP REUSE: RECOVERY.IMG BYTE-IDENTICAL TO PRIOR TESTED TAR")
    print("vbmeta/up_param TAR differences do not affect recovery.img identity")
    check_un1ca_updater()
    print("EXISTING TWRP / UN1CA A16 SOURCE CONTRACT HOST PASS — FLASH STILL LOCKED")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--source-only", action="store_true",
                   help="check current UN1CA updater without local TARs")
    p.add_argument("--tachyon-tar", type=Path, default=REPO_TAR)
    p.add_argument("--tested-tar", type=Path, default=TESTED_TAR)
    args = p.parse_args()
    need(sum([args.self_test, args.source_only]) <= 1, "select only one mode")
    if args.self_test:
        self_test()
    elif args.source_only:
        check_un1ca_updater()
    else:
        compare(args.tachyon_tar.expanduser(), args.tested_tar.expanduser())


if __name__ == "__main__":
    try:
        main()
    except (Hold, OSError, tarfile.TarError) as exc:
        print("TACHYON TWRP UNIFICATION HOLD: " + str(exc), file=sys.stderr)
        sys.exit(2)
