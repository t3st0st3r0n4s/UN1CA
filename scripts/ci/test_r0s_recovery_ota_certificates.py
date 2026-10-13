#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic positive and negative OTA trust inventory fixtures."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "trust", ROOT / "scripts/r0s/check_recovery_ota_certificates.py")
trust = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trust)


def run():
    signer = ROOT / "security/aosp_testkey.x509.pem"
    other = ROOT / "security/aosp_platform.x509.pem"
    assert trust.certs(signer.read_bytes())[0] != trust.certs(other.read_bytes())[0]
    cases = 0
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        pub, zpath = tmp / "publiccert.pem", tmp / "otacerts.zip"

        def put(cert, name="test.x509.pem"):
            with zipfile.ZipFile(zpath, "w") as z:
                z.writestr(name, cert.read_bytes())

        def blocked():
            nonlocal cases
            try:
                trust.inspect(pub, zpath, signer)
            except trust.Blocked:
                cases += 1
                return
            raise AssertionError("unsafe stock trust fixture accepted")

        pub.write_bytes(signer.read_bytes())
        put(signer)
        r = trust.inspect(pub, zpath, signer)
        assert r["stock_ota_exact_cert_match"] and r["stock_ota_public_key_match"]
        assert r["stock_publiccert_public_key_match"]
        cases += 1

        pub.write_bytes(other.read_bytes())
        r = trust.inspect(pub, zpath, signer)
        assert r["stock_ota_public_key_match"] and not r["stock_publiccert_public_key_match"]
        cases += 1

        put(other)
        r = trust.inspect(pub, zpath, signer)
        assert not r["stock_ota_exact_cert_match"] and not r["stock_ota_public_key_match"]
        cases += 1

        pub.write_bytes(b"not X509")
        r = trust.inspect(pub, zpath, signer)
        assert not r["stock_public_certs"]
        cases += 1

        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("../unsafe.pem", signer.read_bytes())
        blocked()
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("notes.txt", b"no cert")
        blocked()
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("valid.pem", signer.read_bytes())
            z.writestr("valid.pem", other.read_bytes())
        blocked()

        der = subprocess.check_output(["openssl", "x509", "-in", str(signer), "-outform", "DER"])
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("ota.der", der)
        r = trust.inspect(pub, zpath, signer)
        assert r["stock_ota_public_key_match"]
        cases += 1
    assert cases == 8, cases
    print(f"r0s recovery OTA trust synthetic tests PASS ({cases} cases)")


if __name__ == "__main__":
    run()
