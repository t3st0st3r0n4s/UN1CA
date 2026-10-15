#!/usr/bin/env python3
"""Install the matching stable KernelSU Next one-shot manager in UN1CA A16.

--check and --self-test are read-only. --verify checks a prepared workdir.
--apply is invoked by r0s's late module, after the kernel integration.
--apply-existing is a guarded one-time catch-up on an already built workdir;
it avoids unnecessarily rebuilding Android partitions or the kernel.
This script never touches an Android device, builds an OTA, or flashes.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import json
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "out/target/r0s/work_dir"
STAGE = ROOT / "staging/r0s/ksunext"
CACHE = ROOT / "out/target/r0s/ksunext_manager_cache"
SYSTEM = WORK / "system/system"
FS_CONFIG = WORK / "configs/fs_config-system"
FILE_CONTEXT = WORK / "configs/file_context-system"
PAYLOAD = SYSTEM / "etc/unica/ksunext/manager_payload.bin"
INSTALLER = SYSTEM / "etc/unica/ksunext/install_manager.sh"
RC = SYSTEM / "etc/init/unica_ksunext_manager.rc"
KERNEL_MARK = WORK / "kernel/.r0s_extremekrnl_a16_integrated"
INIT_LINE = ("    exec_background u:r:ksu:s0 root root -- /system/bin/sh "
             "/system/etc/unica/ksunext/install_manager.sh")
INSTALL_PATH = "system/etc/unica/ksunext/"
ENTRIES = {
    "system/etc/unica": "0 0 755 capabilities=0x0",
    "system/etc/unica/ksunext": "0 0 755 capabilities=0x0",
    INSTALL_PATH + "manager_payload.bin": "0 0 644 capabilities=0x0",
    INSTALL_PATH + "install_manager.sh": "0 0 644 capabilities=0x0",
    "system/etc/init/unica_ksunext_manager.rc": "0 0 644 capabilities=0x0",
}
CONTEXTS = {
    "/system/etc/unica": "u:object_r:system_file:s0",
    "/system/etc/unica/ksunext": "u:object_r:system_file:s0",
    "/system/etc/unica/ksunext/manager_payload\\.bin": "u:object_r:system_file:s0",
    "/system/etc/unica/ksunext/install_manager\\.sh": "u:object_r:system_file:s0",
    "/system/etc/init/unica_ksunext_manager\\.rc": "u:object_r:system_file:s0",
}


class Blocked(Exception):
    pass


def need(ok, message):
    if not ok:
        raise Blocked(message)


def hash_file(path):
    need(path.is_file() and path.stat().st_size > 0,
         "missing/empty: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_manifest():
    content = (STAGE / "manifest.env").read_text()
    result = dict(re.findall(r'^([A-Z0-9_]+)="([^"]*)"$', content, re.M))
    for key, expected in (("A16_MANAGER_PRELOAD_ENABLED", "true"),
                          ("A16_ROOT_SELINUX_QUALIFIED", "false"),
                          ("A16_MANAGER_RUNTIME_QUALIFIED", "false"),
                          ("A16_FLASH_PROMOTION_ALLOWED", "false")):
        need(result.get(key) == expected, "manager staging policy drift: " + key)


def manager_release():
    """Match the current compiled KSU tag to its official signed-release digest."""
    from integrate_extremekrnl_a16 import selected_ksu_pin
    kernel = ROOT / "out/kernel_tmp-exynos2200/KernelSU-Next"
    pin = selected_ksu_pin()
    need("ksu=" + pin in KERNEL_MARK.read_text().splitlines(),
         "ROM integration and current KernelSU build use different commits")
    head = subprocess.run(["git", "-C", str(kernel), "rev-parse", "HEAD"],
                          text=True, capture_output=True, check=True).stdout.strip()
    need(head == pin, "manager and compiled KernelSU commits differ")
    tags = subprocess.run(["git", "-C", str(kernel), "tag", "--points-at", "HEAD"],
                          text=True, capture_output=True, check=True).stdout.splitlines()
    stable = [t for t in tags if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", t)]
    need(len(stable) == 1, "compiled KernelSU commit needs one stable release tag")
    tag = stable[0]
    url = "https://api.github.com/repos/KernelSU-Next/KernelSU-Next/releases/tags/" + tag
    request = Request(url, headers={"Accept": "application/vnd.github+json",
                                    "User-Agent": "UN1CA-r0s-manager"})
    with urlopen(request, timeout=20) as response:
        release = json.load(response)
    need(release.get("tag_name") == tag and not release.get("prerelease"),
         "manager release does not match compiled stable KernelSU")
    matches = []
    for asset in release.get("assets", []):
        name = asset["name"]
        build = re.fullmatch(r"KernelSU_Next_" + re.escape(tag) +
                             r"-spoofed_([0-9]+)-release\.apk", name)
        if build:
            matches.append((name, build.group(1), asset))
    need(len(matches) == 1, "expected one official spoofed manager APK")
    name, build, asset = matches[0]
    digest = asset.get("digest", "")
    need(re.fullmatch(r"sha256:[a-f0-9]{64}", digest) is not None,
         "official manager release SHA256 missing")
    need(asset["browser_download_url"].startswith(
         "https://github.com/KernelSU-Next/KernelSU-Next/releases/download/" +
         tag + "/"), "manager asset URL differs from official release")
    return {"name": name, "build": build, "url": asset["browser_download_url"],
            "sha256": digest.split(":", 1)[1], "tag": tag}


def installer_bytes(build=None):
    text = (STAGE / "install_manager.sh").read_text()
    need('MARKER="/data/local/tmp/.unica_ksunext_manager_@BUILD@_installed"' in text,
         "release-derived manager marker template missing")
    need('PAYLOAD="/system/etc/unica/ksunext/manager_payload.bin"' in text,
         "system APK path changed")
    need('/system/bin/pm install -r "$TEMP"' in text, "pm install -r removed")
    need('[ -f "$MARKER" ] && exit 0' in text, "one-shot marker missing")
    need('if /system/bin/pm install -r "$TEMP"; then' in text,
         "install success handling changed")
    need(text.startswith("#!/system/bin/sh\n"), "Android shell header missing")
    # A staging-only comment must not be copied verbatim to the live ROM.
    lines = [line for line in text.splitlines()
             if not line.startswith("# STAGED ONLY")
             and not line.startswith("# Derived from TachyonOS")]
    rendered = "\n".join(lines) + "\n"
    return rendered.replace("@BUILD@", build).encode() if build else rendered.encode()


def init_bytes():
    text = (STAGE / "unica_ksunext_manager.rc").read_text()
    need("on property:sys.boot_completed=1" in text, "boot trigger missing")
    need(INIT_LINE in text, "init u:r:ksu:s0 invocation drift")
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    return ("\n".join(lines).strip() + "\n").encode()


def check_inputs():
    read_manifest()
    installer_bytes()
    init_bytes()
    need(KERNEL_MARK.is_file(), "custom A16 kernel integration marker missing")
    need(FS_CONFIG.is_file() and FILE_CONTEXT.is_file(),
         "workdir filesystem metadata missing")
    need((WORK / "system/system/build.prop").is_file()
         and "ro.build.version.sdk=36" in (WORK / "system/system/build.prop").read_text().splitlines(),
         "not an Android 16 system workdir")
    lock = (ROOT / "target/r0s/installer/assertions.edify").read_text()
    need('abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");'
         in lock, "installer E3099 protection absent")
    print("KernelSU Next one-shot manager source/workdir CHECK PASS")


def apk(release):
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / release["name"]
    expected = release["sha256"]
    if target.exists():
        need(hash_file(target) == expected, "cached manager APK SHA256 mismatch")
        return target
    with tempfile.NamedTemporaryFile(prefix=".manager.", dir=CACHE, delete=False) as tmp:
        partial = Path(tmp.name)
    try:
        proc = subprocess.run(
            ["curl", "-fL", "--retry", "3", "--retry-delay", "2",
             "--connect-timeout", "20", "-o", str(partial), release["url"]],
            check=False)
        need(proc.returncode == 0, "manager download failed")
        need(hash_file(partial) == expected,
             "official KernelSU Next manager release SHA256 mismatch")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    print("Official KernelSU Next " + release["tag"] + " manager SHA256 PASS")
    return target


def prepare_text(old, records):
    lines = old.splitlines()
    for key, value in records.items():
        matching = [line for line in lines if line.strip().startswith(key + " ")]
        need(not matching or matching == [key + " " + value],
             "conflicting workdir metadata for " + key)
        if not matching:
            lines.append(key + " " + value)
    return "\n".join(lines) + "\n"


def ensure_payload(source, dest, expected=None):
    if dest.exists():
        need(dest.is_file(), "existing path not a file: " + str(dest))
        if expected:
            need(hash_file(dest) == expected,
                 "refusing to replace unexpected manager payload: " + str(dest))
        else:
            need(dest.read_bytes() == source,
                 "refusing to replace unexpected manager script: " + str(dest))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".ksu-manager.", dir=dest.parent)
    os.close(fd)
    temporary = Path(tmp)
    try:
        if expected:
            shutil.copyfile(source, temporary)
            need(hash_file(temporary) == expected, "staged manager payload mismatch")
        else:
            temporary.write_bytes(source)
        temporary.chmod(0o644)
        temporary.replace(dest)
    finally:
        temporary.unlink(missing_ok=True)


def write_metadata(file, data):
    fd, tmp = tempfile.mkstemp(prefix=".ksu-manager.", dir=file.parent)
    os.close(fd)
    temporary = Path(tmp)
    try:
        temporary.write_text(data)
        temporary.chmod(file.stat().st_mode & 0o777)
        temporary.replace(file)
    finally:
        temporary.unlink(missing_ok=True)


def verify(release=None):
    check_inputs()
    release = release or manager_release()
    need(hash_file(PAYLOAD) == release["sha256"],
         "manager payload SHA256 differs from matched KernelSU release")
    need(INSTALLER.read_bytes() == installer_bytes(release["build"]),
         "live manager installer drift")
    need(RC.read_bytes() == init_bytes(), "live init trigger drift")
    fs = FS_CONFIG.read_text().splitlines()
    ctx = FILE_CONTEXT.read_text().splitlines()
    for key, value in ENTRIES.items():
        need(fs.count(key + " " + value) == 1, "fs_config entry missing/drift: " + key)
    for key, value in CONTEXTS.items():
        need(ctx.count(key + " " + value) == 1,
             "file_context entry missing/drift: " + key)
    print("A16 KernelSU Next " + release["tag"] + " MANAGER WORKDIR VERIFY PASS")
    print("pm install -r once after boot / u:r:ksu:s0 / E3099 ACTIVE")
    print("A16 root/SELinux runtime and phone boot still UNVERIFIED")


def apply(existing=False):
    need(existing or os.environ.get("UN1CA_R0S_LATE_PATCH") == "1",
         "--apply is restricted to r0s's final ROM patch stage")
    check_inputs()
    if existing:
        need((WORK / ".completed").is_file(),
             "existing-workdir mode requires a completed ROM build")
        # Do not change inputs while a target-files build holds staging files.
        working = ROOT / "out/target/r0s/tmp"
        need(not working.exists() or
             (working.is_dir() and not any(working.iterdir())),
             "target-files/build temporary directory is active or nonempty")
        check = subprocess.run(
            [sys.executable, str(ROOT / "scripts/r0s/integrate_extremekrnl_a16.py"),
             "--verify"], env={**os.environ, "PATH": str(ROOT / "out/tools/bin")
                                 + os.pathsep + os.environ.get("PATH", "")})
        need(check.returncode == 0, "existing kernel integration not verified")
    release = manager_release()
    package = apk(release)
    ensure_payload(package, PAYLOAD, expected=release["sha256"])
    ensure_payload(installer_bytes(release["build"]), INSTALLER)
    ensure_payload(init_bytes(), RC)
    write_metadata(FS_CONFIG, prepare_text(FS_CONFIG.read_text(), ENTRIES))
    write_metadata(FILE_CONTEXT,
                   prepare_text(FILE_CONTEXT.read_text(), CONTEXTS))
    verify(release)
    if existing:
        print("EXISTING WORKDIR UPDATED — no ROM/kernel compilation, no .completed rewrite")
    else:
        print("LATE ROM KSU MANAGER PATCH APPLIED")


def self_test():
    read_manifest()
    installer_bytes()
    init_bytes()
    need(len(ENTRIES) == 5 and len(CONTEXTS) == 5,
         "manager layout/schema test failed")
    need("on property:sys.boot_completed=1" in init_bytes().decode(),
         "init trigger missing")
    print("KSU Next A16 manager delivery self-test PASS (no download or device)")


def main():
    mode = sys.argv[1:] or ["--check"]
    if mode == ["--self-test"]:
        self_test()
    elif mode == ["--check"]:
        check_inputs()
        print("Read-only; manager not necessarily installed into workdir")
    elif mode == ["--verify"]:
        verify()
    elif mode == ["--apply"]:
        apply(existing=False)
    elif mode == ["--apply-existing"]:
        apply(existing=True)
    else:
        raise Blocked("usage: install_ksunext_manager_a16.py "
                      "[--check|--verify|--apply|--apply-existing|--self-test]")


if __name__ == "__main__":
    try:
        main()
    except (Blocked, OSError, UnicodeError, ValueError, KeyError,
            subprocess.SubprocessError) as exc:
        print("A16 KSU MANAGER DELIVERY BLOCKED: " + str(exc), file=sys.stderr)
        sys.exit(2)
