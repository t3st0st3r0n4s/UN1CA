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
