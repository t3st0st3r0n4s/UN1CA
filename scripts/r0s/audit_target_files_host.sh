#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only verification of a completed GZH3/r0s HOST-ONLY target-files ZIP.
# No ROM build, OTA build, image rewriting, privileged mount or flashing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
die() { printf 'r0s TARGET-FILES DEEP AUDIT BLOCKED: %s\n' "$*" >&2; exit 2; }

if [[ $# != 2 || ! "$2" =~ ^[a-f0-9]{64}$ ]]; then
    echo "Usage: bash scripts/r0s/audit_target_files_host.sh <zip> <expected-sha256>" >&2
    exit 2
fi
ZIP="$1"
[[ "$ZIP" == /* ]] || ZIP="$PWD/$ZIP"
EXPECTED="$2"
[[ -f "$ZIP" && -s "$ZIP" ]] || die "missing or empty ZIP: $ZIP"

export PATH="$ROOT/out/tools/bin:$PATH"
for cmd in python3 sha256sum unzip avbtool lpdump awk mktemp; do
    command -v "$cmd" >/dev/null || die "missing command: $cmd"
done
KEY="$ROOT/security/avb/testkey_rsa4096.pem"
[[ -f "$KEY" ]] || die "expected UN1CA development AVB test key missing"

echo '===== PINNED HOST-ONLY ARCHIVE IDENTITY ====='
ACTUAL="$(sha256sum "$ZIP" | awk '{print $1}')"
[[ "$ACTUAL" == "$EXPECTED" ]] || die "archive SHA-256 differs from pinned host build"
printf 'archive_sha256=%s\n' "$ACTUAL"

echo '===== NATIVE GZH3 STRUCTURE ====='
python3 "$ROOT/scripts/r0s/check_target_files_zip.py" "$ZIP" || die "target-files structural gate failed"

echo '===== FULL ZIP CRC (STREAMING, NO DISK EXTRACTION) ====='
unzip -tq "$ZIP" >/dev/null || die "ZIP member CRC failure"
echo 'ZIP CRC PASS'

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
echo '===== RAW BOOT-CHAIN AVB METADATA AND SIGNATURES ====='
for part in boot vendor_boot dtbo; do
    unzip -p "$ZIP" "$part.img" > "$TMP/$part.img" ||
        die "could not extract $part.img to temporary audit directory"
    [[ -s "$TMP/$part.img" ]] || die "$part.img empty"
    avbtool info_image --image "$TMP/$part.img" > "$TMP/$part.info" ||
        die "$part.img lacks parseable AVB footer"
    avbtool verify_image --image "$TMP/$part.img" --key "$KEY" > "$TMP/$part.verify" 2>&1 || {
        cat "$TMP/$part.verify" >&2
        die "$part.img AVB verification against UN1CA test key failed"
    }
    printf '%s AVB_TEST_KEY_VERIFY_PASS sha256=' "$part.img"
    sha256sum "$TMP/$part.img" | awk '{print $1}'
    grep -E '^(Footer version|Algorithm|Partition Name|Rollback Index):' "$TMP/$part.info" || true
done

echo '===== LP METADATA IN EMPTY SUPER ====='
unzip -p "$ZIP" unsparse_super_empty.img > "$TMP/unsparse_super_empty.img" ||
    die "could not extract empty-super metadata"
lpdump "$TMP/unsparse_super_empty.img" > "$TMP/lpdump.txt" ||
    die "lpdump cannot parse empty-super metadata"
grep -Fq 'group_basic' "$TMP/lpdump.txt" || die "missing native group_basic in LP metadata"
for part in system odm product vendor vendor_dlkm; do
    grep -Eq "(^|[^[:alnum:]_])${part}([^[:alnum:]_]|$)" "$TMP/lpdump.txt" ||
        die "missing expected LP entry: $part"
done
if grep -Eq '(^|[^[:alnum:]_])system_ext([^[:alnum:]_]|$)' "$TMP/lpdump.txt"; then
    die 'unexpected standalone system_ext logical partition'
fi
cat "$TMP/lpdump.txt"

echo 'HOST-ONLY TARGET-FILES DEEP AUDIT PASS'
echo 'AVB verified with project DEVELOPMENT TEST KEY ONLY; not stock trust/rollback qualification.'
echo 'RECOVERY OTA, MODULE ABI, NORMAL-BOOT SELINUX AND BOARD remain UNVERIFIED; BOARD DEFERRED.'
