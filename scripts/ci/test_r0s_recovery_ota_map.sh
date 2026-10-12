#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Synthetic read-only test for native GZH3 recovery crosscheck.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
cat > "$TMP/os_partitions_metadata.txt" <<'EOF'
super_partition_size=11744051200
super_partition_group=group_basic
super_group_basic_group_size=11739856896
super_group_basic_partition_list=system odm product vendor vendor_dlkm
EOF
{
    for p in system odm product vendor vendor_dlkm; do
        printf '%s /%s f2fs ro logical,first_stage_mount\n' "$p" "$p"
    done
    for p in boot vendor_boot dtbo recovery; do
        printf '/dev/block/by-name/%s /%s emmc defaults recoveryonly\n' "$p" "$p"
    done
} > "$TMP/vendor.fstab"
cp "$TMP/vendor.fstab" "$TMP/recovery.fstab"
printf 'system_ext /system_ext f2fs ro avb,logical,first_stage_mount\n' >> "$TMP/recovery.fstab"
bash "$ROOT/scripts/r0s/check_recovery_ota_map.sh" \
    "$TMP/recovery.fstab" "$TMP/vendor.fstab" "$TMP/os_partitions_metadata.txt" > "$TMP/ok"
grep -q 'NATIVE RECOVERY BLOCK LOCATOR CROSSCHECK PASS' "$TMP/ok"
grep -q 'RECOVERY-ONLY STALE/GENERIC ENTRY:' "$TMP/ok"
# A missing raw partition path must block.
sed -i '/\/dev\/block\/by-name\/vendor_boot /d' "$TMP/recovery.fstab"
if bash "$ROOT/scripts/r0s/check_recovery_ota_map.sh" \
    "$TMP/recovery.fstab" "$TMP/vendor.fstab" "$TMP/os_partitions_metadata.txt" >/dev/null 2>&1; then
    echo 'FAIL: missing stock recovery vendor_boot passed' >&2; exit 1
fi
printf '/dev/block/by-name/vendor_boot /vendor_boot emmc defaults recoveryonly\n' >> "$TMP/recovery.fstab"
# Fake extra super system_ext must block; recovery's generic fstab entry alone is allowed.
sed -i 's/system odm product vendor vendor_dlkm/system odm product vendor vendor_dlkm system_ext/' "$TMP/os_partitions_metadata.txt"
if bash "$ROOT/scripts/r0s/check_recovery_ota_map.sh" \
    "$TMP/recovery.fstab" "$TMP/vendor.fstab" "$TMP/os_partitions_metadata.txt" >/dev/null 2>&1; then
    echo 'FAIL: unexpected real super system_ext passed' >&2; exit 1
fi
sed -i 's/system odm product vendor vendor_dlkm system_ext/system odm product vendor vendor_dlkm/' "$TMP/os_partitions_metadata.txt"
# Recovery/vendor must both include native odm, even if staged map has it.
sed -i '/^odm \/odm /d' "$TMP/vendor.fstab"
if bash "$ROOT/scripts/r0s/check_recovery_ota_map.sh" \
    "$TMP/recovery.fstab" "$TMP/vendor.fstab" "$TMP/os_partitions_metadata.txt" >/dev/null 2>&1; then
    echo 'FAIL: missing stock vendor ODM passed' >&2; exit 1
fi
printf 'r0s synthetic recovery/OTA crosscheck PASS (no stock firmware used)\n'