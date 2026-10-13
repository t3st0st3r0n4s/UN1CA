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
