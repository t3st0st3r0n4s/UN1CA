# UN1CA r0s GZH3 — full ROM OTA packaging

## Current implementation (16 October 2026)

The normal UN1CA full ROM installer has **no artificial development abort**.
The one-off TWRP updater-launch probe was a separate test archive, never a
requirement for installing the ROM.

Existing retained target-files archive:
`out/r0s_A16_GZH3_HOST_ONLY-target_files.zip`

SHA256: `4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a`

Reuse the original UN1CA OTA builder through the existing guarded wrapper,
without rebuilding the 11 GiB ROM workdir:

```bash
cd ~/android/UN1CA
python3 scripts/r0s/build_full_ota_guarded.py --self-test
python3 scripts/r0s/build_full_ota_guarded.py
python3 scripts/r0s/build_full_ota_guarded.py --build
python3 scripts/r0s/build_full_ota_guarded.py --verify
```

`--installable` remains accepted as a compatibility alias; both invocations
use the same normal installer. The output retains upstream UN1CA naming:
`UN1CA_<version>_<YYYYMMDD>_r0s[-sign].zip`.

The full OTA carries `system`, `vendor`, `product`, `odm`,
`vendor_dlkm`, `boot.img`, `vendor_boot.img`, and `dtbo.img`.
The installer retains the S901B assertion, dynamic-partition operations
and original updater binary. It does not flash BL, CP, recovery or vbmeta.

## Evidence and remaining qualification

- The earlier full-ROM OTA builder and source/updater structure completed
  host checks on 13 October 2026. Its initial non-installing development
  archive is historical, not the current packaging path.
- The one-off abort-only TWRP probe was launched successfully on the
  actual S901B. It established updater launch, **not** execution of the
  full-ROM block update.
- The custom ExtremeKRNL kernel ZIP separately uses the proven
  three-image TachyonOS updater; it is intended for a matching installed
  A16 ROM and does not replace `vendor_dlkm`.
- A16 boot, retained-bootloader compatibility, AVB/rollback, module loading,
  normal SELinux and the full TWRP block-update path remain BOARD-unverified.

There is no deliberate installation abort in either current package builder.
BOARD qualification is a separate runtime task, not an installer-source gate.
