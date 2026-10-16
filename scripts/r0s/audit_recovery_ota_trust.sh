#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read only: verify GZH3 recovery image and compare stock OTA trust anchors.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="$ROOT/out/fw/SM-S901B_EUX"
IMAGE="$FW/kernel/recovery.img"
TEST_CERT="$ROOT/security/aosp_testkey.x509.pem"
die() { printf 'r0s RECOVERY TRUST BLOCKED: %s\n' "$*" >&2; exit 2; }
export PATH="$ROOT/out/tools/bin:$PATH"
for cmd in sha256sum unpack_bootimg lz4 cpio file python3 openssl; do
    command -v "$cmd" >/dev/null || die "missing tool $cmd"
done
[[ -s "$FW/.extracted" && "$(cat "$FW/.extracted")" == \
    "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3" ]] || die "not pinned GZH3"
[[ -s "$IMAGE" && -s "$TEST_CERT" ]] || die "stock recovery/test certificate missing"
echo "b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688  $IMAGE" |
    sha256sum -c - >/dev/null || die "recovery hash mismatch"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/boot"
unpack_bootimg --boot_img "$IMAGE" --out "$TMP/boot" > "$TMP/boot.txt" 2>&1 ||
    die "stock recovery unpack failed"
[[ -s "$TMP/boot/ramdisk" ]] || die "recovery ramdisk missing"
file -b "$TMP/boot/ramdisk" | grep -qi 'LZ4 compressed data' ||
    die "unexpected stock recovery compression"
lz4 -dc "$TMP/boot/ramdisk" | cpio -it --quiet > "$TMP/entries" ||
    die "recovery ramdisk inventory failed"
PUBLIC="$(grep -E '^(\./)?publiccert\.pem$' "$TMP/entries" | head -1 || true)"
OTA="$(grep -E '^(\./)?system/etc/security/otacerts\.zip$' "$TMP/entries" | head -1 || true)"
[[ -n "$PUBLIC" && -n "$OTA" ]] || die "stock recovery OTA anchor files absent"
for entry in "$PUBLIC" "$OTA"; do
    output="$TMP/$(basename "$entry")"
    lz4 -dc "$TMP/boot/ramdisk" | cpio -i --quiet --to-stdout "$entry" > "$output" ||
        die "failed to read recovery entry $entry"
    [[ -s "$output" ]] || die "empty recovery entry $entry"
    sha256sum "$output"
done
echo '===== STOCK GZH3 RECOVERY VS UN1CA OTA SIGNER ====='
python3 "$ROOT/scripts/r0s/check_recovery_ota_certificates.py" \
    "$TMP/publiccert.pem" "$TMP/otacerts.zip" "$TEST_CERT" ||
    die "certificate comparison failed"
echo 'STATIC TRUST-ANCHOR INVENTORY COMPLETE; signature acceptance NOT verified.'
echo 'BOARD DEFERRED. NO OTA CREATED, NO FLASHING.'
