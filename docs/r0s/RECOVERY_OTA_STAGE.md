# UN1CA S901B Android 16 — provisional OTA block mapping

**Status: STOCK VENDOR FSTAB/SUPER LOCATORS VERIFIED / RECOVERY RAMDISK UNVERIFIED / INSTALLER LOCKED.**

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
