# Native S901B Android 16 firmware + kernel qualification

Stage: RESEARCH / NO IMPLEMENTATION / NO FLASH.

- Samsung's official S901B Android 16 update page documents AP `S901BXXSOGZH3` (2026-09-03; August 2026 SPL). This is **not** a full FUS 4-part firmware pin and does not prove the current firmware selected by `SM-S901B/EUX`.
- The upstream `unica/configs/essi.sh` already specifies `SM-S901B/EUX` as its native Android 16 source. This dev branch intentionally keeps `TARGET_FIRMWARE=$SOURCE_FIRMWARE` until the exact extracted version is independently identified.
- Firmware images must be inventoried by partition, with whole-image hashes and metadata recorded. Confirm EROFS, dynamic partition group sizes, bootloader revision and rollback implications.
- Start kernel qualification from the matched **stock A16 S901B** `boot.img`, `vendor_boot.img`, `dtbo.img` and vendor modules. Do not reuse Android 15 ExtremeKRNL or its `wlan.ko`, fingerprint, input booster and other module outputs.
- Source-level KernelSU Next implementation can be evaluated only against an exact A16 kernel source release; verify symvers, CRCs, compiler/toolchain and module loadability before any boot image integration.
- Samsung Open Source Release Center is the official kernel-source discovery location, but the exact matching S901B A16 source archive remains UNVERIFIED.
- `lineage-23.2` in ExtremeXT's Exynos kernel repository is a *potential reference*, not a proven One UI 8 stock-kernel replacement.
- Remove the unconditional `target/r0s/installer/assertions.edify` abort only when the ROM, kernel and board gates are all passed.

Upstream documentation:
- https://doc.samsungmobile.com/SM-S901B/021722220304/roh.html
- https://opensource.samsung.com/uploadList?classification1=mobile_phone&menuItem=mobile
