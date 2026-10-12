#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only comparison of STOCK and UN1CA workdir boot/vendor_boot internals.
# No image changes, privilege elevation, target-files generation or flashing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="${1:-$ROOT/out/fw/SM-S901B_EUX}"
WORK="${2:-$ROOT/out/target/r0s/work_dir}"
die() { printf 'r0s POSTBUILD BOOT REVIEW BLOCKED: %s\n' "$*" >&2; exit 2; }
[[ -s "$FW/.extracted" && -s "$WORK/.completed" ]] ||
    die 'missing stock extraction or completed workdir'
[[ "$(cat "$FW/.extracted")" == "S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3" ]] ||
    die 'wrong source firmware'
export PATH="$ROOT/out/tools/bin:$PATH"
for cmd in unpack_bootimg sha256sum cpio lz4 gzip file cmp diff awk; do
    command -v "$cmd" >/dev/null || die "required tool missing: $cmd"
done
grep -Eq '^[[:space:]]*abort\("E3099:.*NOT qualified for flashing' \
    "$ROOT/target/r0s/installer/assertions.edify" || die 'E3099 installer lock missing'

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
unpack_one() {
    local side="$1" part="$2" image="$3"
    mkdir -p "$TMP/$side/$part"
    unpack_bootimg --boot_img "$image" --out "$TMP/$side/$part" \
        > "$TMP/$side/$part.header.txt" 2>&1 ||
        die "cannot parse $side $part image"
    bash "$ROOT/scripts/r0s/check_unpacked_boot_header.sh" \
        "$part" "$TMP/$side/$part.header.txt" >/dev/null ||
        die "bad $side $part header"
    printf '%s_%s_sha256=' "$side" "$part"
    sha256sum "$image" | awk '{print $1}'
    grep -E '^(boot image header version|vendor boot image header version|vendor command line args|command line args|os patch level):' \
        "$TMP/$side/$part.header.txt" || true
}
printf '===== STOCK vs MODIFIED BOOT HEADER =====\n'
unpack_one stock boot "$FW/kernel/boot.img"
unpack_one work boot "$WORK/kernel/boot.img"
[[ -s "$TMP/stock/boot/kernel" && -s "$TMP/work/boot/kernel" ]] ||
    die 'unpacked boot kernel missing'
printf '\n===== STOCK vs MODIFIED BOOT KERNEL =====\n'
sha256sum "$TMP/stock/boot/kernel" "$TMP/work/boot/kernel"
if cmp -s "$TMP/stock/boot/kernel" "$TMP/work/boot/kernel"; then
    echo 'boot_kernel=BYTE_IDENTICAL'
else
    echo 'boot_kernel=MODIFIED_FROM_STOCK (needs PROCA change review and ABI check)'
fi
printf '\n===== STOCK vs MODIFIED VENDOR_BOOT HEADER =====\n'
unpack_one stock vendor_boot "$FW/kernel/vendor_boot.img"
unpack_one work vendor_boot "$WORK/kernel/vendor_boot.img"

ramdisk_stream() {
    local input="$1" type
    type="$(file -b "$input")"
    case "$type" in
        *LZ4*) lz4 -dc "$input" ;;
        *gzip*) gzip -dc "$input" ;;
        *cpio*) cat "$input" ;;
        *) die "unrecognised vendor ramdisk format: $input ($type)" ;;
    esac
}
printf '\n===== VENDOR_BOOT RAMDISK FILES / FSTAB =====\n'
total_fstab=0
for side in stock work; do
    count=0
    while IFS= read -r -d '' ramdisk; do
        count=$((count + 1))
        name="$(basename "$ramdisk")"
        printf '\nside=%s ramdisk=%s bytes=%s type=%s\n' \
            "$side" "$name" "$(stat -c %s "$ramdisk")" "$(file -b "$ramdisk")"
        sha256sum "$ramdisk"
        index="$TMP/$side-$name.list"
        ramdisk_stream "$ramdisk" | cpio -it --quiet > "$index" ||
            die "cannot list $side $name"
        grep -Ei '(^|/)(fstab[^/]*|init[^/]*)$' "$index" | head -60 || true
        while IFS= read -r entry; do
            [[ -n "$entry" ]] || continue
            safe="$(printf '%s' "$entry" | tr '/' '_' | tr -cd 'A-Za-z0-9_.-')"
            dest="$TMP/$side-$name-$safe"
            ramdisk_stream "$ramdisk" | cpio -i --quiet --to-stdout "$entry" > "$dest" ||
                die "cannot read $side $entry"
            [[ -s "$dest" ]] || die "empty $side $entry"
            total_fstab=$((total_fstab + 1))
            printf '%s/%s sha256=' "$name" "$entry"
            sha256sum "$dest" | awk '{print $1}'
            grep -E '^[[:space:]]*(system|vendor|product|odm|vendor_dlkm|system_ext)[[:space:]]' "$dest" || true
        done < <(grep -E '(^|/)fstab[^/]*$' "$index" | LC_ALL=C sort || true)
    done < <(find "$TMP/$side/vendor_boot" -maxdepth 1 -type f \
        -name 'vendor_ramdisk*' -print0 | sort -z)
    (( count >= 1 )) || die "no vendor ramdisks in $side vendor_boot"
    printf '%s_vendor_ramdisk_count=%s\n' "$side" "$count"
done
(( total_fstab > 0 )) || die 'no vendor ramdisk fstabs found'
printf '\n===== STOCK vs MODIFIED VENDOR FSTAB DIFFS =====\n'
found_pairs=0
while IFS= read -r stock; do
    work="$TMP/work-${stock#"$TMP/stock-"}"
    if [[ -f "$work" ]]; then
        found_pairs=$((found_pairs + 1))
        printf '\nfile=%s\n' "$(basename "$stock")"
        if cmp -s "$stock" "$work"; then
            printf 'fstab=IDENTICAL\n'
        else
            printf 'fstab=CHANGED (diff first 90 lines)\n'
            diff -u "$stock" "$work" | sed -n '1,90p' || true
        fi
    fi
done < <(find "$TMP" -maxdepth 1 -type f -name 'stock-vendor_ramdisk*-*fstab*' | LC_ALL=C sort)
(( found_pairs > 0 )) || die 'no matched stock/work vendor ramdisk fstab'
printf '\n===== STORAGE / WORKDIR CACHE NOTE =====\n'
du -sh "$WORK"
df -h "$ROOT"
work_hash="$(cat "$WORK/.completed")"
current_hash="$(
    find "$ROOT/unica" "$ROOT/platform/exynos2200" "$ROOT/target/r0s" -type f -print0 |
    sort -z | xargs -0 sha1sum | sha1sum | cut -d ' ' -f 1
)"
if [[ "$work_hash" == "$current_hash" ]]; then
    echo 'workdir_cache_hash=CURRENT'
else
    echo 'workdir_cache_hash=DIFFERS (documentation may cause make_rom.sh to rebuild)'
    echo 'Do not call make_rom.sh without checking whether a rebuild is needed.'
fi
echo 'POSTBUILD BOOT/FSTAB HOST INVENTORY COMPLETE'
echo 'KERNEL MODULE ABI, NORMAL-BOOT SELINUX, OTA AND BOARD UNVERIFIED; E3099 ACTIVE'