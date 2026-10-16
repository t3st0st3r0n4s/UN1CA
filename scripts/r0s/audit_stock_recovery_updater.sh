#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only inventory of stock GZH3 recovery and the upstream UN1CA OTA updater.
# Neither ELF architecture nor strings establish recovery-side execution/trust.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="$ROOT/out/fw/SM-S901B_EUX"
NATIVE="$FW/kernel/recovery.img"
UPDATER="$ROOT/prebuilts/bootable/deprecated-ota/updater"
EXPECTED_RELEASE='S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3'
EXPECTED_SHA='b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688'
fail() { printf 'r0s STOCK RECOVERY UPDATER AUDIT BLOCKED: %s\n' "$*" >&2; exit 2; }

export PATH="$ROOT/out/tools/bin:$PATH"
for cmd in unpack_bootimg lz4 cpio readelf strings sha256sum awk grep file openssl; do
    command -v "$cmd" >/dev/null 2>&1 || fail "missing host inspection tool: $cmd"
done
[[ -s "$FW/.extracted" && "$(cat "$FW/.extracted")" == "$EXPECTED_RELEASE" ]] ||
    fail 'wrong/missing extracted GZH3 release'
[[ -s "$NATIVE" && -s "$UPDATER" ]] ||
    fail 'missing native stock recovery or UN1CA prebuilt OTA updater'
printf '%s  %s\n' "$EXPECTED_SHA" "$NATIVE" | sha256sum -c - >/dev/null ||
    fail 'stock recovery image differs from pinned GZH3 hash'

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/unpacked"

echo '===== STOCK GZH3 RECOVERY ELF INVENTORY ====='
unpack_bootimg --boot_img "$NATIVE" --out "$TMP/unpacked" > "$TMP/header.txt" 2>&1 ||
    fail 'cannot unpack pinned stock recovery image'
[[ -s "$TMP/unpacked/ramdisk" ]] || fail 'stock recovery ramdisk missing'
file -b "$TMP/unpacked/ramdisk" | grep -qi 'LZ4 compressed data' ||
    fail 'unexpected stock recovery ramdisk format'
lz4 -dc "$TMP/unpacked/ramdisk" | cpio -it --quiet > "$TMP/entries" ||
    fail 'could not inventory stock recovery ramdisk'
RECOVERY_ENTRY="$(grep -E '^(\./)?system/bin/recovery$' "$TMP/entries" | head -n 1 || true)"
[[ -n "$RECOVERY_ENTRY" ]] || fail 'no system/bin/recovery executable in pinned recovery ramdisk'
lz4 -dc "$TMP/unpacked/ramdisk" | cpio -i --quiet --to-stdout "$RECOVERY_ENTRY" > "$TMP/recovery" ||
    fail 'cannot stream stock recovery executable'
[[ -s "$TMP/recovery" ]] || fail 'empty stock recovery executable'

for side in stock_recovery unica_updater; do
    if [[ "$side" == stock_recovery ]]; then obj="$TMP/recovery"; else obj="$UPDATER"; fi
    echo "----- $side -----"
    printf 'sha256='; sha256sum "$obj" | awk '{print $1}'
    file -b "$obj"
    readelf -h "$obj" > "$TMP/$side.elf" || fail "$side is not a readable ELF binary"
    grep -E 'Class:|Data:|Type:|Machine:' "$TMP/$side.elf" || fail 'ELF header unavailable'
    readelf -l "$obj" 2>/dev/null | grep -F 'Requesting program interpreter:' || true
    readelf -d "$obj" 2>/dev/null | grep '(NEEDED)' || true
    grep -q 'AArch64' "$TMP/$side.elf" || fail "$side is not a native AArch64 ELF"
done

echo '===== STOCK RECOVERY PUBLIC TRUST-ANCHOR PATH INVENTORY ====='
grep -Ei '(^|/)(keys|otacerts\.zip|.*\.pem|.*\.x509\.der|.*\.crt)$' "$TMP/entries" | head -60 || true

TEST_CERT="$ROOT/security/aosp_testkey.x509.pem"
if [[ -f "$TEST_CERT" ]]; then
    echo '===== PROJECT DEVELOPMENT OTA CERT FINGERPRINT ====='
    openssl x509 -in "$TEST_CERT" -noout -fingerprint -sha256 ||
        fail 'project development OTA certificate unreadable'
else
    echo 'PROJECT OTA TEST CERT: not present'
fi

echo '===== STATIC STRING HINTS (NOT EXECUTION PROOF) ====='
for side in stock_recovery unica_updater; do
    if [[ "$side" == stock_recovery ]]; then obj="$TMP/recovery"; else obj="$UPDATER"; fi
    echo "----- $side -----"
    strings -a "$obj" | grep -Ei 'update-binary|otacerts|signature verification|sideload|update_dynamic_partitions|block_image_update' | LC_ALL=C sort -u | head -35 || true
done

echo 'STOCK RECOVERY / UN1CA UPDATER STATIC INVENTORY PASS'
echo 'AArch64 ELF presence is not proof of supported update-binary protocol or library linkage.'
echo 'STOCK RECOVERY OTA TRUST, EXECUTION, KERNEL ABI LOADABILITY, BOARD UNVERIFIED.'
echo 'BOARD DEFERRED; NO OTA BUILT AND NO FLASHING.'
