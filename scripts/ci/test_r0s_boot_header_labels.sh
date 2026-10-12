#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Synthetic parse-label tests (no boot binaries, board, ROM or firmware needed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HELPER="$ROOT/scripts/r0s/check_unpacked_boot_header.sh"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT

printf '%s\n' 'boot magic: ANDROID!' 'os version: 12.0.0' 'boot image header version: 4' > "$TMP/boot.log"
printf '%s\n' 'boot magic: VNDRBOOT' 'vendor boot image header version: 4' > "$TMP/vendor.log"
bash "$HELPER" boot "$TMP/boot.log"
bash "$HELPER" vendor_boot "$TMP/vendor.log"

if bash "$HELPER" boot "$TMP/vendor.log" >/dev/null 2>&1; then
    echo 'FAIL: vendor_boot label mistakenly accepted as boot label' >&2; exit 1
fi
if bash "$HELPER" vendor_boot "$TMP/boot.log" >/dev/null 2>&1; then
    echo 'FAIL: boot label mistakenly accepted as vendor_boot label' >&2; exit 1
fi

printf '%s\n' 'vendor boot image header version: 3' > "$TMP/vendor_bad.log"
if bash "$HELPER" vendor_boot "$TMP/vendor_bad.log" >/dev/null 2>&1; then
    echo 'FAIL: vendor_boot v3 accepted instead of v4' >&2; exit 1
fi
echo 'r0s boot and vendor_boot header labels test PASS (synthetic only)'