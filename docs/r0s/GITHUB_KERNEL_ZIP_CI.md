# UN1CA A16 r0s — cloud kernel build and GZH3 donor inputs

Branch: `sixteen-r0s-kernel-ci` only; stable `sixteen-r0s` unchanged.

## Confirmed build

GitHub Actions run [38706744894](https://github.com/t3st0st3r0n4s/UN1CA/actions/runs/38706744894) compiled the **exact upstream ExtremeKRNL A16** `build.sh -m r0s -k`, with built-in KernelSU Next v3.4.1. Source pins:

- ExtremeKRNL `78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95`
- KernelSU Next `8f902aeb16033024143ae36cf711df902cf02fae`

No new kernel-build system is needed.

## Persistent A16 boot-chain donors — upload once

The host's already GZH3-reconciled `out/target/r0s/work_dir/kernel/` has **two reusable donors**:

| File | Exact bytes | SHA-256 |
| --- | ---: | --- |
| `boot.img` | 29,704,192 | `55d86a13ae72768023961c8f05ed3eec0f3b4486da3e7a081b848b1e89355ad3` |
| `vendor_boot.img` | 24,961,024 | `5901c98df36a8c11204a7e0e579f2824e24c133640e15b0b605de076901101c0` |

These are **templates with the old compiled kernel/module fragment**; future builds must replace those components while retaining the native GZH3 ramdisks and boot metadata. **Never package these two donor files unchanged as a new KernelSU update.** `dtbo.img` comes from each compilation; `recovery.img` is unused.

Store both in a **GitHub Release**, tag `r0s-a16-gzh3-donors-v1`, not in Git history, without Git LFS.

One-time host upload:

```bash
cd ~/android/UN1CA
D=out/target/r0s/work_dir/kernel

# Verify exact recorded host identity before upload.
(cd "$D" && sha256sum -c   <(curl -fsSL https://raw.githubusercontent.com/t3st0st3r0n4s/UN1CA/sixteen-r0s-kernel-ci/ci_inputs/r0s_a16_gzh3_donors.sha256))
# For maximum portability run the checksums manually if the shell process
# substitution above is not supported by your shell.

gh auth status
gh release create r0s-a16-gzh3-donors-v1   "$D/boot.img" "$D/vendor_boot.img"   --repo t3st0st3r0n4s/UN1CA   --target sixteen-r0s-kernel-ci   --prerelease   --title "UN1CA A16 GZH3 boot-chain donors v1"   --notes "Permanent host-verified boot and vendor_boot template images for experimental kernel CI; contains Samsung-derived firmware material; not flashable."
```

This is a **public** Release because the UN1CA repository is public. Do not upload EFS, signing secrets, stock firmware archives or an entire ROM. Verify you are comfortable publishing the Samsung-derived image content.

CI downloads these two exact files *before compiling* and verifies their pinned SHA-256 from `ci_inputs/r0s_a16_gzh3_donors.sha256`, byte lengths and Android header magic; files are available under `out/target/r0s/work_dir/kernel/` in the ephemeral runner.

CI's current final archive is intentionally **E3099-locked/unreconciled**. Connecting cloud kernel output to the **already existing** `reconcile_extremekrnl_gzh3_a16.py`, AVB test-key signing, and `package_extremekrnl_update_a16.py` checks is a separate next step; the donor download gate does **not** qualify an A16 ZIP for flashing.

After uploading, rerun the existing `A16 r0s ExtremeKRNL kernel ZIP (HOST ONLY)` workflow manually (GitHub Actions UI or `gh workflow run r0s-kernel-zip.yml --repo t3st0st3r0n4s/UN1CA --ref sixteen-r0s-kernel-ci`).

**Removed:** previous reference-ZIP upload/repackage workflow and helpers; uploading the 13 October kernel ZIP would not produce a new cloud-built kernel update.
