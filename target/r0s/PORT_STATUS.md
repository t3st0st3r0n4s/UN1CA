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
- **OTA BLOCKER:** missing A16 `recovery.fstab`. UN1CA's `install_utils.sh` requires a device or platform installer fstab; no safe verified S901B A16 version is available yet.
- Details: `docs/r0s/SOURCE_INVENTORY.md`.

## What is still unverified

- Exact A16 FUS four-part firmware release and hashes; firmware selection currently follows latest from UN1CA's downloader.
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
