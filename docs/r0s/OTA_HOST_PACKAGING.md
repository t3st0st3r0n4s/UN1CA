# UN1CA r0s GZH3: single ZIP host packaging

## Standard UN1CA ROM packaging — 13 October 2026

The **current** retained target-files ZIP is
`out/r0s_A16_GZH3_HOST_ONLY-target_files.zip`, SHA256
`4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a`.
The previously generated locked full ROM
`UN1CA_r0s_A16_GZH3_FINAL_E3099_LOCKED.zip`
(SHA256 `4f092fde076296c7950d92b77e078431ed0c84f595395bc1cdbf46deb74c81fe`)
is **not installable**. It is preserved as existing host evidence.

No kernel, ROM workdir or target-files rebuild is needed. UN1CA's existing
`scripts/build_flashable_zip.sh` remains the only actual OTA builder.
The r0s-only, explicit `--installable` option in
`scripts/r0s/build_full_ota_guarded.py` omits only the pinned E3099
abort from the generated updater. The existing SM-S901B assertion and all
five logical plus three raw images stay intact. Default mode remains
E3099-locked. The signed installable ZIP is a **device-unqualified
candidate**, not a proven bootable ROM.

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
python3 scripts/r0s/build_full_ota_guarded.py --self-test
python3 scripts/r0s/build_full_ota_guarded.py --installable   # space/identity preflight
python3 scripts/r0s/build_full_ota_guarded.py --installable --build
python3 scripts/r0s/build_full_ota_guarded.py --installable --verify
```

The new output uses UN1CA's **original** convention:
`UN1CA_<version>_<YYYYMMDD>_r0s[-sign].zip`, deriving the
version, date and device from retained target-files build metadata and
the optional `-sign` suffix from UN1CA's signing configuration.
No stage labels are added to the normal ZIP filename.
Commands do not touch the phone; they require substantial free disk.
The built ZIP is **not safe to flash merely because E3099 is absent**:
GZH3/ExtremeKRNL boot on the retained unlocked FYI3 binary-I bootloader,
vendor module loading, normal Android/SELinux and rollback from A16 are
not device-qualified. The user's BL/CP/TWRP/vbmeta preservation policy
remains unchanged.

Historical sections below document the previous E3099-locked build and
must not be interpreted as the current final packaging pin.


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

## Next: actual updater versus existing S901B TWRP (read-only)

Run this against the completed 6.09 GB ZIP and the **same existing** pinned
S901B TWRP TAR as the earlier host recovery audits:

```sh
cd ~/android/UN1CA
python3 scripts/r0s/audit_ota_updater_twrp.py
```

The script hashes the full ZIP, confirms its E3099 abort precedes writes,
extracts **only the already packaged** update-binary in temporary host storage,
and verifies that it equals the exact UN1CA updater prebuilt. It checks the
ELF architecture, embedded edify function-name hints, interpreter and direct
shared-library names in the existing TWRP ramdisk. It never invokes the
updater, boots recovery or accesses the phone. This is a *compatibility
inventory*, not proof that a binary will execute or that kernel dm/super
operations will function at runtime. Missing libraries or linker are
reported explicitly, without inventing a new TWRP requirement.

The agreed I(18) FYI3 bootloader stays untouched and the single integrated
ROM ZIP remains E3099-locked. Do **not** flash during this stage.

## Actual signed-OTA updater versus existing TWRP — host PASS (2026-10-13)

The developer ran `python3 scripts/r0s/audit_ota_updater_twrp.py`
on the Ubuntu host against the finished locked GZH3 ZIP (SHA-256
`4200d8239a5243021cdcf7396b0bab4f0dda944f5dc4e1893ffd189c4df9e022`)
and the pinned existing S901B TWRP TAR.

Observed results:

- Packaged `META-INF/com/google/android/update-binary` SHA-256:
  `28378c9dcae8a0e6035e5f90e66c2a128eab3cce2982e43aa33424542507664a`.
  It matched the upstream UN1CA bundled updater byte-for-byte.
- ELF64 / AArch64; **no interpreter and no external NEEDED libraries**;
  statically linked/self-contained. No dependency on TWRP-shipped libc.
- Updater contains named entry-point hints
  `update_dynamic_partitions`, `block_image_update` and `map_partition`.
- `TWRP_OTA_LINKER_PATH_PRESENT=true` and
  `TWRP_MISSING_DIRECT_LIB_NAMES=none`; these are vacuous dependency
  compatibility successes for a static binary, **not** evidence of
  successful TWRP updater invocation.
- `E3099-FIRST CONFIRMED` before any partition-write expressions.
  Host check did not reboot, flash, modify phone, or write BL/CP/recovery.

**Disposition:** Actual embedded updater **host static-ABI PASS**.
No updater-library blocker. Recovery execution, mapped dynamic partition
updates and boot of GZH3 A16 on the retained FYI3 bootloader are still
**DEVICE UNVERIFIED**; E3099 remains installed. Next avoid more parallel
installer architectures and do not rebuild the ZIP. A bounded TWRP
runtime qualification is the remaining updater test, and independently
the A16 kernel/AVB/normal-boot qualification remains mandatory.

## Non-writing TWRP updater-launch probe

The prior full-OTA updater ABI test was a host-only static PASS.
The next test checks actual TWRP updater invocation without offering
the complete A16 ROM to TWRP.

Run on host: `python3 scripts/r0s/make_twrp_abort_probe.py`.
It extracts the byte-identical actual updater from the SHA-pinned
UN1CA OTA, packages that updater alongside an immediate E3099 abort
script, and permits **exactly two ZIP members**.
The probe has no partition-image payloads, ZIP install hooks or
dynamic partition writing commands. The full ROM remains unchanged.

Once the probe has been generated, when convenient boot the existing
TWRP. Copy only this small probe ZIP to the device (e.g. ADB push
to `/tmp` while the device is in TWRP), select it in TWRP Install.
An E3099 error and failed install is the expected **probe PASS**.
Never test by installing the 6 GB GZH3 full ROM ZIP.
If TWRP signature verification rejects this unsigned probe before
launching the updater, record this as inconclusive, not an ABI error.
The installer UI may update recovery logs; abort-only edify does
not write to BL, CP, boot, super or any other partition.

This is a separate tiny diagnostic, **not an alternative ROM or
another installation stage**. Confirm TachyonOS still boots afterwards.
A result still does not qualify runtime update_dynamic_partitions,
block_image_update, GZH3 normal boot, AVB or RIL, and E3099 remains
mandatory for the real UN1CA package.

## Physical FYI3 TWRP E3099-only updater launch — DEVICE PASS (2026-10-13)

User invoked `r0s_TWRP_E3099_ABORT_ONLY_probe.zip` using the
**already-installed S901B TWRP**. The on-screen log reported:

```
Full SELinux support is present.
MTP Enabled
Installing zip file
Unmounting System...
E3099: UN1CA sixteen-r0s is under development and NOT qualified for flashing.
Updater process ended with ERROR: 1
Updating partition details...
...done
```

**EXPECTED PASS**: TWRP launched the actual UN1CA `update-binary`
included byte-identically in the probe, parsed the script and returned
its deliberate `E3099` abort. Error 1 is intentional. Recovery
"Unmounting System" is preparatory state management, not a flash.

Probe contents are only two files (updater ELF and immediate abort);
there is no ROM payload, dynamic operation list or kernel image, and
no probe-specified partition writing. The working FYI3 bootloader was
not targeted. Return to normal TachyonOS boot should be confirmed
separately.

**Gate updated:** old-TWRP *updater-launch* runtime PASS. The full
`update_dynamic_partitions` / `block_image_update` functionality
and EROFS normal-boot experience remain UNTESTED. So do GZH3 kernel,
vendor modules, AVB, radio, SELinux and Android 16 board boot.
Keep E3099 in the actual integrated UN1CA OTA. Do NOT flash it.

## Actual device reboot after abort-only probe — PASS (2026-10-13)

The user confirmed that after the E3099-only real TWRP updater-launch
test, the S901B rebooted **normally into working TachyonOS FYI3**.
Thus the previous recovery-ABI probe is closed with device-level
TWRP updater invocation PASS and **normal original-ROM boot PASS**.
No kernel, super partition or Samsung bootloader write was exercised.
The real UN1CA 6 GB package remains E3099-locked.

Next focused gate: **read the already-installed FYI3 vbmeta partition
without modifying it** and inspect its AVB flags/descriptors using
the existing host `avbtool`. This can characterize AVB policy on
the actual unlocked phone; it cannot prove GZH3 kernel acceptance.
Stock GZH3 test-key signatures have already passed their host gate,
as have exact PROCA-only kernel delta and all five stock vendor
module identity/vermagic checks. Do not repeat them or rebuild the
ROM. Keep FYI3 Samsung bootloader, CP and recovery untouched.
