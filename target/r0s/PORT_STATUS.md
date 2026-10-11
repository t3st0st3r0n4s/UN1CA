# UN1CA `sixteen-r0s` status

**STATE:** CONFIG_PREPARED / HOST_UNVERIFIED / BOARD_DEFERRED / INSTALLER_LOCKED.

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

- Exact A16 Odin AP/BL/CP/CSC archive/image hashes; firmware selection currently follows latest from UN1CA's downloader.
- Exact A16 `super` group sizes (current figures are FYI3-derived placeholders).
- Stock A16 kernel, DTBO, vendor_boot and module ABI compatibility; no A16 KernelSU Next work performed.
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
