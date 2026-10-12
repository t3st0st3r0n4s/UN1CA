#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Stock GZH3 recovery/vendor fstab vs actual super vs staged UN1CA block map.
# READ-ONLY; does not assert that the Samsung recovery updater supports UN1CA.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[[ "$#" == 3 ]] || { echo "Usage: $0 <stock-recovery.fstab> <stock-vendor.fstab> <os_partitions_metadata.txt>" >&2; exit 2; }
REC="$1"
VEN="$2"
META="$3"
STAGED="$ROOT/target/r0s/installer/recovery.fstab"
LOCK="$ROOT/target/r0s/installer/assertions.edify"
fail() { printf 'r0s RECOVERY OTA MAP BLOCKED: %s\n' "$*" >&2; exit 2; }
for f in "$REC" "$VEN" "$META" "$STAGED" "$LOCK"; do
    [[ -s "$f" ]] || fail "file missing or empty: $f"
done

getmeta() { sed -n "s/^$1=//p" "$META" | head -1; }
[[ "$(getmeta super_partition_size)" == "11744051200" ]] || fail 'unexpected native super size'
[[ "$(getmeta super_partition_group)" == "group_basic" ]] || fail 'unexpected native super group'
[[ "$(getmeta super_group_basic_group_size)" == "11739856896" ]] || fail 'unexpected native group capacity'

expected="$(printf '%s\n' system odm product vendor vendor_dlkm | LC_ALL=C sort)"
actual="$(getmeta super_group_basic_partition_list | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort)"
[[ "$actual" == "$expected" ]] || fail "native super partition list unexpected: $actual"

# Exactly these five logical partition names may enter the staged OTA map.
staged="$(awk '$1 !~ /^#/ && NF >= 2 && $1 !~ /^\// {print $1}' "$STAGED" | LC_ALL=C sort)"
[[ "$staged" == "$expected" ]] || fail "staged logical set differs from native super: $staged"

has_locator() {
    local f="$1" dev="$2" mountpoint="$3"
    awk -v d="$dev" -v m="$mountpoint" '
        $1 == d && $2 == m {found=1}
        END {exit !found}
    ' "$f"
}

printf '===== RECOVERY / SUPER LOGICAL PARTITION CROSSCHECK =====\n'
for part in system odm product vendor vendor_dlkm; do
    for f in "$REC" "$VEN" "$STAGED"; do
        has_locator "$f" "$part" "/$part" ||
            fail "missing /$part logical locator in $(basename "$f")"
    done
    printf 'logical_%s=RECOVERY+VENDOR+STAGED_MATCH\n' "$part"
done

printf '\n===== RAW BOOT PARTITION LOCATORS =====\n'
for part in boot vendor_boot dtbo recovery; do
    dev="/dev/block/by-name/$part"
    for f in "$REC" "$VEN" "$STAGED"; do
        has_locator "$f" "$dev" "/$part" ||
            fail "missing /$part raw locator in $(basename "$f")"
    done
    printf 'raw_%s=RECOVERY+VENDOR+STAGED_MATCH\n' "$part"
done

# Samsung stock recovery includes system_ext despite GZH3 super lacking
# a separate system_ext logical partition. This is NOT an OTA input.
if has_locator "$REC" system_ext /system_ext; then
    printf '\nRECOVERY-ONLY STALE/GENERIC ENTRY: /system_ext found; absent from native GZH3 super.\n'
fi
if has_locator "$STAGED" system_ext /system_ext; then
    fail 'system_ext must not be staged as a distinct GZH3 logical partition'
fi
grep -Eq '^[[:space:]]*abort\("E3099:.*NOT qualified for flashing' "$LOCK" ||
    fail 'mandatory E3099 abort missing'

printf '\nNATIVE RECOVERY BLOCK LOCATOR CROSSCHECK PASS\n'
printf 'OTA updater support, generated ZIP safety, recovery flashing and BOARD UNVERIFIED; E3099 LOCKED\n'