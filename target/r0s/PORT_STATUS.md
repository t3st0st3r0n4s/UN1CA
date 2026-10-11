# UN1CA `sixteen-r0s` status

**STATE:** CONFIG_PREPARED / HOST_UNVERIFIED / BOARD_DEFERRED / INSTALLER_LOCKED.

## Source baseline

- Fork basis: `salvogiangri/UN1CA` `sixteen`, commit `ce12c6e077fc1865e574873f316c450cdf587bd2` (2026-10-11).
- Device: Samsung Galaxy S22 5G Exynos `SM-S901B` / `r0s` / `exynos2200`.
- Android: 16 / SDK 36 / One UI 8.
- Source and target: stock/native `SM-S901B/EUX` as defined by current upstream `unica/configs/essi.sh`.
- Feature map is intentionally inherited from the same native source, rather than copying old One UI 7 flags into the new schema.
- UN1CA owns the core build, packaging, OTA, framework, CSC, Paradigm, and default modules.
- The old TachyonOS `r0s-fyi3` remains untouched and is not this branch's parent.

## What has *not* been proven

- Real FUS four-part A16 firmware pin and extraction hashes; current `SOURCE_FIRMWARE` resolves to newest available firmware.
- Exact S901B Android 16 super-partition geometry (A15 sizes in `target/r0s/config.sh` are provisional).
- Kernel/DTBO/vendor_boot/vendor modules compatibility; KernelSU Next A16 integration is not attempted.
- Native A16 camera, Bluetooth, MIDAS and framework/feature patches under a completed ROM.
- Recovery, clean/dirty upgrade behaviour and BOARD tests.

## Safety and CI

- `target/r0s/installer/assertions.edify` aborts any attempted installation unconditionally.
- `.github/workflows/r0s-config.yml` validates configuration only, without firmware downloads or a ROM build.
- Upstream `.github/workflows/ci.yml` is deliberately untouched; upstream full-build checks on the `sixteen` branch and pull requests must not treat the WIP target as ready.
- No flash, host compilation or device qualification claimed.

## Qualification order

1. **CONFIG:** source `buildenv.sh r0s` in lightweight CI, inspect generated values.
2. **FIRMWARE:** identify/pin exact A16 FUS revision; extract/inventory; establish bootloader and partition constraints.
3. **KERNEL:** choose matched stock A16 kernel and boot chain; optionally integrate KernelSU Next from source; verify module ABI and host outputs.
4. **ROM:** use native S901B blobs and UN1CA patches; produce target-files; inspect OTA flash assertions.
5. **BOARD:** controlled hardware tests, SELinux, radio, fingerprint, camera, audio, wireless, modules, recovery and data migration.
6. **PROMOTION:** replace preliminary assertions with real firmware/recovery requirements only when BOARD PASS.
