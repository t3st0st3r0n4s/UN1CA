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

**The normal installer has no artificial abort; BOARD qualification remains pending.**

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

## Post-workdir image parser fix (2026-10-12)

Host inspection of modified UN1CA `boot.img` succeeded: header v4, `os_version=12.0.0`, image SHA256 `cf90d5cba49d65cff2c67a35d5138f8ef02b6bf98aa3592d6625a27aeefd0498`. The same audit's vendor_boot check failed because it searched for the **boot.img** label `boot image header version: 4` instead of the actual AOSP **vendor_boot** label `vendor boot image header version: 4`. `unpack_bootimg` itself returned success before this false negative. The specific header-label check has now been fixed and a synthetic test added; a new real-host audit remains pending. Nothing was repacked or flashed to correct this source-level issue. Android format reference: https://android.googlesource.com/platform/system/tools/mkbootimg/+/808d42e197506319ee65eb078d3defd9602e2ac2/unpack_bootimg.py

## Host workdir audit accepted; next compare embedded kernel and vendor ramdisks (2026-10-12)

The user reran the corrected postbuild inspector on actual GZH3-derived UN1CA workdir: **PASS**. Real images (SHA256): work boot `cf90d5cba49d65cff2c67a35d5138f8ef02b6bf98aa3592d6625a27aeefd0498` (36700176 bytes); work vendor_boot `fb3837838c597d39f58ed103ac8476b0c7cfebbe47dff400e870d55250e4a0a8` (15912960 bytes); work dtbo `e4d14f0fa365a99be3ed7d3a060e9528b103b617f055ef56cd58f965793f7913` (2204388 bytes). Both boot and vendor_boot v4 parsers passed, all five stock vendor modules match byte-for-byte, and four rebuilt core archives passed zip CRC. Work vendor_boot advertises `androidboot.selinux=permissive`; must compare to **stock vendor_boot** before inferring whether it is an introduced change, and normal-OS SELinux remains UNVERIFIED. Added `scripts/r0s/inspect_postbuild_boot_ramdisks.sh` for read-only raw kernel hash, stock/work vendor ramdisk fstab and metadata comparison. No kernel/ROM flash qualification.

## Actual GZH3 stock vs work kernel and ramdisk evidence (2026-10-13)

The real host review (`inspect_postbuild_boot_ramdisks.sh`) produced stock embedded-kernel SHA256 `1a3481f961f2acb93b2ce556c1179d3842359dd00782d9f566b305687a0dee39` and work SHA256 `dd509289798cfa756c649e77179d758101cddae6273a649be7835ae34080ca4a`. Different hashes alone **do not** verify the change is limited to PROCA.

Stock and work `vendor_boot` both have v4 headers and exactly the same vendor cmdline (`androidboot.selinux=permissive bootconfig loop.max_part=7`); UN1CA did not introduce this flag. `vendor_ramdisk01` remains byte-identical (SHA256 `44871726b54bba8454629bc20508ad92aaae45d43f9fc52fa44cfbbf56621f79`). The two matched stock/work fstab files in `vendor_ramdisk00` retain the same logical mount locations and AVB flags but replace f2fs/ext4 alternatives with the intended EROFS entries for all five native partitions. This is host image analysis, **not** a boot or SELinux PASS.

UN1CA's active source at `unica/patches/proca/customize.sh` modifies decompressed ARM64 kernel bytes at offset 40 (if not zero/prepatched) and replaces one exact PROCA string literal with a same-length literal. The new `scripts/r0s/check_proca_kernel_delta.py` implements only those two transformations and compares the **entire decompressed** stock and rebuilt kernel byte-for-byte against the expected result. Any unrelated change, unexpected length or ambiguous duplicate literal blocks. The existing postbuild ramdisk inspection now invokes this exact-delta check. Synthetic tests exercise raw/gzip positive examples and corruption, patch omission and other negative cases.

The **real host exact-delta rerun remains pending**. Passing the new byte-level gate would validate patch scope only, not kernel module ABI, runtime SELinux, AVB, bootability or BOARD. The installer no longer carries the former test-only abort.

## CRITICAL: A15 FYI3 -> GZH3 A16 prerequisite / bootloader rollback gate (2026-10-13)

**This project MUST NOT recommend flashing full stock GZH3 first or
flashing the UN1CA ZIP directly from FYI3 without independent device and
bootchain qualification.** The target files and kernel/module audits are
HOST-only and do not establish either upgrade path.

Current phone is on rooted/unlocked A15 FYI3 firmware
`S901BXXSIFYI3` (Samsung RP/SW REV **I = 18**), with current A15
custom recovery. The extracted GZH3 A16 firmware is
`S901BXXSOGZH3` (Samsung RP/SW REV **O = 24**); the switch is a
**six-revision antirollback jump**. Confirm the exact live device
Download-mode RP value before any attempted flash.
Public firmware build references:
https://samfirm.shop/build/S901BXXSIFYI3 and
https://samfirm.shop/fr/build/S901BXXSOGZH3.
Samsung rollback protection may prevent restoring FYI3 BL once
GZH3 BL is installed.

UN1CA upstream expressly warns that **official One UI 8 removed the
ability to unlock Samsung bootloaders** and reverting to older One UI
can become impossible:
https://github.com/salvogiangri/UN1CA/discussions/129.
The impact on an *already-unlocked* S901B after an O-revision BL flash
is **NOT verified**; retaining the unlocked state must never be assumed.
A stock One UI 8 full BL/AP/CP/CSC flash could therefore destroy
the essential precondition for this custom ROM project.

UN1CA's install guide
https://github.com/salvogiangri/UN1CA/discussions/130
requires custom recovery and a device-specific flashable ZIP, but
**does not universally require booting full stock A16 first**.
Its installation FAQ
https://github.com/salvogiangri/UN1CA/discussions/629
notes that mismatched bootloader revisions may require a specific
firmware before installation. For *our* native-GZH3 based port
there is no validated compatibility proof that FYI3's A15 BL
can start GZH3-derived A16 boot / vendor_boot / dtbo + kernel;
equally, there is no validated safe procedure to use GZH3 BL while
preserving bootloader unlock.

**Mandatory promotion decisions:**

- Preserve device's known-working FYI3 A15 installation, bootloader
  unlock and backups; no production BL or GZH3 stock flash.
- Reconcile FYI3 live Download-mode bootloader RP and security state
  with exact FYI3/GZH3 BL, modem, vbmeta, and boot partition deltas.
- Determine whether A16 GZH3 boot/kernel/vendor can run with a
  retained unlocked A15 bootloader. Requires device-specific evidence,
  not upstream assumptions or a simple old-recovery ELF check.
- If A16 requires later RP-O bootloader, determine and validate
  bootloader-unlock survivability and recovery/rollback safety **before**
  writing any permanent bootloader component. If not achievable,
  this ROM cannot be approved for physical install as designed.
- Independently qualify custom recovery's actual block OTA install
  protocol, AVB and five-partition layout; the original trial-only
  installer abort stays enabled.

**Status: GZH3-ON-RETAINED-I BOOT/AVB COMPATIBILITY = HARD BLOCKER.**

**Narrow correction (2026-10-13):** Samsung's official S901B Android 16
release `S901BXXUIGYI7` uses **bootloader binary I (18)**, the same RP
number as TachyonOS FYI3. Its CSC is `S901BOXMIGYI7`; Samsung's
release history identifies it as One UI 8 / Android 16. Thus Android 16
does **not** intrinsically require moving to GZH3's O (24). The correct
technical question is whether GZH3 boot/vendor can operate with the
*existing* unlocked I bootloader, and whether its companion CP, AVB
and security firmware remain compatible. Binary revision equality
alone is not evidence that FYI3/GYI7 firmware binaries are interchangeable.
Use GYI7 as a reference for the compatible Android 16 firmware generation;
DO NOT flash its stock BL or any stock One UI 8 firmware to this unlocked
development device as an investigative shortcut.

Primary sources:
- https://doc.samsungmobile.com/SM-S901B/021718220304/eng.html
- https://samfirm.shop/build/S901BXXUIGYI7
- https://s-update.samsungvn.com/devices/SM-S901B
Do NOT instruct stock GZH3 preflash or direct current-device A15
TWRP install in the absence of those qualifications.

## Retained-BL reversible route is mandatory (decision 2026-10-13)

The project's selected installation path **retains the working unlocked
TachyonOS FYI3 bootloader (I = 18)**. Do not propose advancing BL to GZH3
O = 24. Device-specific Android 16 S901B evidence (including LineageOS 23.2's
FYI3 prerequisite and Samsung's Android 16 GYI7 binary-I firmware) supports
preserving a binary-I bootloader as a valid *development strategy*, but
does not prove this particular GZH3 kernel boots with our unchanged FYI3 BL.

Any needed GZH3 incompatibility must be handled within a compatible A16
boot/kernel/vendor design, not by breaking the user's BL rollback policy.
Require an independently usable path back to the existing FYI3 TachyonOS
ROM: matched logical partitions/boot chain, relevant vbmeta and the working
TWRP, with saved backups. Data may need format/restore; **reversible ROM
firmware is not the same as guaranteed preservation of Android userdata**.
The A16 install and A15 return path require physical qualification.

## Original TWRP-provided vbmeta flags — host evidence (2026-10-13)

The user directly examined the existing
`~/android/S22-ROM/S901B_twrp_logo_vbmeta.tar`, which contains
`recovery.img`, `up_param.bin` and `vbmeta.img` (10,576 bytes).
The `avbtool info_image` output for that archive's `vbmeta.img`:

- Algorithm: `SHA256_RSA4096`; rollback index `0`;
  rollback index location `0`.
- **Flags `3`**: AVB `HASHTREE_DISABLED=1` and
  `VERIFICATION_DISABLED=2`; standard libavb disables hashtree
  enforcement and descriptor verification for a top-level vbmeta
  bearing these flags. This is evidence of a development-mode
  patched AVB configuration, not a blanket Samsung boot trust bypass.
- Chained descriptors for recovery, dtbo, prism and optics; hash
  descriptors for boot, **bootloader**, fld, harx, keystorage, ldfw,
  tzsw, vendor_boot; hashtree descriptors for five logical partitions.
  These are **verification metadata only**. The bootloader descriptor
  does not write or upgrade Samsung BL.
- The existing package's declared OS/security-patch descriptors are
  mostly 2023 era. Their values are not evidence of the present
  TachyonOS FYI3 image hashes; flags 3 explain why stale hashes can
  be tolerated by standard libavb on an unlocked device.

This is the **original TWRP archive**, not an independently checked
readback of today's `/dev/block/by-name/vbmeta`. The project previously
installed the TWRP package and has not intentionally replaced vbmeta,
so reuse it as the expected baseline, but do not assert byte-for-byte
live identity without evidence.

**AVB design direction:** retain the existing patched vbmeta; the
UN1CA full ZIP intentionally omits vbmeta and all BL/CP/recovery
partitions. Do not flash or replace any of them just to adopt A16.
AOSP's vbmeta flags do **not** prove Samsung secure-boot TrustZone /
antirollback compatibility or that GZH3 normal boot works with the
existing FYI3 bootloader. The historical non-installing A16 package
has development-key AVB footers verified on host; that does not
establish device boot acceptance.

Source for exact flag bit meanings:
https://android.googlesource.com/platform/external/avb/+/master/libavb/avb_vbmeta_image.h
