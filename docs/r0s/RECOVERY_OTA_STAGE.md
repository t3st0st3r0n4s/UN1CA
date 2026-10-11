# UN1CA S901B Android 16 — provisional OTA block mapping

**Status: SOURCE MAPPING PREPARED / NATIVE RECOVERY UNVERIFIED / INSTALLER LOCKED.**

## Why this exists

UN1CA's `scripts/utils/install_utils.sh` requires a target or platform
`recovery.fstab` file, even when it resolves a logical partition to
`map_partition("system")`. Its full updater script also needs raw block
locations for `boot.img`, `vendor_boot.img` and `dtbo.img`.

The S901B A16 firmware has **not** been downloaded or extracted. To avoid
claiming a native One UI 8 recovery fstab, `target/r0s/installer/recovery.fstab`
is only a **provisional updater-script block map** backed by current Exynos 2200
device-source references. It must never be used as a proven recovery mount
configuration.

Reference: https://github.com/LineageOS/android_device_samsung_s5e9925-common/blob/lineage-23.2/configs/init/fstab.s5e9925

## What is mapped

- Logical partitions: `system`, `vendor`, `product`, `vendor_dlkm`, `system_ext`.
  UN1CA uses `map_partition(...)` for these regardless of the raw block column.
  Any additional real A16 dynamic partitions still require native super inventory.
- Non-logical partitions with current device-source evidence:
  `/dev/block/by-name/boot`, `vendor_boot`, `dtbo`, `recovery`.
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
- No firmware download, boot image manipulation, kernel building, full-OTA
  generation, recovery deployment or real-board tests have been performed.

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
