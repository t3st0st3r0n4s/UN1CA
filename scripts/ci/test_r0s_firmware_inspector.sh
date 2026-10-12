#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Synthetic fixture only: never downloads actual firmware or flashes a device.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/kernel" "$TMP/system/system" "$TMP/vendor/etc"
for p in odm product vendor vendor_dlkm; do mkdir -p "$TMP/$p"; done
printf '%s' 'S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3' > "$TMP/.extracted"
cat > "$TMP/os_partitions_metadata.txt" <<'META'
use_dynamic_partitions=true
super_partition_size=11744051200
super_partition_group=group_basic
super_group_basic_group_size=11739856896
super_group_basic_partition_list=system odm product vendor vendor_dlkm
META
printf 'ro.build.version.sdk=36\n' > "$TMP/system/system/build.prop"
for f in boot vendor_boot dtbo; do printf 'synthetic %s\n' "$f" > "$TMP/kernel/$f.img"; done
{
    for p in system odm product vendor vendor_dlkm; do
        printf '%s /%s erofs ro wait\n' "$p" "$p"
    done
    for p in boot vendor_boot dtbo recovery; do
        printf '/dev/block/by-name/%s /%s emmc defaults wait\n' "$p" "$p"
    done
} > "$TMP/vendor/etc/fstab.s5e9925"
bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > "$TMP/ok.log"
grep -q 'FIRMWARE METADATA PRECHECK PASS' "$TMP/ok.log"
grep -q 'native_vendor_fstab_locators=PASS' "$TMP/ok.log"
# Reject an incorrect system_ext-for-odm substitution in real super metadata.
sed -i 's/system odm product vendor vendor_dlkm/system product vendor vendor_dlkm system_ext/' "$TMP/os_partitions_metadata.txt"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: unexpected logical set accepted' >&2; exit 1
fi
sed -i 's/system product vendor vendor_dlkm system_ext/system odm product vendor vendor_dlkm/' "$TMP/os_partitions_metadata.txt"
# Verify that the stock vendor fstab must contain ODM.
sed -i '/^odm \/odm /d' "$TMP/vendor/etc/fstab.s5e9925"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: missing ODM vendor fstab locator accepted' >&2; exit 1
fi
printf 'odm /odm erofs ro wait\n' >> "$TMP/vendor/etc/fstab.s5e9925"
sed -i 's/super_group_basic_group_size=11739856896/super_group_basic_group_size=11600000000/' "$TMP/os_partitions_metadata.txt"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: geometry mismatch went undetected' >&2; exit 1
fi
sed -i 's/super_group_basic_group_size=11600000000/super_group_basic_group_size=11739856896/' "$TMP/os_partitions_metadata.txt"
printf '%s' 'BAD_DEVICE/S901BOXMOGZH3/S901BXXSOGZH3' > "$TMP/.extracted"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: model mismatch went undetected' >&2; exit 1
fi
# Make sure an old four-component fake marker is not accepted.
printf '%s' 'S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3/EXTRA' > "$TMP/.extracted"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: four-component marker incorrectly accepted' >&2; exit 1
fi
# Ensure invalid third (MODEM) component is rejected too.
printf '%s' 'S901BXXSOGZH3/S901BOXMOGZH3/BAD_MODEM' > "$TMP/.extracted"
if bash "$ROOT/scripts/r0s/inspect_extracted_firmware.sh" "$TMP" > /dev/null 2>&1; then
    echo 'FAIL: bad MODEM marker incorrectly accepted' >&2; exit 1
fi
echo 'r0s synthetic firmware-inspector tests PASS (no real firmware involved)'
