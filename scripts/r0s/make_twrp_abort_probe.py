#!/usr/bin/env python3
"""Create an ABORT-ONLY probe from the existing UN1CA update-binary. No flashing."""
import argparse
import hashlib
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "out/UN1CA_r0s_A16_GZH3_E3099_BLOCKED_full_ota.zip"
OUT = ROOT / "out/r0s_TWRP_E3099_ABORT_ONLY_probe.zip"
ROM_SHA = "4200d8239a5243021cdcf7396b0bab4f0dda944f5dc4e1893ffd189c4df9e022"
BINARY_SHA = "28378c9dcae8a0e6035e5f90e66c2a128eab3cce2982e43aa33424542507664a"
BIN = "META-INF/com/google/android/update-binary"
SCRIPT = "META-INF/com/google/android/updater-script"
ABORT = b'abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");\n'

def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def check(path, binary):
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist()) == 2 and set(z.namelist()) == {BIN, SCRIPT}
        assert z.read(SCRIPT) == ABORT
        assert z.read(BIN) == binary
        assert z.testzip() is None

def make(path, binary):
    if path.exists():
        raise ValueError("probe already exists; will not overwrite")
    try:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr(BIN, binary)
            z.writestr(SCRIPT, ABORT)
        check(path, binary)
    except BaseException:
        path.unlink(missing_ok=True)
        raise

def tests():
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "probe.zip"
        make(target, b"test updater")
        check(target, b"test updater")
        with zipfile.ZipFile(target, "a") as z:
            z.writestr("boot.img", b"dangerous")
        try:
            check(target, b"test updater")
        except AssertionError:
            pass
        else:
            raise AssertionError("unsafe extra archive member accepted")
    print("r0s abort-only updater synthetic gate PASS")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            tests()
            return 0
        if not ROM.is_file() or hash_file(ROM) != ROM_SHA:
            raise ValueError("canonical locked UN1CA full OTA not found or hash mismatch")
        lock = ROOT / "target/r0s/installer/assertions.edify"
        if not lock.is_file() or ABORT not in lock.read_bytes():
            raise ValueError("canonical E3099 source lock missing")
        with zipfile.ZipFile(ROM) as z:
            if BIN not in z.namelist() or not 0 < z.getinfo(BIN).file_size <= 33554432:
                raise ValueError("actual ROM updater missing or oversized")
            binary = z.read(BIN)
        if hashlib.sha256(binary).hexdigest() != BINARY_SHA:
            raise ValueError("actual updater hash does not match prior host pass")
        make(OUT, binary)
        print("PROBE_PATH=" + str(OUT))
        print("PROBE_SHA256=" + hash_file(OUT))
        print("PROBE_SIZE=" + str(OUT.stat().st_size))
        print("ONLY UPDATE-BINARY AND IMMEDIATE E3099 ABORT; NO PARTITION PAYLOADS")
        print("NO PHONE CHANGES; ORIGINAL UN1CA FULL ZIP UNCHANGED")
        return 0
    except (OSError, ValueError, AssertionError, zipfile.BadZipFile) as ex:
        print("E3099 PROBE BLOCKED: " + str(ex), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
