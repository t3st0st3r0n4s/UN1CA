#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only comparison of GZH3 recovery OTA certs and UN1CA dev signer."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import zipfile

PEM = re.compile(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)
MAX_FILE = 2 * 1024 * 1024
MAX_ZIP = 12 * 1024 * 1024


class Blocked(Exception):
    pass


def require(ok, message):
    if not ok:
        raise Blocked(message)


def openssl(args, data):
    p = subprocess.run(["openssl", *args], input=data, capture_output=True)
    if p.returncode:
        raise Blocked("unable to parse X.509 certificate/public key")
    return p.stdout


def certs(data):
    require(len(data) <= MAX_FILE, "certificate exceeds size bound")
    blocks = PEM.findall(data)
    candidates = [(block, "PEM") for block in blocks] if blocks else [(data, "DER")]
    out = []
    for raw, fmt in candidates:
        try:
            der = openssl(["x509", "-inform", fmt, "-outform", "DER"], raw)
            pk = openssl(["x509", "-inform", "DER", "-pubkey", "-noout"], der)
            spki = openssl(["pkey", "-pubin", "-inform", "PEM", "-outform", "DER"], pk)
        except Blocked:
            if blocks:
                raise
            return []  # Non-X.509 publiccert may be a separate, unknown format.
        out.append((hashlib.sha256(der).hexdigest(), hashlib.sha256(spki).hexdigest()))
    return out


def ota_archive(path):
    require(path.stat().st_size <= MAX_ZIP, "stock otacerts ZIP too large")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        require(len(infos) <= 128, "too many stock cert ZIP members")
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)), "duplicate stock certificate member")
        require(all(not n.startswith("/") and ".." not in n.split("/")
                    and "\\" not in n for n in names), "unsafe certificate ZIP member")
        require(sum(i.file_size for i in infos) <= MAX_ZIP, "expanded ZIP too large")
        parsed, unknown = [], []
        for i in infos:
            if i.is_dir():
                continue
            require(i.file_size <= MAX_FILE and not (i.flag_bits & 1),
                    "oversized or encrypted stock certificate member")
            rows = certs(z.read(i))
            if rows:
                parsed.extend((i.filename, *r) for r in rows)
            else:
                unknown.append(i.filename)
    require(parsed, "no parseable X.509 cert in stock recovery otacerts ZIP")
    return parsed, unknown


def inspect(publiccert, ota_zip, signer):
    reference = certs(signer.read_bytes())
    require(len(reference) == 1, "dev signer must contain one valid X.509 certificate")
    exact, key = reference[0]
    pub = certs(publiccert.read_bytes())
    ota, unknown = ota_archive(ota_zip)
    return {
        "dev_cert_sha256": exact,
        "dev_public_key_sha256": key,
        "stock_ota_certs": ota,
        "stock_public_certs": pub,
        "unknown_stock_ota_members": unknown,
        "stock_ota_exact_cert_match": any(der == exact for _, der, _ in ota),
        "stock_ota_public_key_match": any(spki == key for _, _, spki in ota),
        "stock_publiccert_exact_match": any(der == exact for der, _ in pub),
        "stock_publiccert_public_key_match": any(spki == key for _, spki in pub),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("publiccert", type=Path)
    p.add_argument("otacerts_zip", type=Path)
    p.add_argument("unica_signer", type=Path)
    a = p.parse_args()
    try:
        r = inspect(a.publiccert, a.otacerts_zip, a.unica_signer)
    except (Blocked, OSError, zipfile.BadZipFile) as exc:
        print("r0s RECOVERY CERT AUDIT BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    for field in ("dev_cert_sha256", "dev_public_key_sha256",
                  "stock_ota_exact_cert_match", "stock_ota_public_key_match",
                  "stock_publiccert_exact_match", "stock_publiccert_public_key_match"):
        value = r[field]
        print(f"{field}={str(value).lower() if isinstance(value, bool) else value}")
    for path, der, spki in r["stock_ota_certs"]:
        print(f"stock_otacert={path} der_sha256={der} public_key_sha256={spki}")
    for der, spki in r["stock_public_certs"]:
        print(f"stock_publiccert_der_sha256={der} public_key_sha256={spki}")
    for path in r["unknown_stock_ota_members"]:
        print(f"unparsed_stock_ota_member={path}")
    if not r["stock_ota_public_key_match"]:
        print("DEVELOPMENT SIGNER KEY NOT FOUND IN PARSED STOCK otacerts.zip")
        print("Likely testkey-signed OTA blocker; other trust routes still unverified.")
    else:
        print("DEVELOPMENT SIGNER KEY PRESENT in parsed otacerts.zip; no execution proof.")
    print("GZH3 RECOVERY CERTIFICATE COMPARISON COMPLETE (READ-ONLY)")
    print("E3099 ACTIVE. NOT OTA/BOARD QUALIFIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
