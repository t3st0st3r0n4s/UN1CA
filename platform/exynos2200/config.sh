# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# First-stage configuration for Samsung Exynos 2200 (S901B/r0s).
# Deliberately no reused ExtremeKRNL, cross-device blobs or vendor substitutions.

TARGET_USE_DYNAMIC_PARTITIONS=true
TARGET_SUPER_GROUP_NAME="group_basic"
TARGET_OS_SINGLE_SYSTEM_IMAGE="essi"
TARGET_OS_BUILD_SYSTEM_EXT_PARTITION=false
# Keep UN1CA's native Android 16 EROFS default.
TARGET_OS_FILE_SYSTEM_TYPE="erofs"
