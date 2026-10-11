#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Synthetic fixture only: never downloads actual firmware or flashes a device.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/kernel" "$TMP/system/system" "$TMP/vendor/etc"
printf '%s' 'S901BXXSOGZH3/S901BOXMOGZH3/CP_VERSION/BOOT_VERSION' > "$TMP/.extracted"
cat > "$TMP/os_partitions_metadata.txt" <<'META'
use_dynamic_partitions=true
super_partition_size=11744051200
super_partition_group=group_basic
super_group_basic_group_size=11739856896
META
printf 'ro.build.version.sdk=36\n' > "$TMP/system/system/build.prop"
for f in boot vendor_boot dtbo; do printf 'synthetic %s\n' "$f" > "$TMP/kernel/$f.img"; done
printf '/dev/block/by-name/metadata /metadata ext4 ro wait\n' > "$TMP/vendor/etc/fstab.s5e9925"
bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > "$TMP/ok.log"
grep -q 'FIRMWARE METADATA PRECHECK PASS' "$TMP/ok.log"
sed -i 's/super_group_basic_group_size=11739856896/super_group_basic_group_size=11600000000/' "$TMP/os_partitions_metadata.txt"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: geometry mismatch went undetected' >&2; exit 1
fi
sed -i 's/super_group_basic_group_size=11600000000/super_group_basic_group_size=11739856896/' "$TMP/os_partitions_metadata.txt"
printf '%s' 'BAD_DEVICE/S901BOXMOGZH3/CP_VERSION/BOOT_VERSION' > "$TMP/.extracted"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: model mismatch went undetected' >&2; exit 1
fi
echo 'r0s synthetic firmware-inspector tests PASS (no real firmware involved)'
