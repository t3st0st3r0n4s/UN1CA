# Existing TachyonOS TWRP reuse — UN1CA r0s Android 16

**Decision:** Use the actual recovery already installed on the user's
SM-S901B, inherited from working TachyonOS FYI3. No new TWRP source tree,
recovery compilation, direct recovery repartitioning or forced installation
of a second recovery. Preserve the current FYI3 binary-I (18) unlocked
bootloader and existing recovery; do not flash GZH3 binary-O bootloader.

## Two different recovery TAR filenames — check recovery payload identity

The [TachyonOS r0s-fyi3 repo](https://github.com/t3st0st3r0n4s/TachyonOS/tree/r0s-fyi3/TWRP)
retains `TWRP/S901B_twrp_vbmeta_only.tar`. Its GitHub blob identity
(SHA-1 including Git blob header) is
`9a164f92b09cd7975e8c1341b11ea5e01abd3b94`, size 67,174,400 bytes.
The [TWRP install guide](https://github.com/t3st0st3r0n4s/TachyonOS/blob/r0s-fyi3/TWRP/INSTALL.md)
identifies this as the bundled S901B TWRP + vbmeta installation archive.

Earlier UN1CA audits and the real FYI3 TWRP updater-launch probe used
`~/android/S22-ROM/S901B_twrp_logo_vbmeta.tar` with SHA256
`f82b9612d92786971609895facb703906744d9a617e673f1cd148e671735d830`.
**Different TAR names/hashes do not establish whether their internal
`recovery.img` bytes match.** The `up_param.bin` boot logo and
`vbmeta.img` may differ even when TWRP itself is identical.

`scripts/r0s/audit_tachyon_twrp_reuse.py` compares the SHA256 of
each TAR's *embedded recovery.img* while verifying the TachyonOS TAR's
actual pinned Git blob and the already-audited previous candidate's
SHA256. It never extracts an image to be flashed and does not require
TWRP sources. If their inner recovery images differ, keep the installed,
already device-tested recovery; do NOT assume the GitHub TAR was tested.

The earlier TAR-comparison script is an **optional forensic audit only**.
It is **not** a prerequisite for the kernel-only updater. The user's
successful TachyonOS A15 kernel ZIP flash on 2026-10-10 is already
accepted as the recovery-use evidence, and the missing local TachyonOS
archive path is not a ROM/kernel blocker.

## Physical compatibility *already* established

The project's [OTA host packaging and TWRP probe log](OTA_HOST_PACKAGING.md)
records 2026-10-13 on-device use of the *existing installed TWRP*:
- The user installed the tiny `original one-off TWRP dummy probe`;
- TWRP successfully invoked the **same AArch64 statically linked
  UN1CA update-binary** bundled into the existing host-only OTA;
- The deliberate test-only abort returned Error 1;
- The user confirmed normal boot back into working TachyonOS afterwards.

Therefore *updater launch* and the prior device's basic recovery function
are not outstanding questions. Do not invalidate these results by requiring
another TWRP tree or a speculative new Android 16 recovery binary.

## How UN1CA is already aligned to TWRP

UN1CA's `target/r0s/installer/recovery.fstab` is **an updater-script block
locator map**, not an instruction to reconfigure the installed recovery.
Its five native GZH3 EROFS logical partitions are
`system`, `vendor`, `product`, `odm`, `vendor_dlkm`, with no
independent `system_ext`.

`scripts/utils/install_utils.sh` generates `map_partition("name")`
for these logical partitions; the existing
`scripts/internal/build_full_ota_zip.sh` builds a full OTA with:
- `update_dynamic_partitions(...)` and `unsparse_super_empty.img`
  metadata;
- `block_image_update(map_partition(...), ...)` on those five partitions;
- Direct package extraction to `/dev/block/by-name/boot`,
  `vendor_boot`, and `dtbo` for the boot chain;
- Original model assertion before any partition operation.

These block-image updates operate on the logical block device; the
recovery itself **does not need to mount those partitions as EROFS**.
The previously observed TWRP recovery fstab covers only 1/5 native
GZH3 EROFS mount declarations, but this is a *filesystem UI/mount
limitation*, **not proof of an incompatibility with the block updater**.
Do NOT change the Android 16 ROM back to ext4 or replace its native
EROFS boot/fstab solely to match the older TWRP's mounting options.
The GZH3 native EROFS early-boot fstab must be preserved.

## Outstanding, narrowly scoped compatibility qualifications

What is **still unverified on the physical phone** is execution of the
`update_dynamic_partitions` and five `block_image_update` calls,
particularly vendor_dlkm, with its current TWRP kernel and device-mapper.
The one-off dummy probe intentionally tested none of those writes.
Likewise GZH3/ExtremeKRNL boot on the FYI3 retained bootloader, AVB trust,
module/KMI and rollback remain separate; no existing evidence grants a
normal A16 boot PASS.

**Kernel-only maintenance is distinct from full-ROM installation.**
For the kernel-only case, follow the proven TachyonOS ExtremeKRNL ZIP:
the original ExtremeKRNL update-binary plus **boot.img, vendor_boot.img,
and dtbo.img only**. No full-ROM legacy block updater, no vendor_dlkm
block write and no new recovery tree.

The existing installed A16 vendor_dlkm modules must already match the
replacement kernel's ABI (and relevant symbol CRCs); this is why the
user's documented A15 upgrade needed no vendor_dlkm rewrite. If this
condition fails for a future KSU/kernel upgrade, stop the 3-image ZIP
path rather than silently adding a logical partition update.

The UN1CA GZH3 kernel ZIP builder now implements the same five-member
ExtremeKRNL recovery package layout, using the GZH3-reconciled signed
boot chain. The A16 on-device runtime gate remains open,
but **A15 recovery qualification must not be repeated**.

Do not flash TWRP, vbmeta, an A16 ROM, or an unqualified kernel ZIP while
the bootloader/rollback qualification remains open.
