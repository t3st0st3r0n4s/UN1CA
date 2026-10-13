# FYI3 A15 -> GZH3 A16: S901B installation contract

Status 2026-10-13: HOST target-files validated; PHONE BOOTCHAIN NOT QUALIFIED.
Keep E3099 abort in target/r0s/installer/assertions.edify. NO flashing, BL
upgrade, A16 stock installation, recovery replacement, userdata wipe or
automatic downgrade recommendation.

## Firmware components and required versions

| Component | Current presumed FYI3 environment | UN1CA GZH3 ROM installer action | Release requirement |
| --- | --- | --- | --- |
| S901B model | S901B/r0s; live ADB must confirm | r0s only | exact model and unlocked Download Mode |
| BL bootloader / TZ | FYI3 RP I=18; confirm actual live RP | NOT INCLUDED | retained BL must demonstrably boot GZH3 kernel, OR compatible later BL proven safe with unlocked state preserved |
| CP radio modem | existing A15 CP; live baseband pending | NOT INCLUDED | existing CP must work with GZH3 vendor RIL/IMS, or explicitly qualified CP migration |
| vbmeta / AVB | existing patched/trusted boot configuration | NOT INCLUDED | A16 boot, dtbo, vendor_boot images actually accepted; development AVB key does not equal Samsung production trust |
| recovery | older TWRP | NOT INCLUDED | recovery runs legacy update-binary and block dynamic-partition installer safely |
| boot | older A15 | REPLACED: GZH3 PROCA-delta kernel | actual GZH3 normal boot, KMI/module loading |
| vendor_boot | older A15 | REPLACED: GZH3-derived EROFS fstab | header/init/SELinux with retained BL accepted |
| dtbo | older A15 | REPLACED: native GZH3 | device-tree and boot firmware compatibility |
| system | A15 | REPLACED: GZH3-derived EROFS | native 5 logical images; group_basic |
| vendor | A15 | REPLACED: GZH3-derived EROFS | compatibility with BL / CP / device hardware |
| product, odm, vendor_dlkm | A15 | REPLACED: GZH3-derived EROFS | packaged exact 5-image geometry, vendor module provenance |
| userdata | encrypted FYI3 | NOT INCLUDED | complete Format Data on FIRST UN1CA installation once all gates clear |
| EFS / sec_efs / cpefs | retained | NOT INCLUDED | maintain verified backups and exact return path |

## Concrete firmware values

- Existing previously reported build S901BXXSIFYI3, RP I = 18.
- Android 16 target S901BXXSOGZH3, RP O = 24, an advance of 6.
- GZH3 super partition size 11,744,051,200 B; group_basic capacity
  11,739,856,896 B; partitions system, vendor, product, odm, vendor_dlkm.
- Packaged HOST_ONLY target-files ZIP SHA-256:
  6c20d013b7f3087e08fe453d5eb10fcf9411107898c98705b6f8b30347a9b8fd.
- Current ZIP does NOT supply BL, CP, vbmeta, recovery or data formatting.
  UN1CA's full OTA code updates dynamic partitions and three boot images;
  the image package has passed host audits but is not a flashable OTA.
- Existing GZH3 stock recovery does not trust UN1CA development OTA signer.
  Custom recovery installation is upstream's supported initial method.
- The older TWRP has direct ELF dependencies present in ramdisk, while
  native EROFS mount coverage is 1/5. Its block updater capability remains
  untested; EROFS mounting != raw block image updating.

## Decision tree with strict pass criteria

A. PREFERRED DEVELOPMENT PATH: preserve current unlocked FYI3 BL and CP.
Require actual device evidence that native GZH3 boot/vendor_boot/dtbo
starts with the current BL and that CP+GZH3 vendor RIL/IMS, vbmeta/AVB
and the recovery installer function. The existing TWRP booting under
Android 15 is not evidence of GZH3 A16 boot. Until all are proven,
this route is NOT FLASH-APPROVED.

B. FALLBACK: if GZH3 requires a later BL, RP O=24 or intermediate version
may prohibit downgrade. Verify exact device Download Mode RP and prove
an already-unlocked SM-S901B remains unlockable/unlocked with that
specific BL BEFORE any BL write. Android 16 One UI 8 official updates
are known to remove OEM unlock ability; a previously unlocked phone's
exact behavior remains unproven. The firmware switch is not a harmless
software prerequisite. Without evidence it is an unacceptable route.

C. If neither A nor B qualifies, development must retain HOST-only
status or rebase to a demonstrably compatible native firmware.
Do not deploy a ROM whose required bootloader would eliminate the
ability to boot custom images on the S901B.

## Measurable release gates

- G0 SOURCE/HOST PASS: Native GZH3 5-way super, boot-chain images,
  ZIP CRC, module provenance, packaging capacity and E3099 abort.
- G1 LIVE BASELINE PENDING: ADB properties of bootloader, modem,
  sdk, model, vbmeta/unlock; Download Mode OEM LOCK and RP SWREV.
- G2 BOOTLOADER HARD BLOCK: real GZH3 boot-chain compatibility with
  retained A15 BL OR safe unlock-persistent updated BL, measured.
- G3 CP AND AVB HARD BLOCK: native GZH3 vendor RIL/modem operation,
  AVB/rollback, FBE/metadata behavior.
- G4 RECOVERY HARD BLOCK: known compatible legacy OTA update-binary
  invocation, group_basic mapping and five logical block updates.
- G5 FIRST INSTALL: full external backups; Format Data necessary.
- G6 BOARD: normal-boot, data, fingerprint, RIL/IMS, NFC, camera,
  vendor modules, enforcing policy/hardware functionality, recovery.
- Only after G0-G6 may someone review removing E3099 or issuing an
  installation package. Passing a command's syntax test != board PASS.

## Immediate read-only command

cd ~/android/UN1CA
python3 scripts/r0s/audit_install_prerequisites.py --self-test
python3 scripts/r0s/audit_install_prerequisites.py

Requires ONE already-online ADB device; does not ask for root or report
its serial, IMEI, IMSI or accounts. No device writes. Manual Download
Mode unlock/RP evidence is needed to finish the G1 baseline.

References:
https://github.com/salvogiangri/UN1CA/discussions/129
https://github.com/salvogiangri/UN1CA/discussions/130
https://github.com/salvogiangri/UN1CA/discussions/629
https://github.com/salvogiangri/UN1CA/discussions/132
https://doc.samsungmobile.com/SM-S901B/021718220304/eng.html
