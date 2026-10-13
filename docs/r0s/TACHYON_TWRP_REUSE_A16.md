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

On the Ubuntu host, first fetch the UN1CA branch, then read-only:

```bash
cd ~/android/UN1CA
git pull --ff-only origin sixteen-r0s
python3 scripts/r0s/audit_tachyon_twrp_reuse.py --self-test
python3 scripts/r0s/audit_tachyon_twrp_reuse.py --source-only
python3 scripts/r0s/audit_tachyon_twrp_reuse.py \
  --tachyon-tar ~/android/tachyonos_s901b/TWRP/S901B_twrp_vbmeta_only.tar \
  --tested-tar ~/android/S22-ROM/S901B_twrp_logo_vbmeta.tar
```

If the actual TachyonOS checkout uses a different directory, pass that
existing file's location; there is no need to clone or rebuild TWRP.

## Physical compatibility *already* established

The project's [OTA host packaging and TWRP probe log](OTA_HOST_PACKAGING.md)
records 2026-10-13 on-device use of the *existing installed TWRP*:
- The user installed the tiny `r0s_TWRP_E3099_ABORT_ONLY_probe.zip`;
- TWRP successfully invoked the **same AArch64 statically linked
  UN1CA update-binary** bundled into the existing host-only OTA;
- The deliberate E3099 abort was printed and returned Error 1;
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
- Source installer `E3099` assertion before any operations.

These block-image updates operate on the logical block device; the
recovery itself **does not need to mount those partitions as EROFS**.
The previously observed TWRP recovery fstab covers only 1/5 native
GZH3 EROFS mount declarations, but this is a *filesystem UI/mount
limitation*, **not proof of an incompatibility with the block updater**.
Do NOT change the Android 16 ROM back to ext4 or replace its native
ER O FS boot/fstab solely to match the older TWRP's mounting options.
The GZH3 native EROFS early-boot fstab must be preserved.

## Outstanding, narrowly scoped compatibility qualifications

What is **still unverified on the physical phone** is execution of the
`update_dynamic_partitions` and five `block_image_update` calls,
particularly vendor_dlkm, with its current TWRP kernel and device-mapper.
The tiny E3099 abort probe intentionally tested none of those writes.
Likewise GZH3/ExtremeKRNL boot on the FYI3 retained bootloader, AVB trust,
module/KMI and rollback remain separate; no existing evidence grants a
normal A16 boot PASS.

Any true kernel-only installer must use the same **proven UN1CA block updater
path**, include matching vendor_dlkm data when changing the kernel ABI,
and preserve GZH3 vendor_boot native ramdisk00 and signed image layout.
The current `package_extremekrnl_update_a16.py` produces only an
E3099-locked, non-flashable development payload; it is not a second ROM
installer. No new TWRP build is a prerequisite.

Do not flash TWRP, vbmeta, an A16 ROM, or an unqualified kernel ZIP while
the E3099 and bootloader/rollback gates remain active.
