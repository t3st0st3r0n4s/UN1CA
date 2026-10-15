# UN1CA A16 r0s — GitHub Actions kernel build (experimental branch)

Branch: `sixteen-r0s-kernel-ci`, **forked from stable `sixteen-r0s`**.
Not based on the abandoned LKM experiment.

## Purpose

Run the **existing, pinned ExtremeKRNL A16** `build.sh -m r0s -k`
in a disposable GitHub-hosted Ubuntu runner and publish a kernel build ZIP
without recompiling on the user's Ubuntu laptop.

- Source: `milxnaq/android_kernel_samsung_s5e9925@78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95`
- Built-in KernelSU Next: `KernelSU-Next/KernelSU-Next@8f902aeb16033024143ae36cf711df902cf02fae` (**v3.4.1**, `CONFIG_KSU=y`)
- No `kernelsu.ko` conversion, no reimplementation of the original kernel build or ZIP updater.
- The workflow downloads only its own small helper from the triggering Git commit,
  avoiding a full checkout of the large UN1CA ROM repository.
- Uses the upstream kernel's own packaging of boot, vendor_boot, dtbo and the
  compiled vendor modules.
- The standard public GitHub-hosted Linux runner has 4 CPUs/16 GiB RAM/14 GiB
  free storage before reclaiming preinstalled toolchains. The workflow
  cleans the **ephemeral GitHub runner only** and refuses to build below a 24 GiB
  free-space gate. Actual runner capacity and build completion **not yet verified**.

## Why CI's first ZIP is intentionally NOT flashable

The upstream ExtremeKRNL `vendor_boot.img` contains its own first-stage
fstab/ramdisk that was previously found **incompatible with native GZH3
EROFS vendor/product/odm/vendor_dlkm layouts**. Our installed-UN1CA-A16 ZIP
must instead come from the **already implemented GZH3 reconciliation,
ROM-integration, signed target-files packaging path**:

- `scripts/r0s/reconcile_extremekrnl_gzh3_a16.py`
- `scripts/r0s/integrate_extremekrnl_a16.py`
- `scripts/r0s/package_extremekrnl_update_a16.py`

Those steps currently require native firmware / hybrid workdir and signed
target-files available only on the host, not in GitHub. It is incorrect to
substitute the *raw upstream* ZIP for that final A16 artifact.

To prevent accidental flashing, CI **preserves all three original upstream
images and updater binary** but prefixes E3099 to the updater-script. It
publishes the locked, explicitly named
`UN1CA-A16-E3099-UNRECONCILED-ExtremeKRNL-*_r0s_KSU_*.zip` plus
`provenance.json` and `NOT_FOR_FLASH.txt`.

The ZIP is for evaluating cloud kernel compilation and KSU version provenance.
It is not a KSU update for an installed A16 ROM, not signed or GZH3-reconciled,
and does not modify `vendor_dlkm` or the existing A16 ROM.

## GitHub Actions operation

The `A16 r0s ExtremeKRNL kernel ZIP (HOST ONLY)` workflow runs automatically
on changes to its **isolated experiment branch** and supports manual dispatch
once GitHub exposes the workflow. Successful runs publish an Actions artifact
(never an automatically published release) with the E3099-locked ZIP and
SHA256/module evidence. A GitHub Actions `success` result means only source
build and ZIP structure, **not** boot or module ABI board qualification.

If a standard runner cannot fit the build, the workflow fails with a
capacity diagnosis instead of silently using a different kernel version.
A larger runner or separate build infrastructure would then be needed.

No changes to stable `sixteen-r0s`, no A15 work, no device flashing, and no
modifications to existing E3099-protected ROM installation paths.


## Host reference upload → GitHub five-entry ZIP parity (2026-10-15)

**This is NOT yet a new-version cloud kernel-to-flashable-ZIP pipeline.**
The original 13 October signed/reconciled ZIP is the immutable reference.
The successful 15 October GitHub build proved cloud kernel compilation; its
unreconciled vendor_boot is NOT substituted into the host-signed images.
Repackaged reference images carry their original hashes. No boot signing keys
or complete firmware/ROM/target-files ZIP are uploaded.

Host command (run from the current **`sixteen-r0s-kernel-ci` checkout**):

```bash
cd ~/android/UN1CA
git fetch origin sixteen-r0s-kernel-ci
git switch sixteen-r0s-kernel-ci
git pull --ff-only origin sixteen-r0s-kernel-ci
python3 scripts/r0s/ci_upload_kernel_reference.py
python3 scripts/r0s/ci_upload_kernel_reference.py --publish
```

**Important:** this switches the *host source checkout* to the experimental
branch. No existing `out/` bytes are rewritten. With local uncommitted
source edits, `git switch` may refuse; do not force it.

Uploader verifies:
- Exact 13 October original ZIP filename; SHA-256 against companion
  `.provenance.json` and the pinned A16 kernel/KSU source commits
- Original ExtremeKRNL update-binary and updater-script Git blob SHA-1
- Three exact partition-sized signed boot images, byte-equal to the retained
  `out/r0s_A16_GZH3_HOST_ONLY-target_files.zip` (whole archive SHA-256
  `4f5088ee40af3fb386cb134e7efea6be0c096349800f7d7f8697670542f51f5a`)
- Exactly five recovery updater entries and correct partition destinations

Upon `--publish`, the host uses the authenticated `gh` CLI to create a
**PUBLIC pre-release** asset named:
`r0s-a16-kernel-reference-v1`.
It then commits **only a JSON checksum manifest** under
`ci_inputs/a16_kernel_reference.json` on the experiment branch,
triggering `.github/workflows/r0s-kernel-reference-zip.yml`.
**The public release contains the proprietary-derived signed boot chain**:
confirm you're willing to publish this file before invoking `--publish`.
Never upload private keys, EFS, entire firmware packages or super images.

The new GitHub workflow downloads that exact public asset, verifies its
SHA-256, verifies the three full partition hashes and exact upstream updater,
and reassembles the canonical
`ExtremeKRNL-v2.5_r0s_KSUNext-v3.4.1_<timestamp>.zip` with unchanged
five member payloads. It publishes the Actions artifact as
`UN1CA-A16-GZH3-REFERENCE-ZIP-NOT-BOARD-QUALIFIED`, never a public
flash-ready Release. The separately successful cloud-compiled Image is
**not** embedded; provenance states `uses_new_cloud_compiled_kernel=false`.

**Next technical step for native cloud-only updates:** use the uploaded native
GZH3 boot metadata/ramdisks as *donor*, substitute the newly compiled
ExtremeKRNL `Image`, DTB, module ramdisk and DTBO, and repeat the original
A16 verification/signing process with exact retained test-key policy. Check
vendor_dlkm CRC ABI against the installed A16 set. Until that pipeline
passes, the reference repackage must not be mistaken for a newly built
or device-qualified kernel update.
