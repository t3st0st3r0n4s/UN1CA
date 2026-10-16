# Native S901B Android 16 firmware + kernel qualification

Stage: RESEARCH / NO IMPLEMENTATION / NO FLASH.

- Samsung's official S901B Android 16 update page documents AP `S901BXXSOGZH3` (2026-09-03; August 2026 SPL). This is **not** a full FUS 4-part firmware pin and does not prove the current firmware selected by `SM-S901B/EUX`.
- The upstream `unica/configs/essi.sh` already specifies `SM-S901B/EUX` as its native Android 16 source. This dev branch intentionally keeps `TARGET_FIRMWARE=$SOURCE_FIRMWARE` until the exact extracted version is independently identified.
- Firmware images must be inventoried by partition, with whole-image hashes and metadata recorded. Confirm EROFS, dynamic partition group sizes, bootloader revision and rollback implications.
- Start kernel qualification from the matched **stock A16 S901B** `boot.img`, `vendor_boot.img`, `dtbo.img` and vendor modules. Do not reuse Android 15 ExtremeKRNL or its `wlan.ko`, fingerprint, input booster and other module outputs.
- Source-level KernelSU Next implementation can be evaluated only against an exact A16 kernel source release; verify symvers, CRCs, compiler/toolchain and module loadability before any boot image integration.
- Samsung Open Source Release Center is the official kernel-source discovery location, but the exact matching S901B A16 source archive remains UNVERIFIED.
- `lineage-23.2` in ExtremeXT's Exynos kernel repository is a *potential reference*, not a proven One UI 8 stock-kernel replacement.
- The earlier dummy-probe abort has been removed from the installer. Kernel and ROM runtime still require BOARD qualification.

Upstream documentation:
- https://doc.samsungmobile.com/SM-S901B/021722220304/roh.html
- https://opensource.samsung.com/uploadList?classification1=mobile_phone&menuItem=mobile

## Native GZH3 firmware now extracted on Ubuntu host (2026-10-12)

The user has downloaded and checksum-verified Samsung A16 Odin archives and extracted matching GZH3 stock images using upstream UN1CA tools. System API is 36. Super geometry matches exactly: 11744051200 bytes, group_basic 11739856896. Stock boot/dtbo/vendor_boot SHA256 and module names are preserved in `BOOT_CHAIN_PORT.md`.

The original boot inspector rejected stock `boot.img` because its header independently stores `os_version=12.0.0`. This is not `ro.build.version.sdk`; parsing/validating the raw value must not require `16`. The stock image and recorded header are retained untouched. Kernel ABI and real-device behavior remain **UNVERIFIED**.

## Stock GZH3 recovery and module metadata (2026-10-12)

All five GZH3 vendor_dlkm modules share vermagic `5.10.237-android12-9-31999025-abS901BXXSOGZH3 SMP preempt mod_unload modversions aarch64`. This is stock-module coherence, not a rebuilt kernel ABI pass. Dependencies include fingerprint_sysfs/exynos_pm_qos, exynos-ufcc, dss, cnss2, cfg80211 and other Qualcomm/Samsung support modules. Matched kernel source, symbol CRCs and board module loading remain pending.

The native recovery image reports `androidboot.selinux=permissive` in its command line; normal Android SELinux state is **not** determined by this recovery-only flag. Native `system/etc/recovery.fstab` was discovered in its LZ4 ramdisk, but the file content and recovery OTA behavior still need inspection. A read-only host inspector has been staged for this purpose.
