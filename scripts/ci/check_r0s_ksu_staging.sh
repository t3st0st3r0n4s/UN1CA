#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# No root, Android boot, APK download or kernel build. Staging guard only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
STAGE="staging/r0s/ksunext"
fail() { printf 'r0s KSU STAGING FAIL: %s\n' "$*" >&2; exit 1; }
for f in "$STAGE/install_manager.sh" "$STAGE/unica_ksunext_manager.rc" "$STAGE/manifest.env"; do
    [[ -f "$f" ]] || fail "missing staged source $f"
done
sh -n "$STAGE/install_manager.sh" || fail 'installer syntax'
bash -n "$STAGE/manifest.env" || fail 'manifest syntax'
# Reading a staging manifest is not a build action.
source "$STAGE/manifest.env"
[[ "$A16_KERNEL_QUALIFIED" == false && "$A16_ROOT_SELINUX_QUALIFIED" == false &&
   "$A16_PROMOTION_ALLOWED" == false ]] || fail 'A16 root unexpectedly promoted'
[[ "$MANAGER_RELEASE" == v3.4.1 && "$MANAGER_PACKAGE_SUFFIX" == 33333 ]] || fail 'manager release drift'
[[ "$MANAGER_SHA256" =~ ^[0-9a-f]{64}$ ]] || fail 'manager digest invalid'
[[ "$MANAGER_URL" == https://github.com/KernelSU-Next/KernelSU-Next/releases/download/v3.4.1/* ]] || fail 'unexpected manager origin'
grep -Fq 'MARKER="/data/local/tmp/.unica_ksunext_manager_33333_installed"' "$STAGE/install_manager.sh" || fail 'release marker drift'
grep -Fq '/system/bin/pm install -r "$TEMP"' "$STAGE/install_manager.sh" || fail 'manager installation semantics drift'
grep -Fq '[ -f "$MARKER" ] && exit 0' "$STAGE/install_manager.sh" || fail 'one-shot semantics drift'
grep -Fq 'exec_background u:r:ksu:s0 root root -- /system/bin/sh /system/etc/unica/ksunext/install_manager.sh' "$STAGE/unica_ksunext_manager.rc" || fail 'staged init declaration drift'
# UN1CA only auto-applies module directories under platform/..., target/...,
# and unica/mods. There must be no active symlink or copied manager init file.
for p in platform/exynos2200/patches target/r0s/patches; do
    [[ ! -d "$p" ]] || ! grep -Rlq 'unica_ksunext_manager\|manager_payload\.bin' "$p" || fail "unexpected active KSU integration in $p"
done
[[ ! -e unica/mods/preload/system/etc/init/unica_ksunext_manager.rc ]] || fail 'manager init mistakenly made active'
[[ ! -e unica/mods/preload/system/etc/unica/ksunext/manager_payload.bin ]] || fail 'manager payload mistakenly made active'
[[ ! -e "$STAGE/module.prop" ]] || fail 'staging must not be an active module'
echo 'r0s KSU STAGING PASS — preserved installer design, root INACTIVE; A16 kernel/SELinux still unverified'
