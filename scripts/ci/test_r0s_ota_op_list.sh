#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Test REAL upstream GENERATE_OP_LIST with tiny fake images. No firmware/ROM/flash.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OTA="$ROOT/scripts/internal/build_full_ota_zip.sh"
INSTALL="$ROOT/scripts/utils/install_utils.sh"
fail() { printf 'r0s OTA OP-LIST FAIL: %s\n' "$*" >&2; exit 1; }

# Extract the genuine UN1CA generator, without executing the full OTA builder.
generator="$(sed -n '/^GENERATE_OP_LIST()$/,/^}$/p' "$OTA")"
[[ "$generator" == *'for p in $PARTITIONS_LIST'* ]] ||
    fail 'upstream OTA generator structure changed'
[[ "$generator" == *'GET_IMAGE_SIZE'* ]] || fail 'upstream OTA size reader changed'
[[ "$generator" == *'remove_all_groups'* ]] || fail 'upstream dynamic op semantics changed'
eval "$generator"

PARTITIONS_LIST="$(sed -n 's/^PARTITIONS_LIST="\([^"]*\)"/\1/p' "$INSTALL")"
[[ "$PARTITIONS_LIST" == *system* && "$PARTITIONS_LIST" == *odm* ]] ||
    fail 'upstream supported partition list changed'

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
TMP_DIR="$TMP"
BUILD_INFO="$(printf '%s\n' 'super_partition_group=group_basic' 'super_group_basic_group_size=11739856896')"
EXPECTED="$(printf '%s\n' system odm product vendor vendor_dlkm | LC_ALL=C sort)"

# Tiny stand-ins let us run the real upstream generation logic without creating
# images, needing root or consuming the stock S901B firmware extraction.
for name in system odm product vendor vendor_dlkm; do
    truncate -s 4096 "$TMP/$name.img"
done
GET_IMAGE_SIZE() { stat -c '%s' "$1"; }
LOGE() { printf 'upstream build error: %s\n' "$*" >&2; }

assert_native_ops() {
    local generated="$TMP/dynamic_partitions_op_list"
    [[ -f "$generated" ]] || return 1
    grep -Fxq 'remove_all_groups' "$generated" || return 1
    grep -Fxq 'add_group group_basic 11739856896' "$generated" || return 1
    [[ "$(awk '$1 == "add" {print $2}' "$generated" | LC_ALL=C sort)" == "$EXPECTED" ]] || return 1
    [[ "$(awk '$1 == "resize" {print $2}' "$generated" | LC_ALL=C sort)" == "$EXPECTED" ]] || return 1
    [[ "$(awk '$1 == "resize" {print $3}' "$generated" | LC_ALL=C sort -u)" == "4096" ]] || return 1
    [[ "$(awk '$1 == "resize" {sum += $3} END {print sum+0}' "$generated")" == 20480 ]] || return 1
    [[ ! -e "$TMP/system_ext.img" ]] || return 1
}

GENERATE_OP_LIST
assert_native_ops || fail 'real upstream generator did not produce exactly five native GZH3 partitions'
printf 'NATIVE OTA OP-LIST PASS: five logical images, no system_ext, correct super group\n'

# Negative: the generic upstream generator WILL admit system_ext if an image
# is unexpectedly present. Our native layout validator must refuse that.
truncate -s 4096 "$TMP/system_ext.img"
GENERATE_OP_LIST
grep -Eq '^add system_ext group_basic$' "$TMP/dynamic_partitions_op_list" ||
    fail 'negative fixture no longer reaches generic system_ext path'
if assert_native_ops; then
    fail 'invented system_ext unexpectedly accepted as native GZH3'
fi
rm -f "$TMP/system_ext.img"
printf 'NEGATIVE PASS: unsupported distinct system_ext flagged\n'

# Negative: synthetic images beyond group maximum must be rejected by the
# genuine upstream size guard, not silently promoted to a flashable image.
GET_IMAGE_SIZE() { printf '%s\n' 12000000000; }
if (GENERATE_OP_LIST) >/dev/null 2>&1; then
    fail 'oversized dynamic partitions unexpectedly accepted'
fi
printf 'NEGATIVE PASS: oversized dynamic group blocked\n'
printf 'r0s upstream OTA operation-list synthetic test PASS (no firmware used)\n'