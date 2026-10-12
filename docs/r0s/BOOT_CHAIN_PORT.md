# Exynos 2200 boot-chain preparation — UN1CA sixteen-r0s

Status: **STOCK GZH3 FIRMWARE EXTRACTED / BOOT METADATA UNDER REVIEW / BOARD NOT TESTED**. The firmware was extracted on the Ubuntu host; no ROM/kernel build or physical boot test.

## Donor/source decision

1. **Authority for runtime images:** native Samsung S901B Android 16 (same `SM-S901B/EUX` in UN1CA's `unica/configs/essi.sh`).
2. **Partition-size reference:** `LineageOS/android_device_samsung_s5e9925-common`, branch `lineage-23.2`, `BoardConfigCommon.mk` (not a proven stock A16 GZH3 image layout).
3. **Candidate kernel source:** Samsung OSRC `SM-S901B_16_Opensource.zip`, whose name and kernel 5.10.237 toolchain notes have been reported in a third-party A16/GZD7 research record. Direct package hash/source inspection and correspondence to GZH3 are **not verified**.
4. **Non-authoritative references:** ExtremeKRNL A15 pinned commit and Lineage kernel 23.2; neither is to be flashed on native One UI 8 without a matching ABI and vendor-module audit.

## Partition-size reference imported into platform config

| Key | Bytes | Reference |
| --- | ---: | --- |
| `TARGET_BOOT_PARTITION_SIZE` | 67108864 | Lineage s5e9925-common |
| `TARGET_VENDOR_BOOT_PARTITION_SIZE` | 33554432 | Lineage s5e9925-common |
| `TARGET_DTBO_PARTITION_SIZE` | 8388608 | Lineage s5e9925-common |
| `TARGET_CACHE_PARTITION_SIZE` | 629145600 | Lineage s5e9925-common |
| `TARGET_SUPER_PARTITION_SIZE` | 11744051200 | Prior FYI3; also Lineage reference |
| `TARGET_GROUP_BASIC_SIZE` | 11739856896 | Prior FYI3 / Lineage group-size numeric reference, group naming differs |

The S901B GZH3 extraction on 2026-10-12 **confirms** the stock `super_partition_size=11744051200`, `super_partition_group=group_basic`, and `super_group_basic_group_size=11739856896`. Other size references remain provisional except `boot.img`'s exact extracted size of 67108864 bytes (not proof of device partition block capacity).

## Reuse of UN1CA upstream extraction

`scripts/extract_fw.sh` already emits `out/fw/SM-S901B_EUX/boot.img_metadata.txt` and `vendor_boot.img_metadata.txt`, with boot header version, OS version and other image details, as well as `kernel/boot.img`, `kernel/vendor_boot.img`, and `kernel/dtbo.img`.

The script `scripts/r0s/inspect_boot_chain.sh` consumes those outputs. It checks boot header v4, provisional partition-size bounds and the **syntax** of the raw boot-header OS field. The header field is **not** the system's Android version (SDK 36 is verified independently from extracted `system/system/build.prop`). It prints SHA256, native vendor fstab location and module inventory. This is deliberately **read-only**, with no kernel build, modification, flashing or runtime assertion.

The synthetic gate `scripts/ci/test_r0s_boot_chain.sh` tests acceptable mock metadata, an invalid header and an oversized image. It does not establish that actual Samsung GZH3 images pass.

## Missing gates

- Exact stock boot/DTBO/vendor_boot files have now been extracted and SHA256 recorded; internal compatibility and stock recovery remain unqualified.
- Matched kernel source, toolchain, config, Module.symvers and exported-symbol CRC compatibility with Samsung vendor modules.
- Actual native A16 recovery fstab and UN1CA full-OTA installer integration.
- Root support (KernelSU Next), enforcing SELinux and physical S901B hardware tests.

**Installer remains intentionally locked with E3099.**

### External references

- https://github.com/LineageOS/android_device_samsung_s5e9925-common/blob/lineage-23.2/BoardConfigCommon.mk
- https://github.com/LineageOS/android_device_samsung_s5e9925-common/blob/lineage-23.2/configs/init/fstab.s5e9925
- https://opensource.samsung.com/
- https://github.com/BuSung-dev/Root-My-Galaxy-Payloads/pull/138

## Real Samsung S901B GZH3 host extraction (2026-10-12)

- `PDA/CSC/MODEM`: `S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3` verified against the local Odin release marker.
- Native `super.img` extraction and partitions: `system odm product vendor vendor_dlkm`; sizes match the earlier static references.
- System `ro.build.version.sdk=36` (**Android 16**).
- Stock `boot.img`: 67108864 bytes, SHA256 `c805736861ad444f0e874cbd6b3f2e006360aae36364e1b2d58d0952f14de7c1`; `header_version=4` and `os_version=12.0.0` as recorded by UN1CA's `unpack_bootimg` parser.
- Stock `vendor_boot.img`: SHA256 `f329135a8fcc199d6e763663267ba2c18e8c0e9f2e8189be9efa158a73cabd47`.
- Stock `dtbo.img`: SHA256 `4c0c923d9f7fb4571be003f9e45a19df37473822136442f4e512deb7fdccf48e`.
- Native modules observed: `fingerprint.ko`, `fingerprint_sysfs.ko`, `input_booster_lkm.ko`, `sec_debug_coredump.ko`, `wlan.ko`.
- `recovery.img` was extracted; **its ramdisk, installer fstab and boot compatibility are not yet inspected**.
- Firmware-inspector PASS; original boot inspector exited 2 **solely because it conflated the boot-header OS field with the Android system version**. Corrected inspector must be rerun before claiming boot-metadata precheck pass.
- Root, recovery OTA, kernel ABI and board remain BLOCKED/DEFERRED.

Primary field-format reference: https://source.android.com/docs/core/architecture/bootloader/boot-image-header

## Genuine GZH3 boot metadata verified on host (2026-10-12)

- Synthetic and real boot metadata inspector PASS.
- Stock `boot.img` 67108864 bytes; `vendor_boot.img` 33554432 bytes; `dtbo.img` 8388608 bytes. They match expected image capacities exactly, but this alone does not prove GPT partition block capacities.
- `boot.img`: header v4; raw boot-header `os_version=12.0.0`, patch level `2026-08`.
- `vendor_boot.img`: header v4; `os_version` not recorded.
- `recovery.img`: header v2, raw boot-header `os_version=12.0.0`, patch `2026-08`, size 100663296 bytes, SHA256 `b30c9dee9337d8a39d940cb25346b975e920c3507574ad0d3ed88dbf6a2ef688`.
- Native `vendor/etc/fstab.s5e9925` SHA256 `7ecce93a3447b047c66d7db22446d3b89389352ac2af6e46dcb5560b73acbfa9`. This is vendor first-stage fstab, not verified native recovery fstab.
- Remaining gates: recovery ramdisk, kernel/module ABI, full ROM and physical S901B.

## UN1CA ROM workdir built on real GZH3 A16 firmware (2026-10-12)

The user successfully ran make_rom.sh --no-target-files. Upstream modified workdir copies of the boot chain: boot.img 36,700,176 bytes versus stock 67,108,864; vendor_boot.img 15,912,960 versus stock 33,554,432; dtbo.img 2,204,388 versus stock 8,388,608. The log shows removal of AVB/Samsung footers, vendor_boot fstab patching and a PROCA boot-kernel patch; modified images must not inherit stock image qualifications. scripts/r0s/inspect_built_workdir.sh is a read-only postbuild header, size, archive and module audit; pending host execution. No boot or board PASS claimed.
