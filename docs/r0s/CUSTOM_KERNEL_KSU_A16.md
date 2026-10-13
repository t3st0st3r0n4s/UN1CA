# A16 S901B ExtremeKRNL / KernelSU Next integration

FOUND an active Android 16 Exynos 2200 custom kernel with built-in KSU:
https://github.com/milxnaq/android_kernel_samsung_s5e9925/tree/sixteen
Exact source commit: 78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95
Released 4 October 2026; S901B r0s.config and build.sh -m r0s -k.
Uses Samsung OSRC S711NKSSIEZI2 changes; not exact GZH3 source.
Linux 5.10.269 / ExtremeKRNL-v2.5, vs native GZH3 5.10.237.

The custom kernel submodule was v3.4.0. We explicitly pin the same
KernelSU Next v3.4.1 version as working TachyonOS to exact commit
8f902aeb16033024143ae36cf711df902cf02fae.

To start the REAL host build on Ubuntu (no phone access):
  cd ~/android/UN1CA
  bash scripts/r0s/build_extremekrnl_a16.sh --check
  bash scripts/r0s/build_extremekrnl_a16.sh --prepare
  bash scripts/r0s/build_extremekrnl_a16.sh --build

Default --check makes no downloads. Prepare clones the large kernel
source and pinned submodules. Build invokes the existing upstream
kernel compile and produces boot.img, vendor_boot.img, dtbo.img
and modules, isolated under out/kernel_candidate_extreme_a16/.
At least 24 GiB before initial clone and 12 GiB before compilation
are enforced floors; peak disk use may be significantly higher.
Compiler may download clang r614150. Do not delete original ROM or
target-files automatically to make room.

Built-in CONFIG_KSU=y and CONFIG_MODVERSIONS=y and 5 matching newly
compiled vendor_dlkm modules are mandatory in the host build gate.
Original GZH3 modules (5.10.237) cannot be reused with the new
5.10.269 custom kernel without establishing compatibility.

After a true host build pass, integrate via UN1CA's existing patch
module system, updating boot/vendor_boot/dtbo and ALL required
vendor_dlkm modules together. The staged manager init/install
lifecycle is already retained under staging/r0s/ksunext and stays
inactive until kernel and A16 SELinux qualification.

No ROM image, active kernel module or phone partition is modified.
E3099 remains active. This is not a flashing instruction.