#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only native GZH3/r0s ROM workdir audit; no repacking or flashing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="${1:-$ROOT/out/fw/SM-S901B_EUX}"
WORK="${2:-$ROOT/out/target/r0s/work_dir}"
fail() { printf 'r0s WORKDIR BLOCKED: %s\n' "$*" >&2; exit 2; }

[[ -s "$FW/.extracted" && -s "$WORK/.completed" ]] ||
    fail 'missing firmware or completed-workdir marker'
[[ "$(cat "$FW/.extracted")" == "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3" ]] ||
    fail 'not the pinned GZH3 firmware'

printf '===== FIVE NATIVE LOGICAL PARTITIONS =====\n'
expected="$(printf '%s\n' system odm product vendor vendor_dlkm | LC_ALL=C sort)"
actual="$(find "$WORK" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' |
    grep -Ev '^(configs|kernel)$' | LC_ALL=C sort)"
[[ "$actual" == "$expected" ]] || fail "unexpected workdir partition set: $actual"
for p in system odm product vendor vendor_dlkm; do
    [[ -d "$WORK/$p" ]] || fail "missing workdir $p"
    [[ -s "$WORK/configs/fs_config-$p" ]] || fail "missing fs_config-$p"
    [[ -s "$WORK/configs/file_context-$p" ]] || fail "missing file_context-$p"
    du -sh "$WORK/$p"
done
[[ ! -e "$WORK/system_ext" && ! -L "$WORK/system_ext" ]] ||
    fail 'separate system_ext image source unexpectedly staged'
[[ -d "$WORK/system/system/system_ext" ]] ||
    fail 'native embedded system_ext folder missing'
printf 'system_ext=EMBEDDED\n'

printf '\n===== ANDROID 16 AND UN1CA PROPERTIES =====\n'
PROPS="$WORK/system/system/build.prop"
[[ -s "$PROPS" ]] || fail 'assembled system build.prop missing'
for expected_prop in ro.build.version.sdk=36 ro.product.device=r0s ro.unica.device=r0s; do
    grep -Fxq "$expected_prop" "$PROPS" ||
        fail "missing workdir property: $expected_prop"
done
grep -Eq '^ro.unica.version=' "$PROPS" || fail 'UN1CA version not set'
grep -E '^(ro.build.version.sdk|ro.product.device|ro.unica.device|ro.unica.version|ro.unica.fingerprint)=' "$PROPS"

printf '\n===== REBUILT APK/JAR ARCHIVES =====\n'
for rel in \
    system/system/priv-app/SecSettings/SecSettings.apk \
    system/system/system_ext/priv-app/SystemUI/SystemUI.apk \
    system/system/framework/framework.jar \
    system/system/framework/services.jar
do
    [[ -s "$WORK/$rel" ]] || fail "missing archive $rel"
    unzip -tq "$WORK/$rel" >/dev/null || fail "invalid archive/CRC: $rel"
    printf 'ZIP_CRC_PASS %s\n' "$rel"
done

printf '\n===== KERNEL MODULE PROVENANCE =====\n'
export PATH="$ROOT/out/tools/bin:$PATH"
if [[ -f "$WORK/kernel/.r0s_extremekrnl_a16_integrated" ]]; then
    echo 'KERNEL_MODE=GZH3_EXTREMEKRNL_A16_KSU'
    python3 "$ROOT/scripts/r0s/integrate_extremekrnl_a16.py" --verify ||
        fail 'custom kernel workdir provenance verification failed'
else
    echo 'KERNEL_MODE=NATIVE_GZH3_PROCA_ONLY'
    for mod in fingerprint.ko fingerprint_sysfs.ko input_booster_lkm.ko sec_debug_coredump.ko wlan.ko; do
        a="$FW/vendor_dlkm/lib/modules/$mod"
        b="$WORK/vendor_dlkm/lib/modules/$mod"
        [[ -s "$a" && -s "$b" ]] || fail "missing module $mod"
        cmp -s "$a" "$b" || fail "stock module was modified: $mod"
        sha256sum "$b"
    done
fi

printf '\n===== WORKDIR BOOT-CHAIN HEADERS / SIZE CAPS =====\n'
export PATH="$ROOT/out/tools/bin:$PATH"
command -v unpack_bootimg >/dev/null || fail 'unpack_bootimg missing'
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
for p in boot vendor_boot dtbo; do
    stock="$FW/kernel/$p.img"
    staged="$WORK/kernel/$p.img"
    [[ -s "$stock" && -s "$staged" ]] || fail "missing $p stock/work image"
    case "$p" in
      boot) max=67108864 ;;
      vendor_boot) max=33554432 ;;
      dtbo) max=8388608 ;;
    esac
    bytes="$(stat -c '%s' "$staged")"
    (( bytes > 0 && bytes <= max )) || fail "$p over image-cap reference"
    printf 'image=%s stock_bytes=%s work_bytes=%s cap=%s\n' \
        "$p.img" "$(stat -c '%s' "$stock")" "$bytes" "$max"
    sha256sum "$staged"
    if cmp -s "$stock" "$staged"; then
        printf '%s MATCHES_STOCK\n' "$p.img"
    else
        printf '%s MODIFIED_FROM_STOCK (ABI and runtime unverified)\n' "$p.img"
    fi
    if [[ "$p" != dtbo ]]; then
        mkdir "$TMP/$p"
        unpack_bootimg --boot_img "$staged" --out "$TMP/$p" > "$TMP/$p.txt" 2>&1 ||
            fail "$p could not be unpacked"
        # Android unpack_bootimg prints DIFFERENT header labels for boot and
        # vendor_boot; testing both against the boot label rejects valid v4.
        if ! bash "$ROOT/scripts/r0s/check_unpacked_boot_header.sh" "$p" "$TMP/$p.txt"; then
            printf '%s header parser output:\n' "$p" >&2
            cat "$TMP/$p.txt" >&2
            fail "rebuilt $p header verification failed"
        fi
        grep -E '^(os version|os patch level|boot image header version|vendor boot image header version|vendor command line args|command line args):' \
            "$TMP/$p.txt" || true
    fi
done

printf '\n===== STORAGE / SAFETY =====\n'
du -sh "$WORK"
df -h "$ROOT"
printf 'WORKDIR HOST AUDIT PASS (not kernel ABI, recovery OTA, target-files or BOARD)\n'
printf 'ROM INSTALLER SOURCE UNCHANGED\n'