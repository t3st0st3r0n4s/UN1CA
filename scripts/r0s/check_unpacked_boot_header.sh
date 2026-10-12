#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Validate unpack_bootimg text output format by image kind. No writes.
set -euo pipefail
[[ "$#" == 2 ]] || { echo 'Usage: check_unpacked_boot_header.sh <boot|vendor_boot> <unpack_bootimg-log>' >&2; exit 2; }
kind="$1"
output="$2"
[[ -s "$output" ]] || { echo "Missing unpack_bootimg output: $output" >&2; exit 2; }
case "$kind" in
    boot) expected='boot image header version: 4' ;;
    vendor_boot) expected='vendor boot image header version: 4' ;;
    *) echo "Unsupported image kind: $kind" >&2; exit 2 ;;
esac
if ! grep -Fxq "$expected" "$output"; then
    printf 'Expected %s for %s; absent or incorrect in %s\n' "$expected" "$kind" "$output" >&2
    exit 2
fi
printf '%s header v4 parser PASS\n' "$kind"