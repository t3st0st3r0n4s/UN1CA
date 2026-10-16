#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only native GZH3 stock recovery and module inventory; no image changes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="$ROOT/out/fw/SM-S901B_EUX"
if [[ -n "$*" ]]; then FW="$1"; fi
EXPECTED_RELEASE="S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3"
RECOVERY_SHA="b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688"
MODULE_RELEASE="5.10.237-android12-9-31999025-abS901BXXSOGZH3"
fail() { printf 'r0s RECOVERY/ABI BLOCKED: %s\n' "$*" >&2; exit 2; }
export PATH="$ROOT/out/tools/bin:$PATH"

[[ -f "$FW/.extracted" ]] || fail 'no extracted Samsung firmware release marker'
[[ "$(cat "$FW/.extracted")" == "$EXPECTED_RELEASE" ]] || fail 'unexpected Samsung release'
[[ -f "$FW/kernel/recovery.img" ]] || fail 'native recovery.img missing'
for cmd in unpack_bootimg file lz4 cpio sha256sum modinfo awk; do
    command -v "$cmd" >/dev/null 2>&1 || fail "missing host command: $cmd"
done
printf '%s  %s\n' "$RECOVERY_SHA" "$FW/kernel/recovery.img" |
    sha256sum -c - || fail 'native recovery image hash mismatch'

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/unpacked"

printf '===== NATIVE STOCK GZH3 RECOVERY HEADER =====\n'
if ! unpack_bootimg --boot_img "$FW/kernel/recovery.img" --out "$TMP/unpacked" >"$TMP/boot_header.txt" 2>&1; then
    cat "$TMP/boot_header.txt" >&2
    fail 'recovery boot image parsing failed'
fi
cat "$TMP/boot_header.txt"

RAMDISK="$TMP/unpacked/ramdisk"
[[ -s "$RAMDISK" ]] || fail 'recovery ramdisk missing'
printf 'ramdisk_type=%s\n' "$(file -b "$RAMDISK")"
file -b "$RAMDISK" | grep -qi 'LZ4 compressed data' ||
    fail 'unknown ramdisk compression; no fallback guess'
ramdisk_stream() { lz4 -dc "$RAMDISK"; }

printf '\n===== RECOVERY CONTENTS INVENTORY =====\n'
ramdisk_stream | cpio -it --quiet > "$TMP/entries"
grep -Ei '(^|/)(fstab|init\.recovery|recovery|updater)' "$TMP/entries" | head -100 || true

ENTRY="$(grep -E '^(\./)?system/etc/recovery\.fstab$' "$TMP/entries" | head -1 || true)"
[[ -n "$ENTRY" ]] || fail 'native system/etc/recovery.fstab missing'

printf '\n===== NATIVE RECOVERY FSTAB CONTENT =====\n'
ramdisk_stream | cpio -i --quiet --to-stdout "$ENTRY" > "$TMP/recovery.fstab"
[[ -s "$TMP/recovery.fstab" ]] || fail 'native recovery fstab is empty'
sha256sum "$TMP/recovery.fstab"
printf 'recovery_fstab_entry=%s\n' "$ENTRY"
cat "$TMP/recovery.fstab"

printf '\n===== CROSSCHECK STOCK RECOVERY AGAINST VENDOR AND GZH3 SUPER =====\n'
bash "$ROOT/scripts/r0s/check_recovery_ota_map.sh" \
    "$TMP/recovery.fstab" \
    "$FW/vendor/etc/fstab.s5e9925" \
    "$FW/os_partitions_metadata.txt"

printf '\n===== RECOVERY INIT ENTRIES =====\n'
for wanted in init.recovery.s5e9925.rc init.recovery.samsung.rc; do
    ENTRY="$(grep -E "(^|/)$wanted$" "$TMP/entries" | head -1 || true)"
    if [[ -z "$ENTRY" ]]; then
        printf '%s: not present\n' "$wanted"
        continue
    fi
    ramdisk_stream | cpio -i --quiet --to-stdout "$ENTRY" > "$TMP/$wanted"
    sha256sum "$TMP/$wanted"
    grep -Ein '(^on |^service |fstab|mount|selinux|recovery|post-fs)' "$TMP/$wanted" | head -75 || true
done

printf '\n===== STOCK GZH3 MODULE VERMAGIC =====\n'
MODULE_DIR="$FW/vendor_dlkm/lib/modules"
[[ -d "$MODULE_DIR" ]] || fail 'no stock vendor_dlkm modules'
for name in fingerprint.ko fingerprint_sysfs.ko input_booster_lkm.ko sec_debug_coredump.ko wlan.ko; do
    KO="$MODULE_DIR/$name"
    [[ -f "$KO" ]] || fail "stock module missing: $name"
    vermagic="$(modinfo -F vermagic "$KO")" || fail "cannot read vermagic: $name"
    depends="$(modinfo -F depends "$KO")" || fail "cannot read depends: $name"
    actual="$(printf '%s\n' "$vermagic" | awk '{print $1}')"
    printf 'module=%s\nvermagic=%s\ndepends=%s\n' "$name" "$vermagic" "$depends"
    sha256sum "$KO"
    [[ "$actual" == "$MODULE_RELEASE" ]] ||
        fail "$name does not match the native stock module kernel release"
done

printf '\nRECOVERY FSTAB HOST INVENTORY COMPLETE (OTA still unqualified)\n'
printf 'STOCK MODULE VERMAGIC COHERENCE PASS (not rebuilt kernel ABI proof)\n'
printf 'ROM/SELINUX-NORMAL-BOOT/BOARD remain unverified; BOARD remains unverified\n'