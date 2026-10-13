#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only packaged kernel/module provenance; NOT an ABI or board qualification.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
die() { printf 'r0s MODULE PROVENANCE BLOCKED: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && "$2" =~ ^[0-9a-f]{64}$ ]] || {
    echo "Usage: bash scripts/r0s/audit_packaged_kernel_modules.sh <zip> <sha256>" >&2
    exit 2
}
ZIP="$1"
[[ "$ZIP" == /* ]] || ZIP="$PWD/$ZIP"
FW="$ROOT/out/fw/SM-S901B_EUX"
WORK="$ROOT/out/target/r0s/work_dir"
export PATH="$ROOT/out/tools/bin:$PATH"
for cmd in sha256sum unzip unpack_bootimg simg2img fsck.erofs modinfo cmp find python3 awk; do
    command -v "$cmd" >/dev/null || die "required host tool missing: $cmd"
done
[[ -s "$ZIP" && -s "$FW/.extracted" && -s "$WORK/.completed" ]] ||
    die 'missing ZIP, stock extraction or completed workdir'
[[ "$(cat "$FW/.extracted")" == "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3" ]] ||
    die 'wrong stock firmware'
[[ "$(sha256sum "$ZIP" | awk '{print $1}')" == "$2" ]] ||
    die 'packaged target-files SHA-256 mismatch'
grep -Eq '^[[:space:]]*abort\("E3099:.*NOT qualified for flashing' \
    "$ROOT/target/r0s/installer/assertions.edify" || die 'installer E3099 missing'

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
echo '===== VERIFY STOCK -> PACKAGED KERNEL PATCH SCOPE ====='
for side in stock work packaged; do
    mkdir -p "$TMP/$side"
    case "$side" in
        stock) img="$FW/kernel/boot.img";;
        work) img="$WORK/kernel/boot.img";;
        packaged)
            unzip -p "$ZIP" boot.img > "$TMP/package_boot.img" ||
                die 'unable to read packaged boot.img'
            img="$TMP/package_boot.img";;
    esac
    [[ -s "$img" ]] || die "missing $side boot.img"
    unpack_bootimg --boot_img "$img" --out "$TMP/$side" > "$TMP/$side.log" 2>&1 ||
        die "cannot unpack $side boot.img"
    bash "$ROOT/scripts/r0s/check_unpacked_boot_header.sh" boot \
        "$TMP/$side.log" >/dev/null || die "incorrect $side boot header"
    [[ -s "$TMP/$side/kernel" ]] || die "missing $side kernel"
    printf '%s_kernel_sha256=' "$side"
    sha256sum "$TMP/$side/kernel" | awk '{print $1}'
done
cmp -s "$TMP/work/kernel" "$TMP/packaged/kernel" ||
    die 'packaged embedded kernel differs from workdir'
if [[ -f "$WORK/kernel/.r0s_extremekrnl_a16_integrated" ]]; then
    python3 "$ROOT/scripts/r0s/integrate_extremekrnl_a16.py" --verify ||
        die 'custom workdir provenance failed'
    echo 'PACKAGED KERNEL CUSTOM EXTREMEKRNL PINNED PASS (not stock PROCA delta)'
else
    python3 "$ROOT/scripts/r0s/check_proca_kernel_delta.py" \
        "$TMP/stock/kernel" "$TMP/packaged/kernel" ||
        die 'packaged kernel delta exceeds approved PROCA changes'
    echo 'PACKAGED KERNEL EXACT PROCA-DELTA PASS'
fi

echo '===== READ ONLY PACKAGED VENDOR_DLKM EROFS ====='
unzip -p "$ZIP" vendor_dlkm.img > "$TMP/vendor_dlkm.simg" ||
    die 'unable to extract vendor_dlkm.img'
[[ -s "$TMP/vendor_dlkm.simg" ]] || die 'vendor_dlkm image empty'
simg2img "$TMP/vendor_dlkm.simg" "$TMP/vendor_dlkm.raw" >/dev/null ||
    die 'invalid vendor_dlkm Android sparse image'
mkdir -p "$TMP/extracted"
fsck.erofs --extract="$TMP/extracted" "$TMP/vendor_dlkm.raw" > "$TMP/erofs.log" 2>&1 || {
    cat "$TMP/erofs.log" >&2
    die 'vendor_dlkm EROFS validation/extraction failed'
}
echo '===== MODULE IDENTITY AND VERMAGIC ====='
CUSTOM=false
if [[ -f "$WORK/kernel/.r0s_extremekrnl_a16_integrated" ]]; then
    CUSTOM=true
    EXPECTED_VERMAGIC='5.10.269-ExtremeKRNL-v2.5+ SMP preempt mod_unload modversions aarch64'
else
    EXPECTED_VERMAGIC='5.10.237-android12-9-31999025-abS901BXXSOGZH3 SMP preempt mod_unload modversions aarch64'
fi
for name in fingerprint.ko fingerprint_sysfs.ko input_booster_lkm.ko sec_debug_coredump.ko wlan.ko; do
    stock="$FW/vendor_dlkm/lib/modules/$name"
    work="$WORK/vendor_dlkm/lib/modules/$name"
    [[ -s "$stock" && -s "$work" ]] || die "source module missing: $name"
    count="$(find "$TMP/extracted" -type f -name "$name" | wc -l)"
    [[ "$count" == 1 ]] || die "unexpected packaged module count $name: $count"
    packed="$(find "$TMP/extracted" -type f -name "$name" -print -quit)"
    cmp -s "$work" "$packed" || die "packaged module differs from workdir: $name"
    if $CUSTOM; then
        cmp -s "$stock" "$work" && die "custom module identical to stock: $name"
        cmp -s "$ROOT/out/r0s_A16_ExtremeKRNL_KSU_hybrid_candidate/vendor_dlkm/lib/modules/$name" "$packed" ||
            die "packaged custom module differs from hybrid: $name"
    else
        cmp -s "$stock" "$work" || die "stock module was modified: $name"
    fi
    vermagic="$(modinfo -F vermagic "$packed")" ||
        die "unable to read vermagic for $name"
    [[ "$vermagic" == "$EXPECTED_VERMAGIC" ]] ||
        die "wrong module vermagic: $name: $vermagic"
    printf '%s WORK_PACKAGE_MATCH mode=%s sha256=' "$name" "$($CUSTOM && echo CUSTOM || echo STOCK)"
    sha256sum "$packed" | awk '{print $1}'
done
echo 'PACKAGED KERNEL / MODULE PROVENANCE PRECHECK PASS'
echo 'NOT FULL KERNEL ABI PASS: exported CRC/KMI and physical module loading unverified.'
echo 'BOOTLOADER TRUST, NORMAL BOOT, RECOVERY OTA, BOARD UNVERIFIED. E3099 ACTIVE.'
