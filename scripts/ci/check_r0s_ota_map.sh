#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Source-only UN1CA OTA resolver smoke test. No firmware download, ROM build, or flash.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
fail() { printf 'r0s OTA-MAP FAIL: %s\n' "$*" >&2; exit 1; }
mapfile -t entries < <(awk 'NF && $1 !~ /^#/ {print $1 " " $2}' target/r0s/installer/recovery.fstab)
for e in \
  '/dev/block/by-name/boot /boot' \
  '/dev/block/by-name/vendor_boot /vendor_boot' \
  '/dev/block/by-name/dtbo /dtbo' \
  '/dev/block/by-name/recovery /recovery'; do
    printf '%s\n' "${entries[@]}" | grep -Fxq "$e" || fail "missing raw mapping $e"
done
for p in system odm product vendor vendor_dlkm; do
  printf '%s\n' "${entries[@]}" | grep -Fxq "$p /$p" || fail "missing logical mapping $p"
done
[[ ! -e target/r0s/installer/install-end.edify ]] || fail 'Unexpected device-specific extra updater script'
# Stock GZH3 super metadata contains exactly five logical partitions.
actual_logical="$(awk 'NF && $1 !~ /^#/ && $1 !~ /^\/dev\/block\// {print $1}' target/r0s/installer/recovery.fstab | LC_ALL=C sort)"
expected_logical="$(printf '%s\n' system odm product vendor vendor_dlkm | LC_ALL=C sort)"
[[ "$actual_logical" == "$expected_logical" ]] || fail 'staged logical set differs from native GZH3 super'

# Keep the installer abort strictly before ANY write operation in generated updater-script.
grep -Eq '^abort\("E3099:.*NOT qualified for flashing' target/r0s/installer/assertions.edify || fail 'E3099 lock missing'
ota_source='scripts/internal/build_full_ota_zip.sh'
assert_line="$(grep -nF 'PRINT_ASSERTIONS "$BUILD_INFO"' "$ota_source" | head -1 | cut -d: -f1)"
write_line="$(grep -nF 'update_dynamic_partitions(package_extract_file(' "$ota_source" | head -1 | cut -d: -f1)"
[[ "$assert_line" =~ ^[0-9]+$ && "$write_line" =~ ^[0-9]+$ ]] || fail 'OTA assertion/write source changed'
(( assert_line < write_line )) || fail 'Updater may write partitions before WIP abort'
# Extract actual UN1CA resolver without executing heavyweight build_utils.sh or its external tools.
resolver="$(sed -n '/^GET_DEVICE_FROM_MOUNTPOINT()$/,/^}$/p' scripts/utils/install_utils.sh)"
[[ "$resolver" == *'map_partition('* ]] || fail 'Upstream resolver changed unexpectedly'
[[ "$resolver" == *'FSTAB_FILE='* ]] || fail 'Upstream fstab resolver changed unexpectedly'
eval "$resolver"
_CHECK_NON_EMPTY_PARAM() { [[ -n "${2:-}" ]]; }
LOGE() { printf 'LOGE: %s\n' "$*" >&2; }
LOGW() { printf 'LOGW: %s\n' "$*" >&2; }
IS_VALID_PARTITION_NAME() {
  case "$1" in system|vendor|product|system_ext|odm|vendor_dlkm|odm_dlkm|system_dlkm) return 0;; esac
  return 1
}
SRC_DIR="$ROOT" TARGET_CODENAME=r0s TARGET_USE_DYNAMIC_PARTITIONS=true
for p in boot vendor_boot dtbo recovery; do
    actual="$(GET_DEVICE_FROM_MOUNTPOINT "/$p")"
    [[ "$actual" == "\"/dev/block/by-name/$p\"" ]] || fail "bad locator /$p: $actual"
done
for p in system odm product vendor vendor_dlkm; do
    actual="$(GET_DEVICE_FROM_MOUNTPOINT "/$p")"
    [[ "$actual" == "map_partition(\"$p\")" ]] || fail "bad logical locator /$p: $actual"
done
if (GET_DEVICE_FROM_MOUNTPOINT '/init_boot' >/dev/null 2>&1); then
    fail 'Unsupported /init_boot unexpectedly resolved'
fi
if (GET_DEVICE_FROM_MOUNTPOINT '/dt' >/dev/null 2>&1); then
    fail 'Unsupported /dt unexpectedly resolved'
fi
printf 'r0s OTA-MAP PREPARED: native GZH3 five-partition map PASS; recovery and BOARD not qualified\n'
