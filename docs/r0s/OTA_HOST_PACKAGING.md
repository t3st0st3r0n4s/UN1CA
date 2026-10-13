# UN1CA r0s GZH3: single ZIP host packaging

Current stage: host target-files complete. This step uses the upstream
`scripts/build_flashable_zip.sh` full-OTA builder against the existing
`out/r0s_A16_GZH3_HOST_ONLY-target_files.zip` (pinned SHA-256
`6c20d013b7f3087e08fe453d5eb10fcf9411107898c98705b6f8b30347a9b8fd`).

Output after successful --build:
`out/UN1CA_r0s_A16_GZH3_E3099_BLOCKED_full_ota.zip`.
This is **one integrated** UN1CA ROM archive; it is not two-stage.
The ZIP contains the five GZH3 logical partitions and
`boot.img`, `vendor_boot.img`, `dtbo.img`.
Samsung BL, CP, recovery and vbmeta are not packaged.

Both modes require source file and SHA pin, exact target-files image
layout and the unchanged unconditional E3099 installation abort.
The builder preserves the existing target-files archive and does
not run `make_rom.sh`, build the kernel, access ADB, flash or wipe.

Usage on the Ubuntu host:

```bash
cd ~/android/UN1CA
python3 scripts/r0s/build_full_ota_guarded.py
# Only when precheck passes and free disk is sufficient:
python3 scripts/r0s/build_full_ota_guarded.py --build
```

The storage precheck estimates the substantial temporary space required
by the stock UN1CA packaging pipeline, including a 6 GiB reserve.
An insufficient-capacity result means do not build, not that GZH3 ROM
is invalid. Never delete the working TachyonOS build/backups automatically.

After packaging the inspector checks real updater-script ordering:
`E3099` must precede partition writes; `update_dynamic_partitions` and
all five `block_image_update` calls must exist. It checks group_basic
geometry, 5 logical mappings, three boot images, the absence of
bootloader/modem/vbmeta/recovery payloads and complete ZIP CRC.

The result is **HOST-ONLY / NOT FLASH APPROVED**. E3099 prevents
installation; TWRP runtime compatibility and GZH3 boot/AVB behaviour
with the retained TachyonOS FYI3 unlocked bootloader remain unproven.
Rollback to TachyonOS is a separate recovery option, not part of UN1CA.

## Actual host full-OTA result — 2026-10-13

The developer ran `scripts/r0s/build_full_ota_guarded.py --build`
after its precheck passed. The wrapper invoked the standard UN1CA
`scripts/build_flashable_zip.sh` and `scripts/internal/build_full_ota_zip.sh`
from the existing pinned GZH3 target-files archive; no ROM rebuild.
All five images were converted to block OTA dat payloads and compressed;
updater-script and OTA metadata generated; the ZIP signed.

Retained local host artifact (not uploaded to GitHub):

- `out/UN1CA_r0s_A16_GZH3_E3099_BLOCKED_full_ota.zip`
- Size: `6087623915` bytes (5.67 GiB).
- SHA-256: `4200d8239a5243021cdcf7396b0bab4f0dda944f5dc4e1893ffd189c4df9e022`
- Source target-files SHA-256: `6c20d013b7f3087e08fe453d5eb10fcf9411107898c98705b6f8b30347a9b8fd`.
- Real output inspector: `UN1CA single-ZIP layout and E3099-FIRST updater checks PASS`.
- Five logical partitions, boot/vendor_boot/dtbo included; no BL, CP,
  recovery or vbmeta payload. Full ZIP CRC passed (builder output).
- Stage: **HOST OTA PASS / BOARD UNTESTED / E3099 INSTALL ABORT ACTIVE**.

**Next development work is not another build.** The unchanged existing
FYI3 bootloader and TWRP must be qualified for this actual UN1CA legacy
block OTA and GZH3 kernel/runtime. No flash should be attempted using
this E3099-locked ZIP; changing the bootloader is excluded by policy.
