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
