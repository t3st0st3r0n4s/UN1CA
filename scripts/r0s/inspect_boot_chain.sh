#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only inspector for UN1CA-extracted S901B A16 boot artifacts.
# Does NOT rebuild images, patch kernel, infer ABI compatibility or flash.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FWDIR="${1:-$ROOT/out/fw/SM-S901B_EUX}"
fail() { printf 'BOOT CHAIN BLOCKED: %s\n' "$*" >&2; exit 2; }
read_field() { sed -n "s/^$1=//p" "$2" | tail -n 1; }
[[ -f "$ROOT/platform/exynos2200/config.sh" ]] || fail 'missing Exynos 2200 platform config'
# Shellcheck SC1091: this is strictly local declarative project configuration.
source "$ROOT/platform/exynos2200/config.sh"
[[ -d "$FWDIR/kernel" ]] || fail 'kernel image extraction is missing'
for part in boot vendor_boot dtbo; do
    image="$FWDIR/kernel/$part.img"
    [[ -f "$image" ]] || fail "missing native $part.img"
    size="$(stat -c '%s' "$image")"
    case "$part" in
        boot) cap="$TARGET_BOOT_PARTITION_SIZE" ;;
        vendor_boot) cap="$TARGET_VENDOR_BOOT_PARTITION_SIZE" ;;
        dtbo) cap="$TARGET_DTBO_PARTITION_SIZE" ;;
    esac
    [[ "$size" =~ ^[0-9]+$ && "$cap" =~ ^[0-9]+$ ]] || fail "invalid $part size"
    (( size > 0 && size <= cap )) || fail "$part.img size $size outside provisional partition cap $cap"
    printf 'image=%s bytes=%s provisional_limit=%s\n' "$part.img" "$size" "$cap"
    sha256sum "$image"
    if [[ "$part" == boot || "$part" == vendor_boot ]]; then
        metadata="$FWDIR/${part}.img_metadata.txt"
        [[ -f "$metadata" ]] || fail "missing upstream ${part}.img_metadata.txt"
        hdr="$(read_field header_version "$metadata")"
        [[ "$hdr" == 4 ]] || fail "$part header version is '${hdr:-missing}', expected v4 candidate"
        # The mkbootimg os_version is image HEADER metadata, not the
        # ro.build.version.sdk of the extracted Android system. Real Samsung
        # S901B GZH3/A16 boot.img reports os_version=12.0.0 (SDK is 36).
        # Validate formatting without falsely requiring header OS = 16.
        os="$(read_field os_version "$metadata")"
        [[ -z "$os" || "$os" =~ ^[0-9]+(\.[0-9]+){0,2}$ ]] ||
            fail "$part malformed boot-header os_version: $os"
        printf 'metadata=%s header_version=%s os_version_header=%s\n' "$(basename "$metadata")" "$hdr" "${os:-not-recorded}"
        if [[ -n "$os" && "$os" != 16 && "$os" != 16.* ]]; then
            printf 'BOOT HEADER NOTE: %s records os_version=%s; this is not the Android system SDK\n' "$part" "$os"
        fi
    fi
done
if [[ -f "$FWDIR/vendor/etc/fstab.s5e9925" ]]; then
    printf 'vendor_fstab=%s\n' "$FWDIR/vendor/etc/fstab.s5e9925"
    sha256sum "$FWDIR/vendor/etc/fstab.s5e9925"
else
    printf 'vendor_fstab=NOT_EXTRACTED (recovery qualification blocked)\n'
fi
if [[ -d "$FWDIR/vendor_dlkm/lib/modules" ]]; then
    printf 'vendor_dlkm_modules:\n'
    find "$FWDIR/vendor_dlkm/lib/modules" -type f -name '*.ko' -printf '%P\n' | LC_ALL=C sort
else
    printf 'vendor_dlkm_modules=NOT_EXTRACTED\n'
fi
printf 'BOOT IMAGE METADATA PRECHECK PASS; kernel ABI, runtime, recovery and BOARD remain UNVERIFIED\n'
