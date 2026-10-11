#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Synthetic fixture only; no Samsung firmware, host kernel or device.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/kernel" "$TMP/vendor/etc" "$TMP/vendor_dlkm/lib/modules"
for part in boot vendor_boot dtbo; do
    printf 'synthetic %s\n' "$part" > "$TMP/kernel/$part.img"
done
for part in boot vendor_boot; do
    printf 'header_version=4\nos_version=16.0.0\n' > "$TMP/${part}.img_metadata.txt"
done
printf 'synthetic /vendor/etc/fstab\n' > "$TMP/vendor/etc/fstab.s5e9925"
bash "$ROOT/scripts/r0s/inspect_boot_chain.sh" "$TMP" > "$TMP/ok.log"
grep -q 'BOOT IMAGE METADATA PRECHECK PASS' "$TMP/ok.log"
sed -i 's/header_version=4/header_version=3/' "$TMP/boot.img_metadata.txt"
if bash "$ROOT/scripts/r0s/inspect_boot_chain.sh" "$TMP" >/dev/null 2>&1; then
    echo 'FAIL: invalid boot header accepted' >&2; exit 1
fi
sed -i 's/header_version=3/header_version=4/' "$TMP/boot.img_metadata.txt"
truncate -s 67108865 "$TMP/kernel/boot.img"
if bash "$ROOT/scripts/r0s/inspect_boot_chain.sh" "$TMP" >/dev/null 2>&1; then
    echo 'FAIL: oversized boot image accepted' >&2; exit 1
fi
echo 'r0s synthetic boot-chain checks PASS (not stock firmware qualification)'
