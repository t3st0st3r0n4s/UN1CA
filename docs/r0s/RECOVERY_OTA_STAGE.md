# UN1CA S901B Android 16 — provisional OTA block mapping

**Status: STOCK RECOVERY FSTAB EXTRACTED / OTA SEMANTICS UNVERIFIED / INSTALLER LOCKED.**

## Why this exists

UN1CA's `scripts/utils/install_utils.sh` requires a target or platform
`recovery.fstab` file, even when it resolves a logical partition to
`map_partition("system")`. Its full updater script also needs raw block
locations for `boot.img`, `vendor_boot.img` and `dtbo.img`.

The Samsung S901B GZH3 firmware **has been downloaded and extracted**.
Its native `vendor/etc/fstab.s5e9925` and `os_partitions_metadata.txt`
confirm logical partition names and raw boot-chain locators. Our
`target/r0s/installer/recovery.fstab` remains a **provisional updater-script
locator map**, NOT a verified stock recovery mount configuration: the native
`recovery.img` was extracted but its ramdisk and updater have not been audited.

Reference: https://github.com/LineageOS/android_device_samsung_s5e9925-common/blob/lineage-23.2/configs/init/fstab.s5e9925

## What is mapped

- Native GZH3 logical partitions: `system`, `odm`, `product`, `vendor`,
  `vendor_dlkm`; **no separately extracted `system_ext` image**. The latter
  may be embedded in system. UN1CA's generic resolver can syntactically
  return `map_partition("system_ext")` even when no such stock partition exists.
- Raw locators `/dev/block/by-name/boot`, `vendor_boot`, `dtbo`,
  `recovery` are verified against the extracted native GZH3 **vendor** fstab,
  not the recovery ramdisk.
- Unprovided `/init_boot` and `/dt`: intentionally fail resolution. No
  device-specific partition may be invented to make an OTA package build.

## Safety and validation

- `target/r0s/installer/assertions.edify` retains unconditional `E3099`
  `abort(...)`. The helper's `PRINT_ASSERTIONS` appears before any updater
  partition operation in the current upstream `build_full_ota_zip.sh`.
- `scripts/ci/check_r0s_ota_map.sh` extracts and executes the actual upstream
  `GET_DEVICE_FROM_MOUNTPOINT` function in isolation with stubbed helpers.
  It exercises logical and nonlogical mappings, verifies unsupported names
  fail, rejects an extra device-specific `install-end.edify`, and checks the
  installation lock is preserved.
- Sandbox fixture checks have passed for valid mapping, wrong vendor_boot
  mapping rejection and removal of the `E3099` abort.
- Firmware downloaded/extracted, boot-image metadata inspected and native
  vendor fstab verified. Still no kernel build, full-OTA generation, recovery
  deployment or real-board test.

## Promotion blockers

1. Confirm native Samsung S901B A16 `fstab.s5e9925`, recovery and boot
   partition references from the matched release.
2. Qualify super group names/sizes against extracted `lpdump`.
3. Establish exact bootloader and rollback assertions for supported firmware
   transitions; ensure /data migration behavior is explicit.
4. Verify recovery updater supports the target's logical partition operations,
   and inspect the generated full OTA for all boot and super image writes.
5. Rebuild full ROM and test on hardware before removing `E3099`.

**This staging does not grant ROM HOST PASS, OTA PASS or BOARD PASS.**

## Verified GZH3 host evidence (2026-10-12)

- `super_partition_size=11744051200`; `group_basic` maximum `11739856896`.
- Partition list `system odm product vendor vendor_dlkm`.
- Stock `vendor/etc/fstab.s5e9925` SHA256 `7ecce93a3447b047c66d7db22446d3b89389352ac2af6e46dcb5560b73acbfa9`.
- `recovery.img`: 100663296 bytes, header v2, SHA256 `b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688`. Ramdisk remains uninspected.
- The staging file is **not** a substitute for Samsung's native recovery image or installer compatibility testing; `E3099` abort remains mandatory.

## Recovery ramdisk discovered on the host (2026-10-12)

Stock recovery header v2 and LZ4 ramdisk unpacked. Contents include `system/etc/recovery.fstab`, `init.recovery.s5e9925.rc`, `init.recovery.samsung.rc` and `system/bin/recovery`. Recovery-specific command line includes `androidboot.selinux=permissive`; this does not describe normal Android SELinux. `scripts/r0s/inspect_recovery_abi.sh` reads and prints the recovery fstab and selected init contents through `cpio --to-stdout` in a temporary directory, with no privileged mount, firmware writes, image changes or phone operations. Genuine host rerun is pending.

## Native recovery fstab inspection (2026-10-12)

The real GZH3 recovery ramdisk's `system/etc/recovery.fstab` was extracted and SHA256-verified in the host log: `91d60dcf617483a260600d2ea25054a56a7cad806ec6011218b044262fe2b488`. It contains raw `/boot`, `/vendor_boot`, `/dtbo`, `/recovery` paths and all five physical super logical names. It additionally lists **`system_ext`**, while the actual Samsung `lpdump` partition list does not contain it. Do not create an extra system_ext partition from a generic recovery fstab entry.

The recovery fstab differs from vendor fstab in AVB policy, supported fs types and recovery-only mounts. These files cannot be interchanged as complete configuration files. The staged UN1CA `recovery.fstab` is used only by UN1CA's partition locator resolver and is **not** a native recovery filesystem policy.

The read-only `scripts/r0s/check_recovery_ota_map.sh` now compares native recovery, native vendor, extracted super metadata and staged updater block locators, refusing unsupported logical names and missing raw locators while allowing extra stock recovery-only entries. Its synthetic test is wired into Actions; genuine host rerun remains pending. This is **mapping consistency only**, not proof that Samsung recovery can run UN1CA's deprecated-OTA update-binary or that normal boot works.

## Dynamic partition operation-list rehearsal (2026-10-12)

The upstream `GENERATE_OP_LIST()` in `scripts/internal/build_full_ota_zip.sh` creates entries only for image files actually present. Its generic `PARTITIONS_LIST` supports `system_ext`, but GZH3 has no separate stock image for it. `scripts/ci/test_r0s_ota_op_list.sh` extracts and executes **the actual function**, with five tiny mock images and the real group size, and asserts exactly `system odm product vendor vendor_dlkm` in the operation list. Negative fixtures reject an invented `system_ext` image and oversized group data. This proves generator behavior under controlled fixtures, **not** the actual image build, updater semantics or runtime recovery. Before any actual OTA, inspect generated image list/operations from the ROM artifact and retain `E3099`.

## Workdir assembly complete, OTA images not yet created (2026-10-12)

Synthetic OTA operation-list tests passed. Real GZH3 UN1CA workdir assembled successfully, no separate system_ext partition, but there is no target-files ZIP, EROFS image set or actual dynamic operation list yet. Remaining free host disk ~41G. Capacity and modified boot-image postbuild checks precede further packaging. E3099 remains active.

## Target-files storage and reuse constraint (2026-10-12)

Real workdir audit PASS, with 41 GiB free. `make_rom.sh` computes `GET_WORK_DIR_HASH()` across `unica`, `platform/exynos2200` and `target/r0s` **including status Markdown**. Documentation edits in `target/r0s` therefore risk an unnecessary rebuild; a direct invocation of upstream `scripts/internal/create_target_files_zip.sh` on the already-built workdir is the safer later route, once storage is gated. It builds temporary EROFS partition images, an `unsparse_super_empty.img` with 11,744,051,200-byte super geometry, and a compressed target-files zip. Disk peak has not been measured; keep the 12 GB Odin and 13 GB extracted stock firmware intact until a controlled retention decision. No target-files or OTA ZIP yet.

## Read-only target-files archive structural gate (2026-10-12)

Added `scripts/r0s/check_target_files_zip.py` to inspect a future real `r0s_*target_files.zip` using only the ZIP central directory, bounded `build_info.txt`, and the first 28 bytes of image members. It enforces the **actual native five-image layout** (`system odm product vendor vendor_dlkm`), rejects a separate `system_ext`, verifies native `group_basic` geometry, Android 16/S901B identity, raw boot/vendor_boot/dtbo image reference caps, and re-checks the `E3099` source assertion. Crucially it reads Android sparse image headers to compare **expanded** logical sizes against the 11,739,856,896-byte group cap; an apparent small ZIP member is *not* proof of a small logical image. It does **not** extract or build images.

Synthetic fixtures exercise correct layout and rejection of added/missing partitions, sparse group overflow, SDK/device mismatches, duplicate ZIP member names, malicious paths, and missing installer lock. CI validates that checker; this does not establish the validity of future real target-files artifacts, image AVB signatures, stock kernel ABI, or recovery/BOARD support.

When an actual target-files ZIP exists, run:

`python3 scripts/r0s/check_target_files_zip.py /path/to/r0s_VERSION-target_files.zip`

**Do not generate or flash OTA merely because the ZIP structure passes**. Actual image construction, storage peak, modified kernel/ramdisk review, recovery updater semantics and physical board validation remain separate gates.

## Guarded direct target-files packaging (2026-10-13)

Real GZH3 PROCA exact-delta audit passed: only the expected 4-byte ARM64 header and one same-length PROCA string substitution occur in the rebuilt decompressed kernel. The vendor_boot cmdline matches stock; vendor_ramdisk01 is byte-identical; matched vendor_ramdisk00 fstab differences are the native five-partition EROFS conversion. Kernel ABI and BOARD remain deferred.

Use `scripts/r0s/build_target_files_guarded.sh` rather than make_rom.sh to prevent the existing 11GB completed workdir from being rebuilt merely because the source/docs hash changed. `--check` (default) is read-only: it confirms pinned GZH3 extraction, API 36 and r0s workdir identity, expected five physical super partitions, metadata, E3099 and an unobstructed builder temporary directory. The capacity planning budget allows an unsparse 11.74GB super-empty file, twice the workdir partition-tree disk usage for image and ZIP staging, plus 7GiB free reserve. **This is an estimate, not a measured or guaranteed peak**.

Host-only check (no packaging): `bash scripts/r0s/build_target_files_guarded.sh --check`

If the preflight passes and available space is sufficient, start direct image packaging only with `bash scripts/r0s/build_target_files_guarded.sh --build`. This sources UN1CA buildenv for the existing target, reruns the disk and workdir/PROCA audits, calls upstream scripts/internal/create_target_files_zip.sh directly into a temporary output, checks the ZIP structure with `check_target_files_zip.py`, and only then moves to a non-overwriting HOST_ONLY target-files filename. It does not run make_rom.sh, build_full_ota_zip.sh or flash anything.

Neither script has run against the real host as of this commit. Do not treat target-files structure or kernel patch scope as boot compatibility, AVB signature validation, recovery OTA compatibility or BOARD PASS. E3099 remains mandatory.

## Native GZH3 target-files actually built on host (2026-10-13)

The user ran `bash scripts/r0s/build_target_files_guarded.sh --build` against
the existing completed S901B Android 16 workdir. Both native GZH3 capacity
preflights, the exact-kernel/ramdisk workdir audit, image construction, and
the target-files structure gate passed without calling `make_rom.sh`.
All five native EROFS partitions were created (system, odm, product, vendor,
vendor_dlkm), and `boot.img`, `dtbo.img`, `vendor_boot.img` were added.
The native group was `group_basic`, cap `11739856896` bytes; total
expanded logical partition sizes were `7579938816` bytes. The produced
`unsparse_super_empty.img` was only 4644 bytes of metadata: the earlier
full-device planning estimate was conservative, not a measured peak.

Host artifact: `out/r0s_A16_GZH3_HOST_ONLY-target_files.zip`.
Observed SHA-256:
`6c20d013b7f3087e08fe453d5eb10fcf9411107898c98705b6f8b30347a9b8fd`.
The packaging script reported **TARGET-FILES STRUCTURE PRECHECK PASS** and
**HOST-ONLY TARGET-FILES CREATED**.

A separate `scripts/r0s/audit_target_files_host.sh` now provides the
next **read-only** verification stage with the expected artifact SHA as
an argument. It checks the archive structure and installer lock, streams
all ZIP members for CRC, verifies raw boot-chain AVB signatures against
the *development test key*, and reads the native empty-super metadata
using `lpdump`. This deep check still requires execution on the actual
host and must not be reported as PASS merely because CI syntax succeeds.

**No OTA was generated or tested.** Native recovery updater semantics,
stock bootloader AVB trust and rollback, kernel/module ABI, normal-boot
SELinux, and physical S901B boot remain UNVERIFIED. The unconditional
`E3099` installer abort remains active. Do not flash this target-files ZIP.

## Deep host audit PASS and kernel/module provenance next (2026-10-13)

The user verified the pinned HOST_ONLY target-files SHA-256, full ZIP CRC,
all three boot-chain AVB signatures against the **development** test key,
and the five readonly native logical partitions in empty-super lpdump.
AVB algorithm was SHA256_RSA4096 and rollback indexes were 0; neither
fact establishes Samsung stock bootloader trust or rollback acceptance.
Native group_basic maximum is 11739856896 bytes. No independent system_ext
partition exists. Deep host target-files validation is **PASS**.

Next read-only gate is scripts/r0s/audit_packaged_kernel_modules.sh. It
extracts only the packaged boot kernel and small vendor_dlkm EROFS filesystem;
it compares the packaged embedded kernel against the exact GZH3 PROCA delta,
and checks all five packaged vendor modules byte-for-byte against stock and
workdir, including native modinfo vermagic. Host execution is pending.
Even PASS is provenance, **not full kernel-module ABI** (exported CRC/KMI
or physical loadability). E3099 remains active; no OTA or flashing.
