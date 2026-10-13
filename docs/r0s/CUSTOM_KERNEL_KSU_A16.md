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

Already ran --prepare using the earlier candidate directory name?
Move the checkout rather than re-cloning ~1 GiB of Git history:
  test ! -e out/kernel_tmp-exynos2200
  mv out/kernel_candidate_extreme_a16 out/kernel_tmp-exynos2200
The canonical location matches TachyonOS's old out/kernel_tmp-exynos2200.

Default --check makes no downloads. Prepare clones the large kernel
source and pinned submodules. Build invokes the existing upstream
kernel compile and produces boot.img, vendor_boot.img, dtbo.img
and modules, isolated under out/kernel_tmp-exynos2200/.
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
## Real Ubuntu host build result — 2026-10-13

**HOST BUILD PASS (not ROM-integrated / not device-qualified).** The user ran
`bash scripts/r0s/build_extremekrnl_a16.sh --build` successfully at the
canonical checkout `out/kernel_tmp-exynos2200/`, after reusing the already
prepared source and downloading upstream clang-r614150. The compile and
upstream kernel ZIP generation completed, and our five-module verification
passed. The log contains one nonfatal `sorttable.c` unused-variable warning;
no reported compile errors. `CONFIG_KSU=y`, `CONFIG_MODVERSIONS=y`,
`KSU: Yes`, `Permissive: No` were observed; the latter is a compile mode,
**not evidence of Android runtime SELinux enforcing**.

Source: `78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95`.
KernelSU Next: `8f902aeb16033024143ae36cf711df902cf02fae` (v3.4.1).
Kernel release: `5.10.269-ExtremeKRNL-v2.5+`.

| Host artifact (relative to checkout `build/out/r0s/`) | Size (bytes) | SHA256 |
| --- | ---: | --- |
| `boot.img` | 29810688 | `d60d14256ed89767820b4de71d1d471c301bd6a63af3db009a9def97e27cec18` |
| `vendor_boot.img` | 24965120 | `2708bca83980d8ef3678462573bdcd4d75682cbf7237f0601c70b9151f8b4e5f` |
| `dtbo.img` | 2206476 | `18a0c5572edcbf6a83bb55a407e956f78c34306e76b97fb9747a988b09c507df` |

Five rebuilt `build/out/r0s/modules/lib/modules/*.ko` files carry the exact
same `5.10.269-ExtremeKRNL-v2.5+ SMP preempt mod_unload modversions aarch64`
vermagic:

| Vendor module | SHA256 |
| --- | --- |
| `fingerprint.ko` | `7b4dcae483c32e211599393cf7142fcb63824437264265f2bd9253fc49c98545` |
| `fingerprint_sysfs.ko` | `fd6744c69f1aff1e1a6f2f536f0f48ba99ca6d7df4d70574543141b38edb5d95` |
| `input_booster_lkm.ko` | `be8e3b2c13056da6f447fd3862b453c03feee2a7c336165203d7c37c4722d1ea` |
| `sec_debug_coredump.ko` | `110cf61f8f18577fa1c327e1fa6fd6a0f4a8da98b22fa8480935233eb59afbf4` |
| `wlan.ko` | `75c4344063ce7af1c8234b6bd01569529094de75e77d555ebbb163598c2002e8` |

**Next engineering gate:** verify the custom boot and vendor_boot header/ramdisk
contents, full module load-list and provenance, A16 firmware and module
interfaces, and how to integrate through the UN1CA patch pipeline without
invalidating its native GZH3/PROCA-only audit. Do not overwrite the existing
11-GiB GZH3 workdir or its existing stock-kernel provenance evidence simply
to promote this candidate. Prepare separate custom-kernel integration gates.
The existing `E3099` safety abort, original FYI3 bootloader, existing phone
installation and recovery remain unchanged.

### Next, read-only artifact inspection

The host build above is not a ROM integration pass. Before any custom kernel
patch-module promotion, run:

```bash
cd ~/android/UN1CA
bash scripts/r0s/audit_extremekrnl_a16_candidate.sh
```

This reads existing custom `boot.img`, `vendor_boot.img`, `dtbo.img`,
KernelSU build configuration, five vendor modules, their dependencies, and
the actual vendor_boot ramdisk fragments, while checking the native GZH3
workdir and installer E3099 are still present. It modifies none of these.
The GitHub CI `--self-test` is syntax-only; only the user's host run can
confirm the actual image and module layout. A PASS is not an ABI, Android
SELinux, bootloader-compatibility, full OTA, or board PASS.
