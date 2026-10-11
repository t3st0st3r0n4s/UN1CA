#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Read-only configuration gate: never downloads firmware, builds, or flashes.
set -eo pipefail

die() { printf 'r0s CONFIG FAIL: %s\n' "$*" >&2; exit 1; }
note() { printf 'r0s: %s\n' "$*"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

bash -n platform/exynos2200/config.sh target/r0s/config.sh || die "Bash syntax"
bash -n scripts/ci/check_r0s_config.sh || die "self syntax"
test -f target/r0s/installer/assertions.edify || die "missing installer lock"

# UN1CA's own generator is the oracle for whether the port is structurally valid.
# Keep nounset disabled: upstream buildenv.sh uses optional, unset variables.
source ./buildenv.sh r0s || die "UN1CA buildenv / gen_config_file.sh failed"

[[ "$TARGET_CODENAME" == "r0s" ]] || die "wrong target codename"
[[ "$TARGET_PLATFORM" == "exynos2200" ]] || die "wrong target platform"
[[ "$TARGET_OS_SINGLE_SYSTEM_IMAGE" == "essi" ]] || die "wrong SSI"
[[ "$SOURCE_PLATFORM_SDK_VERSION" == "36" && "$TARGET_PLATFORM_SDK_VERSION" == "36" ]] || die "expected Android 16 / API 36"
[[ "$SOURCE_FIRMWARE" == "$TARGET_FIRMWARE" ]] || die "source and target firmware diverged"
[[ "$SOURCE_FIRMWARE" == SM-S901B/EUX/* ]] || die "source is not native S901B/EUX"
[[ "$TARGET_PRODUCT_SHIPPING_API_LEVEL" == "$SOURCE_PRODUCT_SHIPPING_API_LEVEL" ]] || die "shipping API mismatch"
[[ "$TARGET_BOARD_API_LEVEL" == "$SOURCE_BOARD_API_LEVEL" ]] || die "board API mismatch"
[[ "$TARGET_USE_DYNAMIC_PARTITIONS" == "true" ]] || die "dynamic partitions disabled"
[[ "$TARGET_OS_FILE_SYSTEM_TYPE" == "erofs" ]] || die "unexpected image format"
[[ "$TARGET_OS_BUILD_SYSTEM_EXT_PARTITION" == "false" ]] || die "unexpected system_ext layout"
[[ "$TARGET_SUPER_GROUP_NAME" == "group_basic" ]] || die "wrong super group"
[[ "$TARGET_SUPER_PARTITION_SIZE" == "11744051200" ]] || die "unexpected provisional super size"
[[ "$TARGET_GROUP_BASIC_SIZE" == "11739856896" ]] || die "unexpected provisional group size"
[[ "$TARGET_BOOT_PARTITION_SIZE" == "67108864" ]] || die "unexpected provisional boot size"
[[ "$TARGET_VENDOR_BOOT_PARTITION_SIZE" == "33554432" ]] || die "unexpected provisional vendor_boot size"
[[ "$TARGET_DTBO_PARTITION_SIZE" == "8388608" ]] || die "unexpected provisional dtbo size"
[[ "$TARGET_CACHE_PARTITION_SIZE" == "629145600" ]] || die "unexpected provisional cache size"
[[ "$TARGET_ASSERT_MODEL" == "SM-S901B" ]] || die "wrong model assertion"

# The native S901B source is also the S901B target: enforce feature equality.
# This catches a renamed/new SOURCE_* property on a future upstream rebase.
feature_count=0
for src_var in "${!SOURCE_@}"; do
    case "$src_var" in
        SOURCE_EXTRA_FIRMWARES) continue ;;
    esac
    tgt_var="TARGET_${src_var#SOURCE_}"
    [[ -v "$tgt_var" ]] || die "missing $tgt_var (source: $src_var)"
    [[ "${!src_var}" == "${!tgt_var}" ]] || die "$src_var differs from $tgt_var"
    feature_count=$((feature_count + 1))
done
(( feature_count >= 55 )) || die "unexpectedly small native feature map ($feature_count)"
note "native source/target mapping PASS ($feature_count matching SOURCE_* fields)"

# Protect against accidentally importing Android 15 blobs/patches.
for patch_dir in platform/exynos2200/patches target/r0s/patches; do
    if [[ -d "$patch_dir" ]] && find "$patch_dir" -type f -print -quit | grep -q .; then
        die "unreviewed active device patches: $patch_dir"
    fi
done

# Prevent WIP installation. A provisional Lineage-derived *block locator*
# exists solely to exercise the OTA resolver; it is NOT native A16 recovery.
grep -Eq '^[[:space:]]*abort\("E3099:.*NOT qualified for flashing' \
    target/r0s/installer/assertions.edify || die "WIP installer abort absent"

test -f target/r0s/installer/recovery.fstab || die "missing provisional OTA block map"
grep -q 'PROVISIONAL UN1CA r0s updater-script BLOCK MAP' \
    target/r0s/installer/recovery.fstab || die "provisional map qualification marker absent"
note "STAGED OTA block locator only — native A16 recovery.fstab NOT qualified"

note "CONFIG PASS (source-only; firmware, kernel, ROM and BOARD not qualified)"
