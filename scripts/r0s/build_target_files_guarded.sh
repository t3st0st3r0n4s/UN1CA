#!/usr/bin/env bash
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# Upstream target-files builder only. No make_rom.sh, no OTA, no flashing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
MODE="--check"
if [[ $# -gt 0 ]]; then MODE="$1"; fi
if [[ $# -gt 1 || "$MODE" != "--check" && "$MODE" != "--build" ]]; then
    echo "Usage: bash scripts/r0s/build_target_files_guarded.sh [--check|--build]" >&2
    exit 2
fi
echo '===== NATIVE A16 TARGET-FILES PREFLIGHT ====='
python3 "$ROOT/scripts/r0s/preflight_target_files.py" || exit 2
# The r0s hybrid ROM now promises the same KSU manager auto-install
# as TachyonOS. Refuse to package a pre-promotion workdir by accident.
if [[ -f "$ROOT/out/target/r0s/work_dir/kernel/.r0s_extremekrnl_a16_integrated" ]]; then
    python3 "$ROOT/scripts/r0s/install_ksunext_manager_a16.py" --verify || {
        echo 'BLOCKED: manager preload absent. Apply --apply-existing to the completed workdir before packaging.' >&2
        exit 2
    }
fi
if [[ "$MODE" == "--check" ]]; then
    echo 'CHECK ONLY — no workdir rebuild, target-files or flashable OTA'
    exit 0
fi

FINAL="$ROOT/out/r0s_A16_GZH3_HOST_ONLY-target_files.zip"
PARTIAL="$FINAL.partial.zip"
[[ ! -e "$FINAL" && ! -e "$PARTIAL" ]] || {
    echo 'BLOCKED: pre-existing target-files output (never overwrite)' >&2; exit 2;
}
# Upstream buildenv uses optional unset variables, so nounset is disabled here.
set +u
source "$ROOT/buildenv.sh" r0s
set -u
[[ "$TARGET_CODENAME" == "r0s" &&
   "$SOURCE_PLATFORM_SDK_VERSION" == "36" &&
   "$TARGET_PLATFORM_SDK_VERSION" == "36" &&
   "$SOURCE_FIRMWARE" == "$TARGET_FIRMWARE" &&
   "$SOURCE_FIRMWARE" == SM-S901B/EUX/* ]] || {
    echo 'BLOCKED: unexpected generated native A16 config' >&2; exit 2;
}
# Repeat capacity after buildenv, which can prepare host tools.
python3 "$ROOT/scripts/r0s/preflight_target_files.py" || exit 2
bash "$ROOT/scripts/r0s/inspect_built_workdir.sh" >/dev/null || exit 2
bash "$ROOT/scripts/r0s/inspect_postbuild_boot_ramdisks.sh" >/dev/null || exit 2
echo '===== DIRECT UPSTREAM TARGET-FILES BUILDER (NO ROM REBUILD) ====='
cleanup_partial() { [[ ! -e "$PARTIAL" ]] || rm -f -- "$PARTIAL"; }
trap cleanup_partial EXIT
"$ROOT/scripts/internal/create_target_files_zip.sh" "$PARTIAL"
python3 "$ROOT/scripts/r0s/check_target_files_zip.py" "$PARTIAL"
mv -- "$PARTIAL" "$FINAL"
trap - EXIT
sha256sum "$FINAL"
echo "HOST-ONLY TARGET-FILES CREATED: $FINAL"
echo 'NOT flashable or board-qualified; BOARD remains unverified.'
