#!/usr/bin/env bash
# Isolated Android 16 r0s ExtremeKRNL + built-in KernelSU Next candidate.
# No ROM modifications, no flashing, no device access, no E3099 removal.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/out/kernel_tmp-exynos2200"
LEGACY_SRC="$ROOT/out/kernel_candidate_extreme_a16"
ART="$SRC/build/out/r0s"
REMOTE="https://github.com/milxnaq/android_kernel_samsung_s5e9925.git"
KERNEL_PIN="78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95"
# Same policy as .github/workflows/r0s-kernel-zip.yml: latest stable GitHub Release.
KSU_TAG=""
KSU_PIN=""
MODE="--check"
if [[ $# -gt 0 ]]; then MODE="$1"; fi
die() { echo "A16 EXTREMEKRNL BLOCKED: $*" >&2; exit 2; }

[[ $# -le 1 ]] || die 'usage: build_extremekrnl_a16.sh [--check|--prepare|--build]'
case "$MODE" in --check|--prepare|--build|--self-test) ;; *) die "unsupported mode: $MODE" ;; esac
if [[ "$MODE" == --self-test ]]; then
  [[ "$KERNEL_PIN" =~ ^[0-9a-f]{40}$ ]] || die 'bad kernel pin'
  bash -n "$ROOT/scripts/r0s/build_extremekrnl_a16.sh" || die 'syntax'
  echo 'A16 ExtremeKRNL/latest-stable KernelSU policy syntax fixtures PASS'
  exit 0
fi
grep -Fq 'abort("E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.");' \
  "$ROOT/target/r0s/installer/assertions.edify" || die 'E3099 missing'
[[ -f "$ROOT/out/fw/SM-S901B_EUX/.extracted" ]] || die 'GZH3 extraction absent'
[[ "$(cat "$ROOT/out/fw/SM-S901B_EUX/.extracted")" == 'S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3' ]] || die 'wrong firmware'
for cmd in git make python3 cpio lz4 zip depmod modinfo sha256sum awk find stat; do
  command -v "$cmd" >/dev/null 2>&1 || die "missing host tool: $cmd"
done
echo "kernel source: $REMOTE"
echo "kernel pin: $KERNEL_PIN"
echo 'KSU Next: latest stable GitHub Release (resolved at prepare/build)'
echo "candidate checkout: $SRC"
echo 'Never reuse native GZH3 5.10.237 modules with the new 5.10.269 kernel.'
if [[ -e "$SRC" ]]; then
  [[ -d "$SRC/.git" ]] || die 'existing path is not kernel checkout'
  URL="$(git -C "$SRC" remote get-url origin)" || die 'no origin'
  [[ "$URL" == "$REMOTE" || "$URL" == 'https://github.com/milxnaq/android_kernel_samsung_s5e9925' ]] || die 'wrong origin'
  [[ -z "$(git -C "$SRC" status --porcelain --untracked-files=no --ignore-submodules=all)" ]] || die 'tracked kernel source changes present'
fi
FREE="$(df -BG --output=avail "$ROOT" | tail -1 | tr -cd '0-9')"
[[ "$FREE" =~ ^[0-9]+$ ]] || die 'disk space unknown'
echo "free_disk_GiB_rounded_up=$FREE"
if [[ "$MODE" == --check ]]; then
  echo 'CHECK ONLY — no download or build'
  if (( FREE < 24 )); then echo 'CAPACITY WARNING: below 24 GiB staging floor (not measured peak)'; fi
  exit 0
fi
# Preserve any successfully compiled kernel and its source checkout.
# A different latest-stable KernelSU version needs an explicit new build workspace;
# never silently switch the checkout while retaining an older build marker.
[[ ! -e "$ART/.r0s_a16_kernel_host_pass" ]] ||
  die 'successful kernel build already exists; preserve it and use a fresh build workspace for a new KernelSU release'
# Match CI: GitHub's /releases/latest excludes pre-releases; pin its exact tag.
KSU_TAG="$(python3 - <<'PY'
import json
from urllib.request import Request, urlopen
url = "https://api.github.com/repos/KernelSU-Next/KernelSU-Next/releases/latest"
request = Request(url, headers={"Accept": "application/vnd.github+json",
                                "User-Agent": "UN1CA-r0s-host-kernel"})
with urlopen(request, timeout=20) as response:
    print(json.load(response)["tag_name"])
PY
)" || die 'cannot resolve latest stable KernelSU Next release'
[[ "$KSU_TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "invalid stable KernelSU tag: $KSU_TAG"
echo "Latest stable KernelSU Next: $KSU_TAG"
# Never download a duplicate multi-gigabyte kernel checkout when the previously
# prepared candidate is still at its original path. Move it explicitly first.
if [[ ! -e "$SRC" && -d "$LEGACY_SRC/.git" ]]; then
  die "existing prepared checkout at $LEGACY_SRC; move it to $SRC before prepare/build (no re-clone)"
fi
if [[ ! -d "$SRC/.git" ]]; then
  (( FREE >= 24 )) || die 'at least 24 GiB free requested for fresh clone'
  [[ ! -e "$SRC" ]] || die 'candidate path already exists'
  git clone --single-branch --branch sixteen --filter=blob:none "$REMOTE" "$SRC" || die 'clone failed; partial files retained'
fi
git -C "$SRC" cat-file -e "$KERNEL_PIN^{commit}" || die 'pinned kernel missing'
git -C "$SRC" checkout --detach "$KERNEL_PIN" || die 'cannot pin kernel'
[[ "$(git -C "$SRC" rev-parse HEAD)" == "$KERNEL_PIN" ]] || die 'source drift'
git -C "$SRC" submodule sync --recursive
git -C "$SRC" submodule update --init --recursive || die 'submodule preparation failed'
git -C "$SRC/KernelSU-Next" fetch origin "refs/tags/$KSU_TAG:refs/tags/$KSU_TAG" ||
  die "KernelSU Next $KSU_TAG tag unavailable"
KSU_PIN="$(git -C "$SRC/KernelSU-Next" rev-parse "refs/tags/$KSU_TAG^{commit}")" ||
  die 'cannot resolve immutable KernelSU Next commit'
[[ "$KSU_PIN" =~ ^[0-9a-f]{40}$ ]] || die 'invalid KernelSU Next commit'
git -C "$SRC/KernelSU-Next" checkout --detach "$KSU_PIN" || die 'KSU pin checkout failed'
[[ "$(git -C "$SRC/KernelSU-Next" rev-parse HEAD)" == "$KSU_PIN" ]] || die 'wrong KSU pin'
[[ -f "$SRC/arch/arm64/configs/r0s.config" ]] || die 'r0s config missing'
grep -q '^CONFIG_KSU=y$' "$SRC/arch/arm64/configs/ksu.config" || die 'KSU build fragment missing'
grep -q '^SUBLEVEL = 269$' "$SRC/Makefile" || die 'kernel base changed'
echo "PREPARE PASS — exact A16 S901B kernel source and KernelSU Next $KSU_TAG ($KSU_PIN)"
if [[ "$MODE" == --prepare ]]; then exit 0; fi
FREE="$(df -BG --output=avail "$ROOT" | tail -1 | tr -cd '0-9')"
(( FREE >= 12 )) || die 'less than 12 GiB free before compiler'
echo '===== REAL BUILD: upstream ExtremeKRNL -m r0s -k ====='
(cd "$SRC" && bash ./build.sh -m r0s -k) || die 'kernel compilation failed'
grep -q '^CONFIG_KSU=y$' "$SRC/out/.config" || die 'CONFIG_KSU not enabled in build'
grep -q '^CONFIG_MODVERSIONS=y$' "$SRC/out/.config" || die 'module ABI versioning disabled'
echo '===== VERIFY KERNEL / VENDOR_BOOT / DTBO ====='
for image in boot vendor_boot dtbo; do
  FILE="$ART/$image.img"
  [[ -s "$FILE" ]] || die "$image.img not built"
  SIZE="$(stat -c %s "$FILE")"
  case "$image" in boot) CAP=67108864 ;; vendor_boot) CAP=33554432 ;; dtbo) CAP=8388608 ;; esac
  (( SIZE <= CAP )) || die "$image.img exceeds partition limit"
  echo "$image.img $SIZE bytes sha256=$(sha256sum "$FILE" | awk '{print $1}')"
done
echo '===== VERIFY FIVE REBUILT VENDOR MODULES ====='
for name in fingerprint.ko fingerprint_sysfs.ko input_booster_lkm.ko sec_debug_coredump.ko wlan.ko; do
  FILE="$ART/modules/lib/modules/$name"
  [[ -s "$FILE" ]] || die "required module missing: $name"
  MAGIC="$(modinfo -F vermagic "$FILE")" || die "invalid vermagic: $name"
  [[ "$MAGIC" == 5.10.269-* ]] || die "$name has mismatched kernel: $MAGIC"
  echo "$name $MAGIC sha256=$(sha256sum "$FILE" | awk '{print $1}')"
done
printf 'source=%s\nksunext=%s\nbuild_only=true\nrom_integrated=false\nboard_pass=false\n' \
  "$KERNEL_PIN" "$KSU_PIN" > "$ART/.r0s_a16_kernel_host_pass"
echo 'A16 EXTREMEKRNL/KSU NEXT BUILD HOST PASS — NOT ROM INTEGRATED'
echo 'Existing E3099-locked ROM and FYI3 bootloader unchanged.'
