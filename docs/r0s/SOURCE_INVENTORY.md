# r0s Android 16 source-level inventory — 2026-10-11

Authoritative base: `salvogiangri/UN1CA` `sixteen` at `ce12c6e077fc1865e574873f316c450cdf587bd2`.
Scope: source review ONLY; no firmware extraction, host compilation or hardware tests.

## Confirmed upstream reuse

- `unica/configs/essi.sh`: native Galaxy S22 Exynos One UI 8, SDK 36, S901B/EUX; 64 `SOURCE_*` declarations including array `SOURCE_EXTRA_FIRMWARES`.
- `scripts/internal/create_work_dir.sh`: `system` and `product` sourced from source firmware, `vendor`, `vendor_dlkm`, `odm`, `odm_dlkm`, `system_dlkm` and kernel images taken from target firmware. Since source and target are both S901B, no cross-device transplant is required.
- `unica/patches/camera/customize.sh`: falls back to the native target `camera-feature.xml` when source/target Android SDK values match.
- `unica/patches/vintf/customize.sh`: falls back to native target VINTF files for equal SDK values.
- `unica/patches/stock_blobs/customize.sh`: contains existing target feature/audio reconciliation.
- `unica/patches/fs/customize.sh`: repacks the native boot/vendor_boot ramdisk fstab for selected filesystem type.
- `scripts/internal/gen_config_file.sh`: defines the current Android 16 target configuration schema.
- `unica/mods`: existing maintained UN1CA mods remain authoritative; do not add duplicates from ExtremeROM.

## Missing or provisional

| Item | State | Evidence required |
| --- | --- | --- |
| `target/r0s` basic config | PREPARED | `scripts/ci/check_r0s_config.sh` on Actions |
| Exynos 2200 platform config | PREPARED | Generated UN1CA config + extracted native images |
| S901B `recovery.fstab` | **MISSING / OTA BLOCKER** | Extract matching A16 recovery/boot fstab and compare recovery mount points |
| S901B OTA bootloader/firmware assertions | **MISSING / OTA BLOCKER** | A16 four-part FUS + supported rollback/upgrade path |
| A16 `super` / `group_basic` geometry | PROVISIONAL (from FYI3) | Extracted A16 `lpdump`; replace unverified figures |
| Boot/dtbo/vendor_boot/module ABI | UNVERIFIED | Native A16 images, stock kernel source and module inventory |
| KernelSU Next | NOT ATTEMPTED | Matched A16 kernel before adaptation |
| Target-specific camera/MIDAS patch set | NOT IMPORTED | Demonstrate failure in native A16 first |
| Recovery/data migration | NOT TESTED | Hardware validation before enabling installer |

## Blocking issue in UN1CA installer

`scripts/utils/install_utils.sh` searches for
`target/r0s/installer/recovery.fstab` and, failing that,
`platform/exynos2200/installer/recovery.fstab`.
Neither file exists in the current port. Do **not** copy the Exynos 2100
`recovery.fstab` or fabricate native Android 16 partitions to satisfy the
installer. The unconditional `E3099` abort remains installed, but the recovery
fstab is separately required before building a production full OTA.

## Code policy

1. Use native S901B A16 system/vendor/boot as the baseline.
2. Carry no Android 15 ExtremeKRNL kernel or vendor modules into A16.
3. No Bluetooth APEX, ArcSoft/HRE, MIDAS, camera, encryption or device-specific
   stock-blob substitutions without a demonstrated A16 regression.
4. Keep UN1CA's Android 16 framework and settings modifications authoritative.
5. Unlock OTA only after firmware, ROM host and real-board evidence passes.
