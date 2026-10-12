# UN1CA `sixteen-r0s` status

**STATE:** HOST_CONFIG_PASS / FIRMWARE_METADATA_PASS / BOOT_METADATA_PENDING_RERUN / ROM_UNBUILT / BOARD_DEFERRED / INSTALLER_LOCKED.

## Source baseline

- Fork basis: `salvogiangri/UN1CA` `sixteen`, commit `ce12c6e077fc1865e574873f316c450cdf587bd2` (2026-10-11).
- Device: Samsung Galaxy S22 5G Exynos `SM-S901B` / `r0s` / `exynos2200`.
- Android: 16 / SDK 36 / One UI 8.
- Source and target: stock/native `SM-S901B/EUX` as defined by upstream `unica/configs/essi.sh`.
- Device feature map intentionally mirrors the same native source; older One UI 7 feature patches are not imported.
- UN1CA owns the build system, OTA framework, CSC, Paradigm and generic ROM modules.
- The old TachyonOS `r0s-fyi3` remains untouched and is not this branch's parent.

## Source-level review (2026-10-11)

- CI script `scripts/ci/check_r0s_config.sh` verifies the current UN1CA schema and native source/target parity; GitHub Actions outcome is **not yet confirmed**.
- UN1CA `create_work_dir.sh` already takes native vendor/kernel blobs from target firmware.
- Camera and VINTF generic patches use target stock metadata when source/target SDK 36 match.
- **OTA BLOCKER:** A provisional `target/r0s/installer/recovery.fstab` now allows *source-level* block-locator testing, but is derived from modern LineageOS rather than verified Samsung A16 recovery. The `E3099` flash abort remains mandatory.
- Details: `docs/r0s/SOURCE_INVENTORY.md`.

## What is still unverified

- Odin components were downloaded and verified by upstream UN1CA's embedded MD5 checks. AP/BL/CP/CSC archive SHA256 inventory remains to be recorded.
- Native GZH3 `super` group sizes now confirmed by UN1CA extraction: 11744051200 total and 11739856896 for `group_basic`.
- Stock A16 boot, vendor_boot and dtbo binaries are extracted and hashed, but module ABI compatibility and A16 KernelSU Next remain unverified.
- Complete patched ROM/target-files, recovery, clean/dirty upgrade path, and real board tests.

## Safety and CI

- `target/r0s/installer/assertions.edify` unconditionally aborts installation.
- `.github/workflows/r0s-config.yml` runs **only** the source configuration gate; it downloads no firmware and builds no ROM.
- Upstream full-build workflow is unchanged. An upstream `sixteen` pull request would include this WIP target in its build matrix; do not merge/pull-request it before qualification.
- No host or device qualification claimed.

## Qualification order

1. **CONFIG:** lightweight Actions execution, inspect generator output.
2. **FIRMWARE:** identify/pin A16 FUS; extract, inventory, fstab and super geometry.
3. **KERNEL:** match A16 boot chain and modules; only then integrate KernelSU Next if desired.
4. **ROM:** produce target-files; inspect OTA recovery and firmware assertions.
5. **BOARD:** verify SELinux, radio, fingerprint, camera, audio, wireless, modules and data migration.
6. **PROMOTION:** remove installer abort only after complete qualification.

## Firmware research update (2026-10-11)

- Samsung update record and EUX firmware listings identify **S901BXXSOGZH3** (Android 16, release 2026-09-03, 2026-08-05 SPL) and CSC **S901BOXMOGZH3**; firmware revision **O**.
- Host FOTA query confirmed `S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3` on 2026-10-11; real Odin AP/BL/CP/CSC contents and extracted-image SHA256 remain **UNVERIFIED**.
- `scripts/r0s/inspect_extracted_firmware.sh` reuses upstream `os_partitions_metadata.txt` to check FUS markers, API 36, super geometry, stock boot images, vendor fstab candidates and native module locations. It is **read-only** and runs only when explicitly invoked on an existing extraction.
- `scripts/ci/test_r0s_firmware_inspector.sh` tests the tool with synthetic fixtures in GitHub Actions; it does **not** obtain stock firmware.
- Modern LineageOS `s5e9925-common` fstab provides a useful `boot` / `vendor_boot` / `dtbo` reference, and its block-path mappings have been staged only for installer-resolver testing, not as qualified One UI 8 recovery evidence.
- Research/evidence details: `docs/r0s/EXTERNAL_FIRMWARE_EVIDENCE.md`.

## Boot-chain source gate (2026-10-11)

- Exynos 2200 boot, vendor_boot, dtbo and cache partition capacities now have **provisional** values from modern `LineageOS/android_device_samsung_s5e9925-common` (`lineage-23.2`).
- `scripts/r0s/inspect_boot_chain.sh` checks UN1CA-extracted stock `boot.img`, `vendor_boot.img`, and `dtbo.img` against those capacity references and UN1CA's `*_metadata.txt` header records, printing image hashes and vendor-module inventory without modifying any file.
- `scripts/ci/test_r0s_boot_chain.sh` tests the reader against synthetic invalid headers and oversized images. **This is not hardware or genuine stock A16 kernel qualification.**
- Samsung OSRC archive name `SM-S901B_16_Opensource.zip` is reported in third-party research for A16 kernel version 5.10.237, but exact **GZH3-matched** stock source/ABI remains unverified.
- See `docs/r0s/BOOT_CHAIN_PORT.md`. Installer lock stays in place.

## Updater-script source-mapping gate (2026-10-11)

- `target/r0s/installer/recovery.fstab` is now a **provisional updater-script block map only**, with raw boot/vendor_boot/dtbo/recovery locators from the maintained LineageOS Exynos 2200 reference.
- `scripts/ci/check_r0s_ota_map.sh` exercises UN1CA's actual `GET_DEVICE_FROM_MOUNTPOINT` resolver without downloading firmware or building tools, verifies `map_partition()` behavior, rejects unknown `init_boot`/`dt` locators, and confirms that `PRINT_ASSERTIONS` is generated before partition writes.
- Synthetic negative checks rejected incorrect vendor_boot mapping and missing `E3099` lock.
- **NOT YET QUALIFIED:** Samsung A16 recovery fstab, OTA package, bootloader/rollback assertions, native kernel, real device.
- See `docs/r0s/RECOVERY_OTA_STAGE.md`.

## Root-manager reuse staged (2026-10-12)

- Reused the **validated A15 installer logic** (one-shot `pm install -r` with a per-release marker) as UN1CA-specific files under `staging/r0s/ksunext/`.
- Recorded the proven A15 manager v3.4.1 APK URL and SHA256, plus old kernel source pins for traceability; neither the APK nor the A15 kernel binary was imported.
- Added `scripts/ci/check_r0s_ksu_staging.sh` to ensure the manager remains **inactive** and verify staged script/manifest invariants.
- **NOT PROMOTED:** KernelSU Next A16 kernel build, `u:r:ksu:s0` availability, real A16 manager install, SELinux enforcing and board behavior.
- Details: `docs/r0s/KSUNEXT_REUSE.md`. Existing UN1CA `preload` module unchanged.

## Real host preflight (2026-10-11)

- **HOST CONFIG PASS** at UN1CA checkout `8c2d52f2a690dd8ad88e545682e3c010f90904ef`: source syntax, native config (65 parity fields), firmware/boot synthetic tests, OTA map and KernelSU staging all passed.
- Recursive submodules initialized and clean; Samsung EUX FOTA query returned `S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3`.
- `protobuf-compiler` was checked as a command incorrectly in the host inventory; executable is `protoc`, which still needs host verification.
- Corrected the firmware inspector and fixtures to follow UN1CA's **three-component** `PDA/CSC/MODEM` marker. This change is source-level; a genuine firmware extraction has not been tested.
- Disk available before firmware/tool preparation: approximately **83 GiB reported by df -h**.

## Native extraction HOST evidence (2026-10-12)

- UN1CA downloader successfully fetched matching `S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3` and verified AP/BL/CP/CSC/HOME_CSC embedded MD5 checks.
- UN1CA extractor produced `system`, `odm`, `product`, `vendor`, `vendor_dlkm` and stock `boot.img`, `vendor_boot.img`, `dtbo.img`, `recovery.img`.
- Genuine `os_partitions_metadata.txt`: `11744051200` super; `group_basic` `11739856896`; five logical partitions.
- Stock system SDK 36; firmware inspector PASS. Stock boot header v4 carries `os_version=12.0.0`; incorrect earlier boot inspector forced 16 and failed. Boot-header raw value validation adjusted, rerun pending.
- Free disk after extraction around 55 GB. No ROM build or device testing.
- Full raw SHA256 image evidence is in `docs/r0s/BOOT_CHAIN_PORT.md`. **E3099** remains locked.

## Stock GZH3 boot & mapping host evidence (2026-10-12)

- Real boot-chain metadata inspector PASS; boot/vendor_boot header v4 and recovery header v2; SDK 36 independently proven by firmware inspector.
- Native super geometry verified: 11744051200 bytes total, group_basic max 11739856896; logical partitions are `system odm product vendor vendor_dlkm`.
- Corrected staged OTA locator map to include native `odm` and not assume a separate `system_ext` logical partition; CI and firmware fixture tests now enforce the five-name layout.
- Stock GZH3 vendor fstab SHA256 `7ecce93a3447b047c66d7db22446d3b89389352ac2af6e46dcb5560b73acbfa9`; native recovery ramdisk remains uninspected.
- Native recovery image SHA256 `b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688`, 100663296 bytes, header v2. This does NOT certify custom recovery or OTA.
- User host has about 55 GB free after stock extraction. Installer `E3099` remains locked.

## Recovery ramdisk/module ABI next host gate (2026-10-12)

- Native GZH3 recovery ramdisk contains `system/etc/recovery.fstab` and Samsung-specific init rc files. Stock recovery header command line reports `androidboot.selinux=permissive`; this does NOT prove normal Android 16 runs permissive.
- All five extracted `.ko` files carry the same stock release `5.10.237-android12-9-31999025-abS901BXXSOGZH3`, with modversions, but kernel source/symbol CRC/loadable ABI remain unverified.
- Added `scripts/r0s/inspect_recovery_abi.sh` to read stock recovery fstab contents and verify consistent GZH3 stock module vermagic on host. The script is read-only; real-run result pending. Installer still `E3099` locked.

## Native recovery fstab host inspection (2026-10-12)

- Recovery LZ4 ramdisk extracted successfully. `system/etc/recovery.fstab` SHA256 `91d60dcf617483a260600d2ea25054a56a7cad806ec6011218b044262fe2b488`.
- Recovery fstab has all GZH3 logical names and raw boot/vendor_boot/dtbo/recovery paths; additionally mentions `system_ext` absent from the actual five-name super metadata. Staged OTA map correctly excludes it.
- Stock recovery header includes `androidboot.selinux=permissive`; no normal-OS SELinux claim.
- All five stock vendor .ko files passed exact `5.10.237-android12-9-31999025-abS901BXXSOGZH3` vermagic coherence check. Rebuilt kernel Module.symvers/CRC and BOARD still untested.
- New read-only native recovery/vendor/super/staging consistency verifier and synthetic negative tests staged. Host rerun pending. E3099 locked; no ROM flash.
