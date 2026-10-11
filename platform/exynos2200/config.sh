# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Native Exynos 2200 Android 16 stage. Partition sizes are provisional:
# cross-referenced with LineageOS s5e9925-common lineage-23.2, not stock GZH3.
# No Android 15 vendor blobs, fstab overrides or custom kernel are imported.
TARGET_USE_DYNAMIC_PARTITIONS=true
TARGET_SUPER_GROUP_NAME="group_basic"
TARGET_OS_SINGLE_SYSTEM_IMAGE="essi"
TARGET_OS_BUILD_SYSTEM_EXT_PARTITION=false
TARGET_OS_FILE_SYSTEM_TYPE="erofs"
TARGET_BOOT_PARTITION_SIZE=67108864
TARGET_DTBO_PARTITION_SIZE=8388608
TARGET_VENDOR_BOOT_PARTITION_SIZE=33554432
TARGET_CACHE_PARTITION_SIZE=629145600
