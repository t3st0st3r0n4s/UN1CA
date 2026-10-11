# Exynos 2200 boot-chain preparation — UN1CA sixteen-r0s

Status: **SOURCE/STATIC GATES ONLY**. No stock A16 image extracted or boot tested.

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

Do not treat these as extracted GZH3 partition metadata. Replace/corroborate only against stock Samsung metadata before a ROM or OTA can be accepted.

## Reuse of UN1CA upstream extraction

`scripts/extract_fw.sh` already emits `out/fw/SM-S901B_EUX/boot.img_metadata.txt` and `vendor_boot.img_metadata.txt`, with boot header version, OS version and other image details, as well as `kernel/boot.img`, `kernel/vendor_boot.img`, and `kernel/dtbo.img`.

The script `scripts/r0s/inspect_boot_chain.sh` consumes those outputs. It checks the expected boot header v4, provisional partition-size bounds and Android 16 boot-header OS identification when present, and prints SHA256, native vendor fstab location and module inventory. This is deliberately **read-only**, with no kernel build, modification, flashing or runtime assertion.

The synthetic gate `scripts/ci/test_r0s_boot_chain.sh` tests acceptable mock metadata, an invalid header and an oversized image. It does not establish that actual Samsung GZH3 images pass.

## Missing gates

- Exact four-part FUS release and stock boot/DTBO/vendor_boot bytes.
- Matched kernel source, toolchain, config, Module.symvers and exported-symbol CRC compatibility with Samsung vendor modules.
- Actual native A16 recovery fstab and UN1CA full-OTA installer integration.
- Root support (KernelSU Next), enforcing SELinux and physical S901B hardware tests.

**Installer remains intentionally locked with E3099.**

### External references

- https://github.com/LineageOS/android_device_samsung_s5e9925-common/blob/lineage-23.2/BoardConfigCommon.mk
- https://github.com/LineageOS/android_device_samsung_s5e9925-common/blob/lineage-23.2/configs/init/fstab.s5e9925
- https://opensource.samsung.com/
- https://github.com/BuSung-dev/Root-My-Galaxy-Payloads/pull/138
