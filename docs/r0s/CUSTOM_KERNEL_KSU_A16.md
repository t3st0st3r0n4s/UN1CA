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

### GZH3 EROFS compatibility gate — introduced after the real custom-kernel audit

The real host ran `scripts/r0s/audit_extremekrnl_a16_candidate.sh`
and returned **CUSTOM KERNEL POSTBUILD INSPECTION PASS**: kernel and
vendor_boot header v4, custom boot OS label 16.0.0/2026-05, five exact
newly built vendor_dlkm modules, 328 `modules.load` entries, and two
LZ4-compressed vendor_boot fragments. This is *not* a vendor-ramdisk
comparison against GZH3.

**Integration is blocked pending a native-to-custom vendor_boot reconciliation.**
The native UN1CA GZH3 ROM workdir has already modified the Samsung
vendor_boot fstab to use EROFS for the five logical partitions. The raw
ExtremeKRNL vendor_boot was independently packaged with its own fstab
and omits the GZH3 boot command line's
`androidboot.selinux=permissive` token. Neither image should be copied
over the other automatically: the early-mount fstab and the normal-boot
SELinux policy must be explicitly qualified.

Read-only comparison, preserving all native and custom images:

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
PATH="$PWD/out/tools/bin:$PATH" \
  python3 scripts/r0s/compare_extremekrnl_gzh3_a16.py
```

The comparator unpacks both vendor_boot images into a temporary directory,
lists the ramdisks, prints the work-vs-candidate fstab differences,
checks the five custom .ko files embedded in vendor_ramdisk01 against
the compiled artifacts, and checks `modules.load` names. A reported
`INTEGRATION HOLD` is an expected, safe outcome if these differ.
It must not be bypassed: use the actual diff to design a reconciled
vendor_boot and matched module/metadata pipeline.

Other remaining qualifications: firmware/DTBO compatibility between
ExtremeKRNL's Samsung S711N EZI2 source and S901B GZH3, custom
kernel/module dependency ABI and module load ordering, the original FYI3
binary-I bootloader, AVB, complete A16 ROM and SELinux runtime, and
rollback and physical BOARD tests. KernelSU manager reuse remains staged
and inactive. `E3099` stays mandatory.

### Actual GZH3-vs-ExtremeKRNL hold — host 2026-10-13

The real `compare_extremekrnl_gzh3_a16.py` run proved both vendor_boot
images have two valid ramdisk fragments. Five custom `.ko` files embedded
in custom `vendor_ramdisk01` are byte-identical to their compiled
artifacts; `modules.load` has 328 entries and **0 missing filenames**.

The candidate **cannot be copied directly** into UN1CA: its
`first_stage_ramdisk/fstab.s5e9925` requests `f2fs` for native
GZH3/UN1CA `erofs` vendor, vendor_dlkm, product and odm. All three fstabs
differ, including `/data` encryption and AVB handling. The comparison
appropriately returned `REQUIRES RECONCILIATION`. This is not a failed
kernel compile or unresolved module inventory.

**Implementation added:** `scripts/r0s/reconcile_extremekrnl_gzh3_a16.py`
builds an *isolated* host-only hybrid candidate, preserving the native
GZH3 workdir `boot` ramdisk and metadata, native vendor ramdisk00
(including the three exact fstabs), native vendor bootconfig and metadata,
while substituting the pinned ExtremeKRNL built kernel/DTB, custom
vendor_ramdisk01, custom dtbo and five matching vendor_dlkm modules.
The builder unpacks the results and asserts the exact component hashes
before writing a separate folder under `out/`. No prior output is
overwritten, no existing ROM workdir is patched, and E3099 is not removed.

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
python3 scripts/r0s/reconcile_extremekrnl_gzh3_a16.py --self-test
PATH="$PWD/out/tools/bin:$PATH" \
  python3 scripts/r0s/reconcile_extremekrnl_gzh3_a16.py
```

The host builder result is **PENDING** until it runs against real
boot metadata. Additional work remains for vendor_dlkm metadata packaging,
ROM patch module activation, AVB/signed target-files, actual runtime KSU,
firmware compatibility, FYI3 bootloader, and device validation. Do not
flash these candidate images.

### Real hybrid candidate PASS; late UN1CA module now wired — 2026-10-13

The user executed the real GZH3/ExtremeKRNL hybrid builder successfully:

| Artifact | SHA256 |
| --- | --- |
| `boot.img` | `55d86a13ae72768023961c8f05ed3eec0f3b4486da3e7a081b848b1e89355ad3` |
| `vendor_boot.img` | `5901c98df36a8c11204a7e0e579f2824e24c133640e15b0b605de076901101c0` |
| `dtbo.img` | `18a0c5572edcbf6a83bb55a407e956f78c34306e76b97fb9747a988b09c507df` |

Five `vendor_dlkm` modules matched their separately compiled pin hashes
and the hybrid repack verified native GZH3 EROFS first-stage fstab and
ramdisk preservation byte-for-byte. This is **HYBRID HOST PASS**, not
boot/device compatibility.

The reproducible UN1CA ROM integration is now
`target/r0s/late_patches/extremekrnl/{module.prop,customize.sh}`.
Upstream `scripts/make_rom.sh` now applies optional device late patches
**after** the generic `unica/patches` and `unica/mods`, thereby preserving
the prior PROCA and filesystem patches before substituting the verified
hybrid. It is not a global ROM module: only the r0s target has this
late module. The canonical source checkout stays in
`out/kernel_tmp-exynos2200` and the candidate stays isolated under
`out/r0s_A16_ExtremeKRNL_KSU_hybrid_candidate`.

The integrity tool
`scripts/r0s/integrate_extremekrnl_a16.py` pins all three image SHA256s,
five vendor module SHA256s, source/KSU commits, module vermagic,
firmware marker, native boot ramdisk, native vendor_ramdisk00/bootconfig
and E3099. `--check` is read-only. `--apply` is guarded to the
target late-patch phase only. After a future completed rebuild, `--verify`
checks the integrated workdir by exact pinned hashes. The stock workdir
and packaged provenance checks remain strict in stock mode, but dispatch
to custom provenance when the custom marker exists.

**First, perform a read-only host preflight (does not rebuild workdir):**

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
PATH="$PWD/out/tools/bin:$PATH" \
python3 scripts/r0s/integrate_extremekrnl_a16.py --check
```

Only if that passes may the operator choose to rebuild the UN1CA workdir
through the normal `make_rom.sh --no-target-files` path, which executes
the late module automatically. This is a real workdir regeneration, not
a single-file in-place toggle; it must NOT be run until disk capacity and
existing output backups are considered. No automatic target-files,
flashable ZIP, firmware, bootloader, TWRP or phone change is caused by
the integration script. The existing E3099 installer lock remains.

**Still not qualified:** kernel DTB/DTBO interoperability with this GZH3
firmware and retained FYI3 bootloader I, normal-boot SELinux,
`vendor_dlkm` metadata compatibility and actual module loading,
AVB/bootloader trust, KSU manager runtime, recovery/rollback, physical BOARD.

### Real integrated UN1CA A16 workdir HOST PASS — 13 October 2026

User completed `source ./buildenv.sh r0s` followed by
`bash scripts/make_rom.sh --no-target-files` and subsequent
`integrate_extremekrnl_a16.py --verify`,
`inspect_built_workdir.sh` and
`inspect_postbuild_boot_ramdisks.sh` audits, all **PASS**.
The build completed without producing target-files, OTA or flashing.

- Android API 36, device `r0s`, native embedded `system_ext`;
  UN1CA version `3.2.1-aa6c8661`.
- The late module executed after upstream filesystem/PROCA patches,
  with `A16 EXTREMEKRNL R0S WORKDIR LATE-INTEGRATION PASS`.
- Integrated `boot.img`: 29,704,192 bytes,
  SHA256 `55d86a13ae72768023961c8f05ed3eec0f3b4486da3e7a081b848b1e89355ad3`.
- Integrated `vendor_boot.img`: 24,961,024 bytes,
  SHA256 `5901c98df36a8c11204a7e0e579f2824e24c133640e15b0b605de076901101c0`.
- Integrated `dtbo.img`: 2,206,476 bytes,
  SHA256 `18a0c5572edcbf6a83bb55a407e956f78c34306e76b97fb9747a988b09c507df`.
- All five `vendor_dlkm` custom module hashes exactly matched the
  pinned hybrid. The four key APK/JAR CRCs passed.
- Native GZH3 `vendor_boot` commandline remains
  `androidboot.selinux=permissive bootconfig loop.max_part=7`.
  This **is not** an enforcing-SELinux runtime claim.
- E3099 remained active and no device or bootloader was altered.

**Packaging is NOT yet run.** Host reported `df -h` available **25G**
and workdir size around **11G**. The guarded target-files preflight
`scripts/r0s/preflight_target_files.py` requires a conservative
free-space budget of full-sized `super_empty` + 2× actual partition
worktree bytes + 7 GiB reserve (approximately **39 GiB** given rounded
workdir totals). The exact requirement must be printed by the script;
do not override its storage check or delete firmware, rollback artifacts,
kernel source, or workdir automatically. Run a read-only capacity
inventory before scheduling packaging:

```bash
cd ~/android/UN1CA
python3 scripts/r0s/preflight_target_files.py
du -h --max-depth=2 out | sort -h | tail -35
df -h .
```

Next technical check before claiming target-files/BOARD success:
the exact module boot dependency and `vendor_dlkm` metadata layout,
signed boot/AVB test-key package after storage is available, FYI3
bootloader compatibility, normal-boot SELinux/KSU manager and recovery
rollback. E3099 must remain in place.

### KernelSU Next v3.4.1 manager autoinstall (TachyonOS parity)

The real Android 16 workdir rebuild had initially integrated only the
**built-in** KernelSU Next v3.4.1 kernel. The user reiterated the previously
agreed TachyonOS behaviour: **automatic manager preload/install** as well,
not a manual APK installation.

The A16 `r0s` late module now calls
`scripts/r0s/install_ksunext_manager_a16.py --apply` after it installs
the pinned ExtremeKRNL hybrid, so **future standard ROM workdir builds**
embed the identical v3.4.1 **spoofed 33333** official release manager:
- Download/pin:
  `https://github.com/KernelSU-Next/KernelSU-Next/releases/download/v3.4.1/KernelSU_Next_v3.4.1-spoofed_33333-release.apk`
- SHA256:
  `f41778ee812512ae96bf53e7265114de5e0414bc5cb92397f49e1052d77da118`,
  independently confirmed from the GitHub v3.4.1 release asset's digest.
- Workdir `system/system/etc/unica/ksunext/manager_payload.bin`
  (runtime `/system/etc/unica/ksunext/manager_payload.bin`).
- `/system/etc/unica/ksunext/install_manager.sh` uses the retained
  TachyonOS one-shot `pm install -r` success-marker logic, with
  `/data/local/tmp/.unica_ksunext_manager_33333_installed` as its new
  per-ROM marker. After a deliberate uninstall, no boot-time resurrection.
- `/system/etc/init/unica_ksunext_manager.rc` declares
  `on property:sys.boot_completed=1` and
  `exec_background u:r:ksu:s0 root root -- /system/bin/sh /system/etc/unica/ksunext/install_manager.sh`.
- `configs/fs_config-system` and `configs/file_context-system` include
  explicit files and directories (UID/GID 0, `0644` files,
  `0755` directories, `u:object_r:system_file:s0`).
- APK is pinned by digest, downloaded into a retained host-only manager cache
  and copied into workdir; no `.apk` binary tracked by GitHub.

**Catch up an already-built UN1CA workdir without repeating the 24-minute
ROM rebuild** (and *before* packaging), ONLY after any in-progress
target-files packaging has finished or been safely stopped:

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
python3 scripts/r0s/install_ksunext_manager_a16.py --check
python3 scripts/r0s/install_ksunext_manager_a16.py --apply-existing
python3 scripts/r0s/install_ksunext_manager_a16.py --verify
bash scripts/r0s/build_target_files_guarded.sh --check
```

`--apply-existing` requires the completed workdir, the exact current
custom-kernel provenance PASS, E3099 and an empty builder temporary
directory. It preserves the prior `.completed` marker (so a later normal
ROM build correctly sees source changes), modifies **only** the system
manager payload/script/init and system metadata, does not regenerate
all APK/JARs, compile kernel, touch /data/device or package OTA.
The target-files guarded builder now *requires* manager `--verify`
before producing a new custom kernel archive.

If an archive was packaged **before** this manager integration, its bytes
**do not include** the manager, and its old package hash / target-files
verification cannot establish auto-install. Do not present it as A16
manager-integrated; the archive must be rebuilt after workdir promotion.

The GitHub one-shot mechanism mirrors the proven Android 15 delivery,
but its `u:r:ksu:s0` execution, actual package-manager success and
root-manager runtime remain **A16 BOARD DEFERRED**. E3099 active.

### Kernel-only recovery-update workflow (no full ROM rebuild)

**The upstream kernel `build.sh -m r0s -k` already emits an ExtremeKRNL
ZIP under `out/kernel_tmp-exynos2200/build/out/r0s/`**, but it is
**not compatible with the GZH3/UN1CA hybrid**. Its updater-script
writes the upstream raw `boot.img`, `vendor_boot.img`, and
`dtbo.img` directly to by-name devices; its `vendor_boot.img`
does not preserve native GZH3 EROFS/AVB early mount, and the zip does
not update the five rebuilt `vendor_dlkm` modules. **Do not flash it.**

To retain TachyonOS's fast kernel-only update route, the
`scripts/r0s/package_extremekrnl_update_a16.py` tool prepares a
**GZH3-compatible host-only recovery payload** from the existing,
already signed and audited UN1CA target-files archive. It carries
`images/boot.img`, `images/vendor_boot.img`, `images/dtbo.img`,
and `images/vendor_dlkm.img`; this keeps matching EROFS `vendor_dlkm`
content beside the boot chain. Unlike the upstream ZIP, these boot
images have been reconciled with the native workdir before packaging.

The output
`out/r0s_A16_ExtremeKRNL_KSUNext_v3.4.1_GZH3_RECOVERY_HOLD.zip`
contains an unconditional E3099-aborting `updater-script`,
**no** `update-binary` or partition writer, a manifest with pinned
source/KernelSU commits, SHA256 for all four payloads and a prominent
`NOT_FLASHABLE.txt`. It is **not** yet TWRP-flashable.

This separate payload is generated **without running make_rom.sh,
recompiling the kernel, or building target-files again**, provided
existing target-files (with module-matching, signed images) is present.
To validate and create the candidate using the actual 2026-10-13
target-files artifact:

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
python3 scripts/r0s/package_extremekrnl_update_a16.py self-test
python3 scripts/r0s/package_extremekrnl_update_a16.py check \
  4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a
python3 scripts/r0s/package_extremekrnl_update_a16.py build \
  4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a
python3 scripts/r0s/package_extremekrnl_update_a16.py verify
```

`build` reruns the deep target-files and packaged-module audits before
copying payload bytes. It refuses to overwrite a previous output, and
there is no implicit attempt to flash or sideload the candidate. For
a future build supply that build's actual SHA256; never use an older
digest or ROM module set.

**Before a real recovery ZIP can be enabled:** finish
GZH3/FYI3 bootloader and AVB test-key trust checks, KMI/`modules.load`
and runtime module loading, recovery ABI and Android 16 TWRP support,
mounting/updating a *dynamic* EROFS `vendor_dlkm` partition, partition
backups and rollback, and physical BOARD boot. Then add a deliberately
reviewed recovery updater to a *new* flash-qualified output format.
Do not bypass E3099 or reuse upstream `package_extract_file` writes.

For later KernelSU Next **code** upgrades the kernel itself must be
rebuilt, and if its ABI changes the matching `vendor_dlkm` modules
and `vendor_boot` load list must be rebuilt and validated. A full
UN1CA userspace ROM rebuild is not inherently needed. Updating only
the standalone Manager APK may not need any kernel flashing at all.

### Kernel-only TWRP updater — executable architecture, 2026-10-13

**User-established A15 baseline:** On 2026-10-10, the working TachyonOS
S901B TWRP successfully flashed
`ExtremeKRNL-Nexus-2200-v1_r0s_UNOFFICIAL_KSU_10-10-2026_11-27-29.zip`
to upgrade built-in KernelSU Next to v3.4.1 **without a ROM rebuild**.
This is accepted. Do NOT repeat A15 TWRP/TAR identity/source/ABI checks
as a requirement for this workflow; the missing optional local
`TachyonOS/TWRP` TAR is not an A16 build blocker.

The older `package_extremekrnl_update_a16.py` output
`*_RECOVERY_HOLD.zip` (no update-binary, inert archive) was replaced,
not supplemented with a second updater architecture. It now creates
`out/r0s_A16_ExtremeKRNL_KSUNext_v3.4.1_TWRP_E3099_LOCKED.zip`
from the existing real
`out/r0s_A16_GZH3_HOST_ONLY-target_files.zip`. Its contents are:
- The **same actual** `prebuilts/bootable/deprecated-ota/updater` binary
  from the UN1CA updater-launch probe already accepted by installed TWRP;
- `vendor_dlkm.new.dat.br`, `vendor_dlkm.transfer.list`,
  `vendor_dlkm.patch.dat` generated from target-files' **AVB-signed
  GZH3 EROFS vendor_dlkm.img** by the upstream `img2sdat` + Brotli
  tooling; the five pinned ExtremeKRNL modules travel with this image;
- Reconciled and AVB-signed `boot.img`, `vendor_boot.img`, `dtbo.img`
  copied from validated target-files — NOT the raw upstream kernel ZIP;
- An edify updater: **unconditional E3099 first**, then
  `block_image_update(map_partition("vendor_dlkm"), ...)`, followed
  by the three by-name boot image writes;
- A digest manifest and prominent do-not-flash notice.

**Critically, NO `remove_all_groups` and NO
`update_dynamic_partitions`**. A kernel-only updater targets an
*existing installed A16 UN1CA* and must not delete or resize system,
product, vendor or odm. It assumes installed `vendor_dlkm` exists with
sufficient space. It does not touch TWRP, recovery, firmware BL/CP,
vbmeta or userdata. It does not rebuild userspace or the kernel.

Existing target-files SHA256 from the actual user build:
`4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a`.

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
python3 scripts/r0s/package_extremekrnl_update_a16.py self-test
python3 scripts/r0s/package_extremekrnl_update_a16.py build \
  4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a
python3 scripts/r0s/package_extremekrnl_update_a16.py verify
```

The `build` mode performs A16 target-files AVB and kernel-module
provenance audits, then outputs one small kernel-only updater ZIP.
**The output is intentionally E3099-locked**; do not attempt to flash.
A16 first-install, normal boot, AVB trust on retained FYI3 BL,
vendor_dlkm update-capability and kernel rollback/BOARD remain to be
qualified before authorising a future writable updater. The successful
A15 update is not automatically proof of A16 kernel compatibility.

After A16 is operational, future KSU versions require compiling the
changed kernel (and ABI-coupled modules as needed) and packaging these
components only. A **full ROM userspace rebuild is unnecessary**.
