#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only GZH3 stock/workdir vs existing S901B TWRP candidate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="$ROOT/out/fw/SM-S901B_EUX"
WORK="$ROOT/out/target/r0s/work_dir"
STOCK="$FW/kernel/recovery.img"
STAGED="$WORK/kernel/recovery.img"
TWRP_TAR="$HOME/android/S22-ROM/S901B_twrp_logo_vbmeta.tar"
if [[ $# -gt 1 ]]; then
    echo "Usage: bash scripts/r0s/audit_recovery_candidates.sh [S901B_twrp_logo_vbmeta.tar]" >&2
    exit 2
fi
if [[ $# == 1 ]]; then TWRP_TAR="$1"; fi
fail() { printf 'r0s RECOVERY CANDIDATE BLOCKED: %s\n' "$*" >&2; exit 2; }
export PATH="$ROOT/out/tools/bin:$PATH"
for cmd in tar unpack_bootimg sha256sum cmp cpio lz4 gzip file awk grep stat; do
    command -v "$cmd" >/dev/null || fail "missing host utility: $cmd"
done
[[ -s "$FW/.extracted" && "$(cat "$FW/.extracted")" == \
    "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3" ]] || fail 'wrong GZH3 source'
[[ -s "$WORK/.completed" && -s "$STOCK" && -s "$STAGED" && -s "$TWRP_TAR" ]] ||
    fail 'missing stock/workdir recovery or TWRP archive'
echo "b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688  $STOCK" |
    sha256sum -c - >/dev/null || fail 'stock GZH3 recovery image hash mismatch'
grep -Eq '^[[:space:]]*abort\("E3099:.*NOT qualified for flashing' \
    "$ROOT/target/r0s/installer/assertions.edify" || fail 'E3099 installer lock missing'

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
echo '===== TWRP TAR MEMBER INVENTORY (NO RESTORE) ====='
sha256sum "$TWRP_TAR"
tar -tf "$TWRP_TAR" > "$TMP/members" || fail 'cannot list candidate TAR'
head -45 "$TMP/members"
awk '$0=="recovery.img" || $0=="./recovery.img" || $0 ~ /\/recovery\.img$/ {print}' \
    "$TMP/members" > "$TMP/candidates"
[[ "$(wc -l < "$TMP/candidates")" -eq 1 ]] ||
    fail 'TWRP TAR must contain exactly one recovery.img'
MEMBER="$(head -n 1 "$TMP/candidates")"
[[ "$MEMBER" != /* && "$MEMBER" != ../* && "$MEMBER" != *'/../'* ]] ||
    fail 'unsafe TAR candidate member name'
# -xO streams exactly one member to stdout. Never restore TAR paths onto disk.
tar -xOf "$TWRP_TAR" -- "$MEMBER" > "$TMP/twrp.img" ||
    fail 'could not read TAR recovery.img'
[[ -s "$TMP/twrp.img" ]] || fail 'TWRP recovery member empty'
(( $(stat -c '%s' "$TMP/twrp.img") <= 100663296 )) ||
    fail 'TWRP recovery exceeds stock reference size'
if [[ -s "$HOME/Downloads/S901B_twrp_logo_vbmeta.tar" ]]; then
    if cmp -s "$TWRP_TAR" "$HOME/Downloads/S901B_twrp_logo_vbmeta.tar"; then
        echo 'TWRP_ARCHIVE_DUPLICATE=BYTE_IDENTICAL'
    else
        echo 'TWRP_ARCHIVE_DUPLICATE=DIFFERENT_BYTES'
    fi
fi

echo '===== IMAGE HEADER / KERNEL / RAMDISK INVENTORY ====='
for side in stock work twrp; do
    mkdir "$TMP/$side"
    case "$side" in
        stock) image="$STOCK";;
        work) image="$STAGED";;
        twrp) image="$TMP/twrp.img";;
    esac
    printf '%s_recovery_bytes=%s\n' "$side" "$(stat -c %s "$image")"
    printf '%s_recovery_sha256=' "$side"
    sha256sum "$image" | awk '{print $1}'
    unpack_bootimg --boot_img "$image" --out "$TMP/$side" > "$TMP/$side.header" 2>&1 ||
        fail "unpack_bootimg could not inspect $side recovery image"
    grep -Ei '^(boot image header version|os version|os patch level|command line args):' \
        "$TMP/$side.header" || true
    [[ -s "$TMP/$side/kernel" && -s "$TMP/$side/ramdisk" ]] ||
        fail "$side recovery lacks kernel or ramdisk"
    printf '%s_kernel_sha256=' "$side"
    sha256sum "$TMP/$side/kernel" | awk '{print $1}'
    printf '%s_ramdisk_sha256=' "$side"
    sha256sum "$TMP/$side/ramdisk" | awk '{print $1}'
    printf '%s_ramdisk_type=%s\n' "$side" "$(file -b "$TMP/$side/ramdisk")"
done

echo '===== GZH3 WORKDIR RECOVERY MUST RETAIN STOCK PAYLOAD ====='
cmp -s "$TMP/stock/kernel" "$TMP/work/kernel" ||
    fail 'workdir recovery kernel differs from GZH3 stock'
cmp -s "$TMP/stock/ramdisk" "$TMP/work/ramdisk" ||
    fail 'workdir recovery ramdisk differs from GZH3 stock'
echo 'STOCK_WORKDIR_RECOVERY_KERNEL_AND_RAMDISK_IDENTICAL=true'
echo '===== TWRP EMBEDDED KERNEL EQUIVALENCE ====='
if cmp -s "$TMP/stock/kernel" "$TMP/twrp/kernel"; then
    echo 'TWRP_KERNEL_EQUALS_GZH3_STOCK=true'
else
    echo 'TWRP_KERNEL_EQUALS_GZH3_STOCK=false'
    echo 'TWRP candidate is NOT native-kernel-qualified for GZH3.'
fi

ramdisk_stream() {
    local side="$1" description
    description="$(file -b "$TMP/$side/ramdisk")"
    case "$description" in
        *LZ4*) lz4 -dc "$TMP/$side/ramdisk";;
        *gzip*) gzip -dc "$TMP/$side/ramdisk";;
        *cpio*) cat "$TMP/$side/ramdisk";;
        *) return 2;;
    esac
}
echo '===== RECOVERY FSTAB / TWRP FILE INVENTORY ====='
for side in stock work twrp; do
    echo "--- $side ---"
    if ramdisk_stream "$side" | cpio -it --quiet > "$TMP/$side.list" 2>/dev/null; then
        grep -Ei '(^|/)(fstab[^/]*|recovery|twrp[^/]*)$' "$TMP/$side.list" | head -70 || true
        grep -Ei '(^|/)(recovery\.fstab|twrp\.fstab|fstab\.[^/]*)$' \
            "$TMP/$side.list" | head -8 > "$TMP/$side.fstabs" || true
        while IFS= read -r entry; do
            [[ -n "$entry" ]] || continue
            printf 'fstab_entry=%s\n' "$entry"
            if ramdisk_stream "$side" | cpio -i --quiet --to-stdout "$entry" \
                > "$TMP/$side.fstab" 2>/dev/null; then
                [[ -s "$TMP/$side.fstab" ]] || continue
                sha256sum "$TMP/$side.fstab"
                grep -E '(system_ext|vendor_dlkm|/system|/vendor|/boot|/recovery|/product|/odm)' \
                    "$TMP/$side.fstab" | head -35 || true
            fi
        done < "$TMP/$side.fstabs"
    else
        echo 'ramdisk_inventory=UNSUPPORTED_FORMAT_OR_BAD_CPIO'
    fi
done
echo 'RECOVERY STATIC HOST INVENTORY COMPLETE (NOT DEVICE COMPATIBILITY PASS)'
echo 'Prior TWRP kernel match is only one gate; updater, fstab, bootloader still unverified.'
echo 'NO RECOVERY/OTA FLASH. E3099 ACTIVE.'
