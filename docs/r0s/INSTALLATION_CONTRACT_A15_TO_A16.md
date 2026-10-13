# TachyonOS FYI3 A15 -> UN1CA GZH3 A16: S901B installation contract

Status 2026-10-13: HOST target-files validated; PHONE BOOTCHAIN NOT QUALIFIED.
Keep E3099 abort in target/r0s/installer/assertions.edify. NO flashing, BL
upgrade, A16 stock installation, recovery replacement, userdata wipe or
automatic downgrade recommendation.

## Fixed development policy: retain bootloader and reversible firmware

**User-approved direction (2026-10-13):** Keep the installed, unlocked
TachyonOS/FYI3 **Samsung bootloader at binary I (18)**. The UN1CA Android 16
port must operate with that retained bootloader; **no Samsung bootloader
upgrade or binary O (24) dependency is permitted** in this development
route. Upstream LineageOS 23.2 SM-S901B Android 16 installation instructions
specify FYI3 firmware as a baseline, supporting the approach at the
Android-version level. This does not independently qualify GZH3-on-FYI3
kernel/AVB runtime.

**Rollback requirement:** preserve a supported return to working TachyonOS
FYI3 by restoring its matched boot/vendor_boot/dtbo, five logical
partitions and any necessary vbmeta/recovery configuration, with existing
EFS backups protected. Do not rely on bootloader downgrading; the bootloader
is deliberately never advanced. Android user data may require a wipe or
independent backup restore on a return from A16; preservation of userdata
is **not** guaranteed. A writeable/full rollback package and recovery
procedure must be verified before the A16 installer is enabled.

**Implementation outcome:** If GZH3 boot/kernel/vendor cannot work on the
retained I bootloader, adjust the ROM firmware/boot-chain approach or use an
earlier compatible A16 source. Do **not** solve that by upgrading the
bootloader. Treat CP/AVB/recovery compatibility as specific remaining
engineering checks, not a reason to restart generic phone audits.

## Verified Android 16 firmware at the EXISTING bootloader revision

**Key finding (Samsung release history and EUX archive):** Samsung released
SM-S901B **Android 16 / One UI 8** as `S901BXXUIGYI7` with **bootloader
binary I (18)**, the same rollback revision as the working TachyonOS FYI3
`S901BXXSIFYI3`. Therefore **Android 16 itself does not require an O (24)
bootloader**. GZH3's `O` describes the revision of the matching Samsung
*stock GZH3 bootloader package*, not a proven minimum requirement of all
A16 kernels/vendor images.

Primary historical and firmware evidence:
- https://doc.samsungmobile.com/SM-S901B/021718220304/eng.html
- https://samfirm.shop/build/S901BXXUIGYI7
- https://s-update.samsungvn.com/devices/SM-S901B

**Project decision:** retain the known-working unlocked FYI3 BL (binary I)
during development. Keep GZH3 as the most-progressed native A16 ROM source,
using stock Android 16 GYI7 (also binary I) as the **low-level firmware
compatibility reference**. Before any ROM installation, establish whether
GZH3's newer kernel, vendor_boot, DTBO and vendor need a firmware change
beyond binary-I capability. Matching binary-I numbering does NOT prove
TachyonOS's *exact* FYI3 bootloader bytes are identical to GYI7 nor that
FYI3 BL boots unmodified GZH3 images.

**Do not flash** GYI7 stock or GZH3 BL as a shortcut. One UI 8 has
bootloader-unlocking restrictions and preservation of the existing
unlocked state is not established for this S901B. Neither full stock A16
preinstallation nor an O-revision rollback jump is currently a justified
prerequisite. Compare FYI3/GYI7/GZH3 BL/CP details only as needed to
resolve this exact compatibility boundary; do not restart generic
Android property surveys or port from scratch.

## Firmware components and required versions

| Component | Existing TachyonOS FYI3 baseline | UN1CA GZH3 ROM installer action | Release requirement |
| --- | --- | --- | --- |
| S901B model | SM-S901B/r0s proven by TachyonOS build and prior on-device work | r0s only | preserve device identity and unlocked bootloader |
| BL bootloader / TZ | FYI3 RP I=18; confirm actual live RP | NOT INCLUDED | retained BL must demonstrably boot GZH3 kernel, OR compatible later BL proven safe with unlocked state preserved |
| CP radio modem | existing A15 CP; live baseband pending | NOT INCLUDED | existing CP must work with GZH3 vendor RIL/IMS, or explicitly qualified CP migration |
| vbmeta / AVB | existing patched/trusted boot configuration | NOT INCLUDED | A16 boot, dtbo, vendor_boot images actually accepted; development AVB key does not equal Samsung production trust |
| recovery | Existing S901B TWRP, used for TachyonOS/kernel installation | NOT INCLUDED | validate this recovery with the legacy UN1CA block installer, not a new recovery build by default |
| boot | TachyonOS ExtremeKRNL 5.10.238, built-in KSU Next v3.4.1, board-tested | REPLACED: GZH3 PROCA-delta kernel 5.10.237 | GZH3 normal boot, matched vendor module ABI; Android 15 kernel not directly reusable |
| vendor_boot | older A15 | REPLACED: GZH3-derived EROFS fstab | header/init/SELinux with retained BL accepted |
| dtbo | older A15 | REPLACED: native GZH3 | device-tree and boot firmware compatibility |
| system | A15 | REPLACED: GZH3-derived EROFS | native 5 logical images; group_basic |
| vendor | A15 | REPLACED: GZH3-derived EROFS | compatibility with BL / CP / device hardware |
| product, odm, vendor_dlkm | A15 | REPLACED: GZH3-derived EROFS | packaged exact 5-image geometry, vendor module provenance |
| userdata | encrypted FYI3 | NOT INCLUDED | complete Format Data on FIRST UN1CA installation once all gates clear |
| EFS / sec_efs / cpefs | retained | NOT INCLUDED | maintain verified backups and exact return path |

## Known TachyonOS evidence — do not restart device discovery

Actual starting ROM is [TachyonOS r0s-fyi3](https://github.com/t3st0st3r0n4s/TachyonOS/tree/r0s-fyi3),
not unmodified Samsung FYI3. Its [build and validation record](https://github.com/t3st0st3r0n4s/TachyonOS/blob/r0s-fyi3/docs/r0s-fyi3-build.md)
specifies:

- Target Samsung FYI3 `S901BXXSIFYI3/S901BOXMIFYI3/S901BXXSIFYI3/S901BXXSIFYI3`,
  Android 15/API 35; donor software S721B BYH1. Firmware-based target,
  with donor software changes, is not an unknown generic A15 image.
- Kernel boot, vendor_boot, dtbo are from ExtremeKRNL pin
  `9ac30b43ebf74a607bf778d479609ab7ccf0797b`;
  native A15 `5.10.238-ExtremeKRNL-Nexus-2200-v1+`.
- Built-in KernelSU Next v3.4.1 pin
  `8f902aeb16033024143ae36cf711df902cf02fae`.
  TachyonOS documentation reports real kernel boot, SELinux enforcing,
  root and five kernel-module loads PASS. This is A15 evidence, not A16 evidence.
- TWRP exists and was used to flash the working A15 kernel recovery ZIP.
- EFS/SEC_EFS/CPEFS backups and kernel rollback evidence are already retained
  from the TachyonOS development workflow.

**Do not require re-running the generic `audit_install_prerequisites.py`
script as a prerequisite to further engineering.** It can serve as an
optional read-only pre-flash snapshot, but cannot establish GZH3 bootloader
compatibility, radio firmware requirements or unlock preservation.
The productive next research task is a focused **FYI3 vs GZH3 BL/CP/vbmeta
and recovery-installer transition** analysis, reusing archived TachyonOS
results instead of repeatedly discovering model/kernel/root state.

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

B. EXCLUDED: advancing the bootloader from FYI3 binary I to GZH3 binary O
or any other revision is outside the agreed reversible installation path.
If the newer bootloader is necessary, rework the Android 16 boot/kernel
firmware combination rather than making that upgrade a prerequisite.

C. If the retained-I path cannot be qualified, retain HOST-only status
or rebase/adapt to compatible Android 16 firmware. Never require a bootloader
upgrade that breaks the agreed TachyonOS FYI3 recovery route.

## Measurable release gates

- G0 SOURCE/HOST PASS: Native GZH3 5-way super, boot-chain images,
  ZIP CRC, module provenance, packaging capacity and E3099 abort.
- G1 BASELINE ALREADY ESTABLISHED FROM TACHYONOS: model, Android 15 API 35,
  FYI3 target pin, rooted/unlocked development workflow, recovery and
  v3.4.1 kernel boot/module load are documented and previously tested.
  Only the exact currently installed low-level BL/CP revisions and
  Download Mode OEM LOCK/RP state merit a fresh pre-flash cross-check.
- G2 BOOTLOADER HARD BLOCK: real GZH3 (or adapted Android 16) boot-chain
  compatibility with the **retained TachyonOS FYI3 bootloader**. BL upgrade
  is not an accepted alternative.
- G3 CP AND AVB HARD BLOCK: native GZH3 vendor RIL/modem operation,
  AVB/rollback, FBE/metadata behavior.
- G4 RECOVERY HARD BLOCK: known compatible legacy OTA update-binary
  invocation, group_basic mapping and five logical block updates.
- G5 FIRST INSTALL/RETURN: full external backups, qualified TachyonOS FYI3
  restore including ROM and matched boot-chain images, and Format Data if
  required. No promise of preserving userdata across A16 -> A15.
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

## Implementation priority — firmware transition, not generic property audits

1. Compare known TachyonOS/FYI3 original BL, CP, vbmeta and recovery
   provenance with native S901B GZH3 release images and the new
   UN1CA ZIP's write set. Identify whether A16 kernel and TrustZone
   demand a BL upgrade on S901B.
2. Confirm the retained-I bootloader / native GZH3 startup combination
   using device-specific technical evidence; do not infer compatibility
   from a host parser. If no reliable safe validation route is available,
   keep deployment blocked and investigate firmware-compatible adaptation.
3. Independently review old TWRP legacy OTA block protocol and
   GZH3 super partition op list without modifying the device.
4. Only then decide whether to require selected firmware updates,
   a modified installation package or an updated recovery.

The previously created generic ADB baseline audit is optional. It
must not be portrayed as a new requirement to identify a phone we
already ported and qualified under TachyonOS A15.

## Immediate reversible-install prerequisite: FYI3 TachyonOS recovery ZIP

TachyonOS `r0s-fyi3` source `scripts/internal/build_flashable_zip.sh`
already generates an updater that (subject to what is present in the
selected ROM package) writes the full dynamic logical partition group
and `boot`, `vendor_boot`, `dtbo`. A separate new A15 rollback
flasher is not presently required; first select a **known-good retained
TachyonOS FYI3 ZIP**, together with the already-tested KernelSU v3.4.1
recovery kernel ZIP if the ROM rollback ZIP contains a different kernel.

The narrow read-only checker
`scripts/r0s/check_tachyon_rollback_zip.py` inventories *actual local*
TachyonOS archives for the five exact logical partitions, three raw
boot-chain images, correct legacy block OTA verbs, device firmware
assertion and absence of BL, CP, vbmeta/recovery overwrites. It reports
structural evidence only; it never installs anything. Missing or wrong
files are blockers. It deliberately does not decrypt/mount userdata.

From `~/android/UN1CA`:
```sh
python3 scripts/r0s/check_tachyon_rollback_zip.py
```
The default searches `~/android/tachyonos_s901b/out/` for
`TachyonOS_*_r0s*.zip`; explicit archive path(s) also work.
This is a one-time A15 rollback candidate check, **not another Android
device audit**. Once this is confirmed, next inspect the **UN1CA
GZH3 OTA write set** against those same five partitions and avoid any
bootloader changes. Do not remove E3099 or flash.
