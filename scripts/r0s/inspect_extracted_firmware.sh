#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only native S901B Android 16 extraction qualification; no firmware downloads.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FWDIR="${1:-$ROOT/out/fw/SM-S901B_EUX}"
fail() { printf 'FIRMWARE EVIDENCE BLOCKED: %s\n' "$*" >&2; exit 2; }
field() { local key="$1" file="$2"; sed -n "s/^${key}=//p" "$file" | head -n 1; }

[[ -d "$FWDIR" ]] || fail "no extracted SM-S901B_EUX firmware directory: $FWDIR"
[[ -f "$FWDIR/.extracted" ]] || fail "missing .extracted marker"
[[ -f "$FWDIR/os_partitions_metadata.txt" ]] || fail "missing upstream os_partitions_metadata.txt"

# Samsung FOTA <latest> and UN1CA's .downloaded/.extracted markers are
# PDA/CSC/MODEM (three values). The Odin archive itself may contain
# AP/BL/CP/CSC tarballs; that is a different notion of "four-part".
EXTRACTED="$(cat "$FWDIR/.extracted")"
[[ "$EXTRACTED" =~ ^S901B[[:alnum:]]+/S901B[[:alnum:]]+/S901B[[:alnum:]]+$ ]] ||
    fail "expected S901B FOTA marker PDA/CSC/MODEM, got: $EXTRACTED"
IFS='/' read -r PDA CSC MODEM <<< "$EXTRACTED"
ODIN_MARKER="$ROOT/out/odin/SM-S901B_EUX/.downloaded"
if [[ -f "$ODIN_MARKER" ]]; then
    [[ "$(cat "$ODIN_MARKER")" == "$EXTRACTED" ]] || fail "Odin download marker differs from extracted firmware"
fi

EXPECTED_PDA="${R0S_EXPECTED_PDA:-S901BXXSOGZH3}"
EXPECTED_CSC="${R0S_EXPECTED_CSC:-S901BOXMOGZH3}"
[[ "$PDA" == "$EXPECTED_PDA" ]] || fail "PDA differs from research candidate: got $PDA, expected $EXPECTED_PDA"
[[ "$CSC" == "$EXPECTED_CSC" ]] || fail "CSC differs from research candidate: got $CSC, expected $EXPECTED_CSC"

META="$FWDIR/os_partitions_metadata.txt"
PARTITION_SIZE="$(field super_partition_size "$META")"
GROUP="$(field super_partition_group "$META")"
[[ "$PARTITION_SIZE" =~ ^[0-9]+$ ]] || fail "invalid or missing super_partition_size"
[[ "$GROUP" == group_basic ]] || fail "unexpected super group: $GROUP"
GROUP_SIZE="$(field "super_${GROUP}_group_size" "$META")"
[[ "$GROUP_SIZE" =~ ^[0-9]+$ ]] || fail "invalid or missing super group size"
(( GROUP_SIZE > 0 && GROUP_SIZE < PARTITION_SIZE )) || fail "invalid partition/group sizing"

PARTITION_LIST="$(field "super_${GROUP}_partition_list" "$META")"
[[ -n "$PARTITION_LIST" ]] || fail 'missing native super partition list'
mapfile -t partitions < <(tr ' ' '\n' <<< "$PARTITION_LIST" | sed '/^$/d' | LC_ALL=C sort)
mapfile -t expected_partitions < <(printf '%s\n' system odm product vendor vendor_dlkm | LC_ALL=C sort)
[[ "${partitions[*]}" == "${expected_partitions[*]}" ]] ||
    fail "unexpected native GZH3 logical partition set: $PARTITION_LIST"
for part in "${expected_partitions[@]}"; do
    [[ -d "$FWDIR/$part" ]] || fail "missing extracted logical partition: $part"
done

printf 'r0s Android 16 firmware evidence (read-only)\n'
printf 'firmware_fota_triplet=%s\n' "$EXTRACTED"
printf 'super_partition_size=%s\n' "$PARTITION_SIZE"
printf 'super_partition_group=%s\n' "$GROUP"
printf 'super_group_size=%s\n' "$GROUP_SIZE"
printf 'super_partition_list=%s\n' "$PARTITION_LIST"

if [[ "$PARTITION_SIZE" != 11744051200 || "$GROUP_SIZE" != 11739856896 ]]; then
    printf 'GEOMETRY REVIEW REQUIRED: extracted A16 sizes differ from provisional FYI3 values.\n' >&2
    # Continue reporting useful evidence; fail below, before any PASS claim.
    GEOMETRY_MATCH=false
else
    GEOMETRY_MATCH=true
fi

if [[ -f "$FWDIR/system/system/build.prop" ]]; then
    PROP_SDK="$(sed -n -e 's/^ro.build.version.sdk=//p' -e 's/^ro.system.build.version.sdk=//p' "$FWDIR/system/system/build.prop" | head -n 1)"
    printf 'source_sdk=%s\n' "${PROP_SDK:-UNVERIFIED}"
    [[ "$PROP_SDK" == 36 ]] || fail "native source SDK is not verified as 36"
else
    fail "missing system/system/build.prop"
fi

for part in boot vendor_boot dtbo; do
    file="$FWDIR/kernel/$part.img"
    [[ -f "$file" ]] || fail "missing native kernel/$part.img"
    sha256sum "$file"
done

printf 'fstab_candidates:\n'
if [[ -d "$FWDIR/vendor/etc" ]]; then
    find "$FWDIR/vendor/etc" -maxdepth 2 -type f -name 'fstab*' -print | LC_ALL=C sort
else
    fail "no native vendor/etc directory for fstab inventory"
fi
# Validate stock vendor first-stage fstab, distinct from recovery fstab.
VENDOR_FSTAB="$FWDIR/vendor/etc/fstab.s5e9925"
[[ -f "$VENDOR_FSTAB" ]] || fail 'native vendor fstab.s5e9925 missing'
for part in boot vendor_boot dtbo recovery; do
    awk -v dev="/dev/block/by-name/$part" -v mp="/$part" '
        $1 == dev && $2 == mp { found=1 }
        END { if (!found) exit 1 }
    ' "$VENDOR_FSTAB" || fail "vendor fstab missing /$part"
done
for part in "${expected_partitions[@]}"; do
    awk -v p="$part" -v mp="/$part" '
        $1 == p && $2 == mp { found=1 }
        END { if (!found) exit 1 }
    ' "$VENDOR_FSTAB" || fail "vendor fstab missing logical /$part"
done
printf 'native_vendor_fstab_locators=PASS (recovery still unverified)\n'
printf 'native_vendor_modules:\n'
if [[ -d "$FWDIR/vendor_dlkm/lib/modules" ]]; then
    find "$FWDIR/vendor_dlkm/lib/modules" -maxdepth 2 -type f -name '*.ko' -printf '%P\n' | LC_ALL=C sort
else
    printf 'NOT_FOUND_IN_EXPECTED_DIRECTORY\n'
fi

$GEOMETRY_MATCH || fail "A16 super geometry differs; update r0s config after verification"
printf 'FIRMWARE METADATA PRECHECK PASS (source layout only; recovery, kernel, OTA and BOARD remain UNVERIFIED)\n'
