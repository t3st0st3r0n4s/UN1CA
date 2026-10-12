# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Galaxy S22 5G Exynos (SM-S901B) -- initial Android 16 native-source port.
# The UN1CA `essi` source is the same S901B Android 16 firmware as our target.
# Therefore keep all Samsung product features identical to the source until a
# device-backed reason to override an individual value is established.

# This target is intentionally coupled to the native `essi` source configuration.
source "$SRC_DIR/unica/configs/essi.sh"

# Copy the current native source feature map into the matching target variables.
# Bash's ${!SOURCE_@} expansion enumerates the current SOURCE_* variable names.
for _r0s_source_key in "${!SOURCE_@}"; do
    case "$_r0s_source_key" in
        SOURCE_EXTRA_FIRMWARES) continue ;;  # array handled below
    esac
    printf -v "TARGET_${_r0s_source_key#SOURCE_}" '%s' "${!_r0s_source_key}"
done
unset _r0s_source_key

TARGET_NAME="Galaxy S22 5G (Exynos)"
TARGET_CODENAME="r0s"
TARGET_PLATFORM="exynos2200"
TARGET_ASSERT_MODEL=("SM-S901B")
TARGET_EXTRA_FIRMWARES=()

# Preserve the native Android 16 S901B firmware on both sides of the build.
# Firmware revision is inherited from UN1CA until a reproducible A16 pin is selected.
TARGET_FIRMWARE="$SOURCE_FIRMWARE"

# These super/group sizes are confirmed by real GZH3 Android 16 lpdump.
# Stock logical list: system odm product vendor vendor_dlkm.
# This does NOT qualify ROM packaging or recovery OTA.
TARGET_SUPER_PARTITION_SIZE=11744051200
TARGET_GROUP_BASIC_SIZE=11739856896
