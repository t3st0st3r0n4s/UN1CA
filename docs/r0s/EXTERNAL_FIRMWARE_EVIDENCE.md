# S901B Android 16 firmware and recovery research (11 October 2026)

**Status: PUBLIC RESEARCH ONLY. No Android 16 firmware has been downloaded or extracted for this port.**

## Public Samsung EUX firmware candidate

| Field | Evidence-backed value |
| --- | --- |
| Model/CSC | `SM-S901B / EUX` |
| OS | Android 16 / One UI 8; API level 36 |
| PDA/AP | `S901BXXSOGZH3` |
| OXM CSC | `S901BOXMOGZH3` |
| Samsung publication date | 2026-09-03 |
| Security patch | 2026-08-05 |
| Bootloader / binary revision | `O` (public firmware listing) |
| Public archive MD5 | `9e4e16470c68c344a3aefbb3eebd727a` (third-party archive listing, **not** a hash verified by this project) |
| FOTA `PDA/CSC/MODEM` | `S901BXXSOGZH3/S901BOXMOGZH3/S901BXXSOGZH3` (observed on Ubuntu host 2026-10-11) |
| Odin archive components | AP/BL/CP/CSC tarballs **not yet downloaded/verified** |
| Extracted image hashes / fstab / lpdump | **Not verified** |

Primary Samsung publication:
https://doc.samsungmobile.com/SM-S901B/021722220304/roh.html

EUX firmware listing:
https://samfw.com/firmware/sm-s901b/eux/s901bxxsogzh3

Cross-reference for EUX PDA and CSC:
https://s-update.samsungvn.com/devices/SM-S901B

The `SOURCE_FIRMWARE` key in `unica/configs/essi.sh` still uses UN1CA's Samsung FUS lookup. The result may change when Samsung updates firmware. **Do not mistake the three-component FOTA update string for four Odin archive component hashes or a pinned Samsung release download.** This milestone does not change the source firmware selection.

## Native extraction pipeline (reuse, not replacement)

UN1CA `scripts/extract_fw.sh` already creates:

- `out/fw/SM-S901B_EUX/.extracted`: Samsung `PDA/CSC/MODEM` triplet recorded by UN1CA's extractor.
- `out/fw/SM-S901B_EUX/os_partitions_metadata.txt`: `lpdump`-derived super partition and group sizes.
- `out/fw/SM-S901B_EUX/kernel/`: extracted stock boot chain images.
- `out/fw/SM-S901B_EUX/vendor/` and `vendor_dlkm/`: native hardware configurations and modules.
- `out/odin/SM-S901B_EUX/.downloaded`: downloaded firmware release marker.

Use `scripts/r0s/inspect_extracted_firmware.sh` only after a separately authorised extraction exists. The script compares the two release markers (if both are present), source SDK, stock boot-image SHA256, and extracted dynamic partition geometry against the **provisional** Android 15-derived figures in `target/r0s/config.sh`. It reports candidate fstab locations and module names, but does not produce a qualified recovery fstab or boot image.

Without an extraction, the inspector intentionally refuses to run. GitHub Actions uses only `scripts/ci/test_r0s_firmware_inspector.sh` with generated **synthetic files**.

Example for a future already-existing local extraction (not necessary now):

```bash
bash scripts/r0s/inspect_extracted_firmware.sh out/fw/SM-S901B_EUX
```

## Recovery device references and unresolved gap

Modern LineageOS Exynos 2200 common device source:
https://github.com/LineageOS/android_device_samsung_s5e9925-common/blob/lineage-23.2/configs/init/fstab.s5e9925

That fstab documents block paths including `/dev/block/by-name/boot`, `/dev/block/by-name/vendor_boot`, `/dev/block/by-name/dtbo`, `/dev/block/by-name/recovery`, and multiple logical partitions. It is an **AOSP/Lineage reference**, not proof of Samsung One UI 8's recovery mount semantics.

Older TWRP Exynos 2200 common device tree:
https://github.com/milxnaq/android_device_samsung_s5e9925/blob/android-12.1/recovery.fstab

This older fstab does not establish current Android 16 compatibility.

UN1CA's `scripts/utils/install_utils.sh` expects `target/r0s/installer/recovery.fstab` or `platform/exynos2200/installer/recovery.fstab` when resolving nonlogical targets. A **provisional block-locator file** now exists under `target/r0s/installer/recovery.fstab`, sourced only from modern LineageOS Exynos 2200 mapping references. It is not Samsung native A16 recovery evidence; real recovery and production OTA remain **BLOCKED**, and the `E3099` installer abort stays in place. See `docs/r0s/RECOVERY_OTA_STAGE.md`.

## Promotion requirements

1. Obtain and verify the A16 Samsung FOTA triplet, Odin AP/BL/CP/CSC archive components and extracted image hashes.
2. Use UN1CA's extracted `os_partitions_metadata.txt` to confirm actual super geometry.
3. Extract matching stock A16 recovery/vendor boot fstab, compare with device-level references and verify installer mount paths.
4. Confirm matched stock A16 kernel, DTBO, vendor_boot, modules and compatible recovery.
5. Complete ROM and real-board qualification before removing the installer abort.

**No host, ROM, kernel, recovery or BOARD PASS is claimed in this document.**
