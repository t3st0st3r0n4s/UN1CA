#!/usr/bin/env python3
"""Verify and publish ONLY the existing A16 kernel ZIP as CI reference.

NO host firmware, signing key, entire target-files ZIP, or full ROM workdir
is uploaded. The five-member existing ZIP is a publicly downloadable GitHub
pre-release asset. Upload first, THEN commit its SHA manifest to the CI branch
to trigger reference packaging. Nothing is flashed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

REPO = "t3st0st3r0n4s/UN1CA"
BRANCH = "sixteen-r0s-kernel-ci"
TAG = "r0s-a16-kernel-reference-v1"
KERNEL = "78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
KSU = "8f902aeb16033024143ae36cf711df902cf02fae"
TF_SHA = "4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a"
UB_BLOB = "0a6085a9251b664ed0b591d8457ca2c01afaaa8e"
US_BLOB = "3973dff6043769d063b792c78739c5236a8e808a"
REF_NAME = "ExtremeKRNL-v2.5_r0s_KSUNext-v3.4.1_13-10-2026_19-42-41.zip"
NAMES = ("META-INF/com/google/android/update-binary",
         "META-INF/com/google/android/updater-script",
         "files/boot.img", "files/vendor_boot.img", "files/dtbo.img")
CAPS = {"boot.img": 67108864, "vendor_boot.img": 33554432,
        "dtbo.img": 8388608}


def need(ok: bool, msg: str):
    if not ok:
        raise RuntimeError("A16 REFERENCE HOLD: " + msg)


def sha_stream(source):
    h = hashlib.sha256()
    for part in iter(lambda: source.read(1024 * 1024), b""):
        h.update(part)
    return h.hexdigest()


def sha(path: Path):
    with path.open("rb") as f:
        return sha_stream(f)


def blob(content: bytes):
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\\0" + content).hexdigest()


def cmd(*argv, stdin=None, check=True):
    r = subprocess.run(argv, input=stdin, text=True, capture_output=True)
    if check:
        need(r.returncode == 0, "command failed: " + " ".join(argv[:4])
             + "\\n" + r.stderr[-1500:])
    return r


def check_zip(path: Path):
    need(path.is_file() and path.name == REF_NAME,
         "existing A16 reference ZIP missing or unexpected filename")
    data = {}
    with zipfile.ZipFile(path) as z:
        files = [i.filename for i in z.infolist() if not i.is_dir()]
        need(len(files) == 5 and set(files) == set(NAMES),
             "reference ZIP must have only the 3 images and 2 updater entries")
        need(z.testzip() is None, "reference ZIP CRC invalid")
        need(blob(z.read(NAMES[0])) == UB_BLOB, "updater binary differs from pinned source")
        script = z.read(NAMES[1])
        need(blob(script) == US_BLOB, "updater script differs from pinned source")
        need(b"E3099" not in script, "reference ZIP has development abort")
        expected = {
            f'package_extract_file("files/{i}", "/dev/block/by-name/{i[:-4]}");'
            for i in CAPS
        }
        actual = {s.strip() for s in script.decode().splitlines()
                  if s.strip().startswith("package_extract_file(")}
        need(actual == expected, "unexpected updater partition write list")
        for name in CAPS:
            item = z.getinfo("files/" + name)
            need(item.file_size == CAPS[name], "reference image isn't signed padded partition-size: " + name)
            with z.open("files/" + name) as stream:
                data[name] = {"bytes": item.file_size, "sha256": sha_stream(stream)}
        with z.open("files/boot.img") as f:
            need(f.read(8) == b"ANDROID!", "boot.img Android header invalid")
        with z.open("files/vendor_boot.img") as f:
            need(f.read(8) == b"VNDRBOOT", "vendor_boot.img Android header invalid")
    return data


def check_target_files(path: Path, images):
    need(path.is_file(), "pinned GZH3 target-files ZIP not available: " + str(path))
    need(sha(path) == TF_SHA, "source GZH3 target-files SHA256 differs from host PASS")
    with zipfile.ZipFile(path) as z:
        for name, info in images.items():
            need(name in z.namelist(), "target-files missing " + name)
            need(z.getinfo(name).file_size == info["bytes"], "target-files image size drift: " + name)
            with z.open(name) as stream:
                need(sha_stream(stream) == info["sha256"],
                     "reference ZIP differs from signed target-files: " + name)


def check_provenance(path: Path, expected):
    need(path.is_file(), "existing kernel ZIP provenance file missing: " + str(path))
    report = json.loads(path.read_text())
    need(report.get("kernel_source") == KERNEL, "kernel provenance pin changed")
    need(report.get("ksunext_source") == KSU, "KSU provenance pin changed")
    need(report.get("ksunext_release") == "v3.4.1", "KSU release drift")
    need(report.get("target_files_sha256") == TF_SHA, "target-files provenance SHA drift")
    need(report.get("kernel_zip_sha256") == expected, "host ZIP digest differs from provenance")


def publish(zip_path, manifest, output):
    need(cmd("gh", "auth", "status", check=False).returncode == 0,
         "gh CLI not authenticated (run gh auth login)")
    # A public pre-release is intentional: user explicitly requested GitHub hosting.
    view = cmd("gh", "release", "view", TAG, "--repo", REPO, "--json",
               "assets", check=False)
    if view.returncode != 0:
        cmd("gh", "release", "create", TAG, str(zip_path),
            "--repo", REPO, "--target", BRANCH, "--prerelease",
            "--title", "A16 r0s host boot-chain reference (not board qualified)",
            "--notes", "Existing, previously host-verified 3-image UN1CA A16 kernel ZIP. "
                       "Reference input for cloud packaging only. Contains Samsung-derived "
                       "boot images. Public download. Not a proven device update.")
    else:
        existing = json.loads(view.stdout)
        name = [a for a in existing.get("assets", [])
                if a.get("name") == REF_NAME]
        need(len(name) == 1, "release exists but the exact expected asset is missing")
        local = output / ("release_check_" + REF_NAME)
        cmd("gh", "release", "download", TAG, "--repo", REPO,
            "--pattern", REF_NAME, "--dir", str(output))
        downloaded = output / REF_NAME
        need(downloaded.is_file() and sha(downloaded) == manifest["reference_zip_sha256"],
             "existing GitHub release reference differs from the local host ZIP")
        downloaded.unlink()

    content = json.dumps(manifest, indent=2, sort_keys=True) + "\\n"
    api = "repos/" + REPO + "/contents/ci_inputs/a16_kernel_reference.json"
    existing = cmd("gh", "api", api + "?ref=" + BRANCH, check=False)
    args = ["gh", "api", "-X", "PUT", api, "-f",
            "message=ci(r0s): bind verified A16 host kernel reference",
            "-f", "branch=" + BRANCH,
            "-f", "content=" + base64.b64encode(content.encode()).decode()]
    if existing.returncode == 0:
        old = json.loads(existing.stdout)
        need(old.get("type") == "file", "unexpected manifest API entry")
        old_content = base64.b64decode(old["content"]).decode()
        need(old_content != content, "manifest already published; no new push needed")
        args.extend(["-f", "sha=" + old["sha"]])
    elif "404" not in existing.stderr:
        need(False, "cannot inspect existing manifest: " + existing.stderr[-800:])
    cmd(*args)
    print("PUBLISHED: " + REPO + " " + TAG)
    print("MANIFEST COMMITTED: " + BRANCH + "/ci_inputs/a16_kernel_reference.json")
    print("GitHub Actions package-reference workflow triggered by the manifest push.")


def main():
    root = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path,
                   default=root / "out" / REF_NAME)
    p.add_argument("--target-files", type=Path,
                   default=root / "out/r0s_A16_GZH3_HOST_ONLY-target_files.zip")
    p.add_argument("--publish", action="store_true")
    args = p.parse_args()
    imgs = check_zip(args.reference)
    check_target_files(args.target_files, imgs)
    checksum = sha(args.reference)
    check_provenance(args.reference.with_suffix(".provenance.json"), checksum)
    manifest = {
        "schema": 1, "device": "SM-S901B", "android": 16,
        "input_status": "SIGNED_HOST_REFERENCE_NOT_BOARD_QUALIFIED",
        "repository": REPO, "release_tag": TAG,
        "reference_filename": REF_NAME, "reference_zip_sha256": checksum,
        "target_files_sha256": TF_SHA, "kernel_source": KERNEL,
        "ksunext_source": KSU, "ksunext_release": "v3.4.1",
        "images": imgs, "input_has_private_signing_key": False,
    }
    print("A16 SIGNED REFERENCE 3-IMAGE SOURCE / PROVENANCE PASS")
    print("ZIP:", args.reference)
    print("SHA256:", checksum)
    output = root / "out/r0s_kernel_reference"
    output.mkdir(exist_ok=True)
    (output / "a16_kernel_reference.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\\n")
    print("Manifest:", output / "a16_kernel_reference.json")
    if args.publish:
        publish(args.reference, manifest, output)
    else:
        print("DRY RUN: nothing uploaded. Add --publish to upload public release and trigger CI.")

if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, KeyError, ValueError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
