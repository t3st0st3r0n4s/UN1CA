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

## Real packaged kernel and GZH3 module provenance PASS (2026-10-13)

Host invocation of `audit_packaged_kernel_modules.sh` succeeded against the pinned
SHA-256 `6c20d013b7f3087e08fe453d5eb10fcf9411107898c98705b6f8b30347a9b8fd`.
Packaged embedded-kernel SHA-256 `dd509289798cfa756c649e77179d758101cddae6273a649be7835ae34080ca4a`
exactly matched the completed workdir. Against native GZH3 kernel SHA-256
`1a3481f961f2acb93b2ce556c1179d3842359dd00782d9f566b305687a0dee39`,
the only accepted decompressed binary differences were ARM64 header offset 40
and the same-length PROCA string replacement at offset 26891441.

The archived vendor_dlkm sparse EROFS filesystem was extracted without mounting.
All five packaged modules—fingerprint, fingerprint_sysfs, input_booster_lkm,
sec_debug_coredump, wlan—were byte-identical to both extracted native stock
and completed workdir, and their modinfo vermagic matched pinned stock GZH3.
**PACKAGED KERNEL / MODULE PROVENANCE PRECHECK PASS.** No unexpected kernel
or vendor module ABI changes were found relative to native GZH3, but this
does not execute the modules or prove runtime KMI/CRC resolution.

## Native stock recovery / UN1CA updater static compatibility inventory

Next gated step: `scripts/r0s/audit_stock_recovery_updater.sh` (read-only).
It checks the exact stock GZH3 recovery image hash, inventories its LZ4
ramdisk and bundled native recovery executable, inspects the upstream
deprecated-OTA updater ELF architecture and dependencies, lists candidate
stock recovery trust-anchor paths, and prints the development OTA certificate
fingerprint. This provides **evidence**, not confirmation that Samsung recovery
accepts a test-signed UN1CA OTA or can invoke this updater. Static inventory
needs to run on the actual host; CI performs syntax checks only. No full OTA
is authorised, and the E3099 abort must remain active.

## GZH3 stock recovery / UN1CA updater static inventory PASS (2026-10-13)

The user ran `audit_stock_recovery_updater.sh` against pinned GZH3.
Native recovery ELF was dynamically linked AArch64 with `/system/bin/linker64`
(ELF sha256 `95422429a08199b5520e73dafd16e87b69d9f52e9f31c1a0ffbbaa8cdf02a5b2`).
UN1CA's deprecated-OTA updater was statically linked AArch64 for Android 36
(sha256 `28378c9dcae8a0e6035e5f90e66c2a128eab3cce2982e43aa33424542507664a`).
Recovery strings include the `META-INF/com/google/android/update-binary` path,
`/tmp/update-binary`, and `Signature verification failed`; the UN1CA updater
exposes `block_image_update` and `update_dynamic_partitions`.
These are **static compatibility indications**, not proof of successful execution.

GZH3 stock recovery ramdisk contains `publiccert.pem` and
`system/etc/security/otacerts.zip`. Development OTA signing cert
`security/aosp_testkey.x509.pem` reported SHA-256 fingerprint
`A4:0D:A8:0A:59:D1:70:CA:A9:50:CF:15:C1:8C:45:4D:47:A3:9B:26:98:9D:8B:64:0E:CD:74:5B:A7:1B:F5:DC`.

New read-only `scripts/r0s/audit_recovery_ota_trust.sh` extracts only those
stock recovery certificate files from the hash-pinned GZH3 ramdisk and uses
`scripts/r0s/check_recovery_ota_certificates.py` to compare exact X.509
certificate hashes and canonical public-key hashes against the project's
development signer. Synthetic positive/negative fixtures are covered by CI.
A missing key is a likely blocker for testkey-signed native-recovery OTA,
**not proof that no other recovery verification path exists**. Real-host
certificate comparison is pending; no flashable OTA has been generated.
Installer abort E3099 remains active.

## Real GZH3 stock recovery OTA signer comparison (2026-10-13)

The user reran `python3 scripts/ci/test_r0s_recovery_ota_certificates.py`,
which passed all 8 synthetic cases. Then the genuine extracted GZH3 recovery
trust files were compared with the repository's development OTA signer via
`bash scripts/r0s/audit_recovery_ota_trust.sh`. This **read-only evidence
collection passed**; it is **not** a stock recovery OTA compatibility PASS.

- UN1CA `security/aosp_testkey.x509.pem`: certificate DER SHA-256
  `a40da80a59d170caa950cf15c18c454d47a39b26989d8b640ecd745ba71bf5dc`;
  public-key SPKI SHA-256
  `ef57b690165cb561b5026922c00d2d6574e8b184fa7d161e076f06e06e6d35db`.
- GZH3 recovery `system/etc/security/otacerts.zip`:
  `asks_update.x509.pem` DER SHA-256
  `b731578c253c65e350653e7e1dc5a26f417289fcff17bc456d466e80617478f2`;
  `asks_update_256.x509.pem` DER SHA-256
  `958fd77e6cc19af94dfaab7c9c8046fe58d92a63c89a212b01e2fa45a1e81b7b`.
  Both stock certificates use SPKI SHA-256
  `fb41b567dd246f03f55a25c5772ebb731322422421eb64230a1f731130085357`.
- GZH3 recovery root `publiccert.pem`: DER SHA-256
  `14cd0fbd3a3479e66a40e974a6b9f19f8e48f05254857cb6619c845aa1b4b509`;
  SPKI SHA-256
  `292afe4ffe8d8a96c1c961831903f4a0d8e831cbed39d53235a5f063e4cc38e2`.
- Exact cert and public-key comparisons with both stock trust stores were
  **false**. No UN1CA development signer public key was found among the
  parsed native GZH3 recovery certificates.

**Disposition:** Native GZH3 stock recovery does **not** have demonstrated
trust for an OTA signed with UN1CA's development testkey. Treat that route
as **BLOCKED / NOT QUALIFIED** until an independently verified acceptance
mechanism exists. This does not invalidate host target-files or stock-kernel
provenance, nor prove anything about other custom recoveries. Do not use
Samsung's production signing identity, replace the stock trust database,
disable signature verification on stock recovery, or flash based on strings
alone.

**Next gate:** inspect an exact S901B/r0s recovery candidate against
GZH3 boot header, kernel, ramdisk, fstab, installer/updater capabilities,
and expected partition geometry. Prior Android 15 TWRP/Lineage recoveries
are only candidate sources; they must not be presumed compatible with
GZH3 Android 16. Before any real OTA or recovery write, further qualify
bootloader/GPT/rollback constraints, kernel-module ABI/loadability, normal
SELinux behavior, and a controlled on-device recovery validation plan.
Keep the completed HOST_ONLY target-files ZIP and stock extracted firmware
unchanged. Installer `E3099` remains active.

## Local S901B recovery candidates located (2026-10-13)

The user's read-only inventory found the pinned GZH3 stock recovery image
(`out/fw/SM-S901B_EUX/kernel/recovery.img`, 100663296 bytes),
a GZH3-derived workdir recovery
(`out/target/r0s/work_dir/kernel/recovery.img`, 74764304 bytes),
and a prior TWRP archive `S901B_twrp_logo_vbmeta.tar` (70112768 bytes),
present in both `~/android/S22-ROM` and `~/Downloads`.
Unrelated Orange Pi RK recovery artifacts were excluded.

Source review of `scripts/internal/create_work_dir.sh` demonstrates that
the workdir kernel directory is copied from the selected target stock firmware;
`scripts/unsign_bin.sh` then strips AVB/Samsung signing as applicable.
This workdir recovery is stock-derived, **not an Android 16 custom recovery**.
Its kernel/ramdisk equivalence remains subject to a byte-for-byte host audit.
`scripts/internal/create_target_files_zip.sh` does **not** include
`recovery.img`; it includes boot, dtbo and vendor_boot.

New `scripts/r0s/audit_recovery_candidates.sh` is a read-only comparison:
it lists TAR entries, streams exactly one recovery.img member to a temp
directory, inspects stock/workdir/TWRP Android boot headers and embedded
kernel/ramdisk hashes, enforces stock/workdir payload equivalence, compares
candidate TWRP kernel against native GZH3 and inventories recovery fstabs.
Synthetic CI runs syntax only; **real host candidate audit pending**.
No candidate is authorised for GZH3 flashing, and `E3099` remains active.

## Actual GZH3 stock vs older TWRP static recovery comparison (2026-10-13)

Real host invocation of `audit_recovery_candidates.sh` completed.
TWRP archive `S901B_twrp_logo_vbmeta.tar` SHA-256
`f82b9612d92786971609895facb703906744d9a617e673f1cd148e671735d830`
was byte-identical between the two local copies and contains
`recovery.img`, `up_param.bin` and `vbmeta.img`.
Its `recovery.img` is 67153936 bytes (SHA-256
`3abeda14db0311aca2fd1898c18e7270105ec2c9c57d38bed6ab977e49a28577`).

Stock GZH3 recovery and workdir-derived recovery have **byte-identical**
embedded kernel SHA-256
`1a3481f961f2acb93b2ce556c1179d3842359dd00782d9f566b305687a0dee39`
and LZ4 ramdisk SHA-256
`1d7f5d7c0c2727436663ba5203dbf8a57b987db36fbaf4d0f2e1ef0b1d54c59c`.
Stock recovery patch header says August 2026.
The older TWRP candidate kernel SHA-256 is
`0030075e2e70eeeb878a2eba85f321a90a21dc2efe746e7caa742ecf7ab73147`,
**not equal** to stock GZH3, and its boot header patch field is December
2025. Both use recovery boot header v2, but that alone is insufficient.
TWRP ramdisk is gzip, stock is LZ4; the TWRP binary is present.

Stock `recovery.fstab` includes all native logical names and EROFS system;
the old TWRP `recovery.fstab` has EROFS for system but shows only f2fs
for vendor/product/odm and has vendor_dlkm **commented out**.
Its commented system_ext is consistent with no separate GZH3 super partition.
A native GZH3 EROFS-aware recovery would need to qualify mount rules for
all five actual logical images. This does not establish what other fstabs
or installer paths may exist in the TWRP userspace.

**Decision: old TWRP TAR is NOT GZH3 flash-qualified.** Do not flash
or simply transplant its old kernel. Work toward GZH3-aligned recovery
kernel and properly ported recovery userspace/fstabs with static checks,
followed by controlled physical recovery verification. A historical
public Exynos 2200 TWRP tree exists but is Android 12.1 based and
documents decryption limitations; it is not a native GZH3 release.

New `scripts/r0s/inspect_twrp_gzh3_userspace.py` provides read-only,
sha256-pinned TWRP ramdisk fstab coverage and userspace ELF inventory.
Synthetic fstab fixtures can be run with `--self-test`; actual-host
execution remains pending. Retain E3099 and preserve the validated
target-files ZIP and firmware extraction.

## Older TWRP Android 16 EROFS / binary userspace real-host audit (2026-10-13)

The user ran `inspect_twrp_gzh3_userspace.py --self-test`:
5 synthetic tests PASS. The genuine hash-pinned older TWRP archive reported
`native_five_partition_erofs_coverage=1/5`: system had an EROFS entry,
vendor/product/odm were f2fs-only, and vendor_dlkm had no active fstab entry.
No separate system_ext was active. This is a real fstab coverage **BLOCKED**
result, not a failure of the inspector.

The TWRP userspace executable `system/bin/twrp` has SHA-256
`e98dbb299222e8008aaa275455ca6a94cabf0b19aa544d93ec6afc8499a090b1`.
It is a dynamically linked AArch64 ELF marked for Android 32. No dynamic
partition or EROFS string hints were printed by that specific scan; that
absence is not proof of unsupported functionality. Older TWRP kernel remains
different from native GZH3; do not swap kernels and assume boot support.

New `scripts/r0s/audit_recovery_runtime_abi.py` performs the **next**
read-only userspace study. It compares ELF PT_INTERP/DT_NEEDED dependencies
of the pinned stock GZH3 `system/bin/recovery` against TWRP `system/bin/twrp`
and inventories which direct dependencies occur in each recovery ramdisk.
It streams a single pinned TAR member and parses both recovery ramdisks in
memory; no partitions or persistent images are created or mounted.
CI runs synthetic cpio parser/negative fixtures only. Host execution is
still pending. Absence of a library in a ramdisk does not establish runtime
absence from all possible mounted filesystems.

Current disposition: **old TWRP GZH3 recovery/userspace NOT QUALIFIED**.
Review direct dependencies, linker, fstab, first-stage init/SELinux and
GZH3-aligned recovery source before building any candidate. Preserve
stock GZH3 extraction, completed target-files ZIP and E3099 installer lock.

## Correct install-method distinction: UN1CA upstream supports custom recovery ZIP (2026-10-13)

Authoritative upstream installation guide:
https://github.com/salvogiangri/UN1CA/discussions/130
states that a **custom recovery**, e.g. TWRP or OrangeFox, is UN1CA's
primary/only supported **initial install** method. It offers either
recovery UI ZIP install or recovery's ADB sideload. The upstream updater
guide https://github.com/salvogiangri/UN1CA/discussions/185 confirms
custom-recovery installation for manual updates and provides an
on-device UN1CA Updates app for supported upgrades. The current build
code `scripts/build_flashable_zip.sh` and
`scripts/internal/build_full_ota_zip.sh` assembles a **legacy recovery
ZIP** with `META-INF/com/google/android/update-binary`, an edify
`updater-script`, dynamic partition operation list, data payloads and
boot-chain images. It does not install or bundle a TWRP image.

**Correction of interpretation:** A TWRP recovery built for an earlier
firmware/Android version *may still be able to flash* a newer ROM when
booted on the presently installed device. A custom recovery's ability
to **mount EROFS filesystems for browsing/backups** is distinct from
the edify update-binary's ability to **map and write logical partitions
in block mode**. Thus the real TWRP `recovery.fstab` EROFS coverage
of 1/5 is an important recovery filesystem limitation but **does not
alone prove that UN1CA's legacy block OTA cannot be installed with this
TWRP**. Nor does kernel image mismatch against GZH3 necessarily block
a recovery which boots and runs with the existing A15 boot stack.

The existing S901B TWRP candidate is **not yet installation-qualified**.
Before any OTA write, validate its actual functioning recovery session,
legacy update-binary protocol support, dynamic partition mapping and
`update_dynamic_partitions` / `block_image_update` behavior with
GZH3 geometry, source/target bootloader and AVB compatibility,
partition names and fail-safe recovery path. Inspect any format-data,
fstab and SELinux implications separately. Merely finding relevant
symbols/strings is not a runtime check. There is no need to assume that
a new native GZH3 TWRP build is mandatory solely to install the ROM.

The stock GZH3 recovery does not contain UN1CA's development OTA
signing key; this **stock recovery** trust mismatch must not be
conflated with custom recovery behavior. Do not remove `E3099` until
device/recovery gates are actually passed, and do not attempt to
flash the existing HOST_ONLY target-files ZIP.
