#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only A16 r0s custom-kernel postbuild audit; no ROM/phone writes.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/out/kernel_tmp-exynos2200"
ART="$SRC/build/out/r0s"
FW="$ROOT/out/fw/SM-S901B_EUX"
WORK="$ROOT/out/target/r0s/work_dir"
KPIN=78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95
SPIN=""
die() { echo "r0s CUSTOM KERNEL AUDIT BLOCKED: $*" >&2; exit 2; }
[[ $# -eq 0 || ( $# -eq 1 && "$1" == --self-test ) ]] || die 'usage: audit_extremekrnl_a16_candidate.sh [--self-test]'
if [[ $# -eq 1 && "$1" == --self-test ]]; then
  bash -n "$ROOT/scripts/r0s/audit_extremekrnl_a16_candidate.sh"
  [[ "$KPIN" =~ ^[a-f0-9]{40}$ ]] || die 'invalid kernel pin'
  echo 'Custom kernel audit self-test PASS'
  exit 0
fi
export PATH="$ROOT/out/tools/bin:$PATH"
for cmd in git grep sed sha256sum modinfo unpack_bootimg find stat file lz4 cpio awk cmp wc sort; do
  command -v "$cmd" >/dev/null || die "missing $cmd"
done
[[ -s "$FW/.extracted" && -s "$WORK/.completed" ]] || die 'native GZH3 extraction/workdir missing'
[[ "$(cat "$FW/.extracted")" == 'S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3' ]] || die 'firmware mismatch'
[[ -s "$ART/.r0s_a16_kernel_host_pass" ]] || die 'build PASS marker absent'
SPIN="$(sed -n 's/^ksunext=//p' "$ART/.r0s_a16_kernel_host_pass")"
[[ "$SPIN" =~ ^[a-f0-9]{40}$ ]] || die 'invalid KernelSU Next commit in build provenance'
[[ "$(git -C "$SRC" rev-parse HEAD)" == "$KPIN" ]] || die 'kernel source pin drift'
[[ "$(git -C "$SRC/KernelSU-Next" rev-parse HEAD)" == "$SPIN" ]] || die 'KSU source pin drift'
grep -Fxq CONFIG_KSU=y "$SRC/out/.config" || die 'CONFIG_KSU is not enabled'
grep -Fxq CONFIG_MODVERSIONS=y "$SRC/out/.config" || die 'module ABI versioning disabled'
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
echo '===== CUSTOM BOOT IMAGES ====='
for name in boot vendor_boot dtbo; do
  img="$ART/$name.img"
  [[ -s "$img" && -s "$FW/kernel/$name.img" ]] || die "missing candidate/stock $name image"
  size="$(stat -c %s "$img")"
  case "$name" in boot) cap=67108864;; vendor_boot) cap=33554432;; dtbo) cap=8388608;; esac
  (( size <= cap )) || die "$name exceeds partition-size reference"
  printf '%s bytes=%s sha256=' "$name.img" "$size"
  sha256sum "$img" | awk '{print $1}'
  if [[ "$name" != dtbo ]]; then
    mkdir -p "$TMP/$name"
    unpack_bootimg --boot_img "$img" --out "$TMP/$name" > "$TMP/$name.header" 2>&1 || die "cannot unpack $name"
    bash "$ROOT/scripts/r0s/check_unpacked_boot_header.sh" "$name" "$TMP/$name.header" || die "$name header invalid"
    grep -E '^(boot image header version|vendor boot image header version|command line args|vendor command line args|os version|os patch level):' "$TMP/$name.header" || true
  fi
done
echo '===== FIVE MATCHED VENDOR_DLKM MODULES ====='
for name in fingerprint fingerprint_sysfs input_booster_lkm sec_debug_coredump wlan; do
  path="$ART/modules/lib/modules/$name.ko"
  [[ -s "$path" ]] || die "missing $name.ko"
  magic="$(modinfo -F vermagic "$path")"
  [[ "$magic" == "5.10.269-ExtremeKRNL-v2.5+ "* ]] || die "$name wrong vermagic: $magic"
  printf '%s sha256=' "$name.ko"
  sha256sum "$path" | awk '{print $1}'
  echo "depends=$(modinfo -F depends "$path")"
done
for name in modules.alias modules.dep modules.load modules.softdep; do
  [[ -f "$ART/modules/lib/modules/$name" ]] || die "missing $name"
done
echo "modules.load entries=$(wc -l < "$ART/modules/lib/modules/modules.load")"
echo '===== VENDOR_BOOT FRAGMENTS ====='
count=0
while IFS= read -r -d '' file; do
  count=$((count+1))
  name="$(basename "$file")"
  echo "$name: $(file -b "$file")"
  lz4 -dc "$file" | cpio -it --quiet > "$TMP/$name.list" || die "corrupt $name ramdisk"
  echo "$name entries=$(wc -l < "$TMP/$name.list")"
  grep -E '(^|/)(fstab[^/]*|modules\.load|fingerprint\.ko|wlan\.ko)$' "$TMP/$name.list" | head -30 || true
done < <(find "$TMP/vendor_boot" -maxdepth 1 -type f -name 'vendor_ramdisk*' -print0 | sort -z)
(( count >= 2 )) || die "expected two vendor_boot fragments, found $count"
echo 'CUSTOM KERNEL POSTBUILD INSPECTION PASS — ROM INTEGRATION / BOARD DEFERRED; BOARD DEFERRED'
