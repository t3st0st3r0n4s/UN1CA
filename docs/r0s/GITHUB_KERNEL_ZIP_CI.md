# UN1CA A16 r0s — one GitHub kernel build pipeline

Branch: `sixteen-r0s-kernel-ci`. Stable `sixteen-r0s` unchanged.

## Proven cloud compilation

The pinned A16 ExtremeKRNL `build.sh -m r0s -k` completed successfully
in [Actions run 38706744894](https://github.com/t3st0st3r0n4s/UN1CA/actions/runs/38706744894).
No replacement kernel builder was introduced.

- ExtremeKRNL: `78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95` (v2.5 / 5.10.269)
- KernelSU Next: `8f902aeb16033024143ae36cf711df902cf02fae` (v3.4.1, **built-in**)

## Permanent GZH3 donor images

Public Release: [r0s-a16-gzh3-donors-v1](https://github.com/t3st0st3r0n4s/UN1CA/releases/tag/r0s-a16-gzh3-donors-v1).

| File | Exact bytes | SHA-256 |
| --- | ---: | --- |
| `boot.img` | 29,704,192 | `55d86a13ae72768023961c8f05ed3eec0f3b4486da3e7a081b848b1e89355ad3` |
| `vendor_boot.img` | 24,961,024 | `5901c98df36a8c11204a7e0e579f2824e24c133640e15b0b605de076901101c0` |

CI downloads both exact files and verifies the pinned
`ci_inputs/r0s_a16_gzh3_donors.sha256` manifest on every run.
They retain **native GZH3 headers, EROFS first-stage ramdisk and bootconfig**.
Their old kernel and vendor module ramdisk are replaced from the **newly
compiled** source. No `recovery.img`, full stock firmware, large ROM tree,
entire target-files ZIP or Git LFS assets are needed.

## Canonical workflow

1. Clone exact pinned kernel + KernelSU and run original upstream
   `build.sh -m r0s -k`.
2. Invoke the **existing** `scripts/r0s/reconcile_extremekrnl_gzh3_a16.py`
   with `--ci-donors`. Only its input gate differs from host mode;
   original repacking and structural verification are shared.
3. Invoke the **existing** `scripts/r0s/package_extremekrnl_update_a16.py`
   with `ci-build` and `ci-verify`. Uses the host's same
   `SIGN_IMAGE_WITH_AVB` hash-footer parameters and public UN1CA test key.
   Carries the **original** ExtremeKRNL `update-binary` and
   `updater-script`, unchanged.
4. Check all five compiled modules are present and verify the
   module/version structure in the reconciler. Record module SHA-256
   for diagnostics only; compiler-dependent module hashes are **not**
   equality gates. The kernel-only ZIP does not update `vendor_dlkm`.
5. Upload canonical-format
   `ExtremeKRNL-v2.5_r0s_KSUNext-v3.4.1_<build-date>.zip`,
   SHA256SUMS and provenance **as an Actions artifact**, not a GitHub Release.

Commands unchanged in the original host production path.
The cloud-specific path avoids needing or inventing a full ROM workdir
or synthetic GZH3 firmware extraction marker.

**Qualification:** the cloud **compiler** has passed once; the
reconciliation → AVB → canonical packaging integration has been committed
but is not host/board-qualified until a complete new Actions run succeeds.
Even then **A16 physical boot and KSU/runtime remains BOARD DEFERRED**.
Do not flash based solely on an Actions green check.

## Reuse compilation

A pinned GitHub Actions cache stores `build/out/r0s` and the compiled
`.config` immediately after successful kernel compilation, **before** any
reconciliation/packaging failure. A cache hit skips `build.sh`.

Automatic push triggers are deliberately limited to a single explicit
`ci_inputs/r0s_a16_kernel_ci.run` marker; changing packaging scripts does
not trigger 30–40 minute compilations. The cache key changes only when the
kernel/KSU sources or relevant compiler environment changes.

## Packaging-only default — no repeated compilation

Changes to scripts **do not trigger the expensive workflow**.
Manual runs now default to `rebuild_kernel=false`. The runner uses its
pinned Actions cache, or downloads the retained host compilation Release.
If neither is present, it fails rather than compiling automatically.
Only explicitly selecting `rebuild_kernel=true` starts a kernel rebuild.

**One-time seed from existing successful October 13 host build**
(no recompilation, no entire ROM tree):

```bash
cd ~/android/UN1CA
(
  cd out/kernel_tmp-exynos2200
  tar -czf ../r0s-a16-compiled-v3.4.1.tar.gz \
    out/.config \
    build/out/r0s/boot.img \
    build/out/r0s/vendor_boot.img \
    build/out/r0s/dtb.img \
    build/out/r0s/dtbo.img \
    build/out/r0s/modules/lib/modules/{fingerprint,fingerprint_sysfs,input_booster_lkm,sec_debug_coredump,wlan}.ko \
    build/out/r0s/ExtremeKRNL-*_r0s_KSU_*.zip
)
gh release create r0s-a16-extremekrnl-v2.5-ksunext-v3.4.1-compiled \
  out/r0s-a16-compiled-v3.4.1.tar.gz \
  --repo t3st0st3r0n4s/UN1CA --target sixteen-r0s-kernel-ci \
  --prerelease --title "A16 r0s pinned compiled kernel v3.4.1" \
  --notes "Previously compiled ExtremeKRNL v2.5 / built-in KSU Next v3.4.1; input for experimental package-only CI. No device qualification."
```

This is a public Release asset containing compiled firmware binaries, not private
keys or EFS. It need only be uploaded once. Subsequent packaging changes
reuse the compiler cache; updating the actual kernel/KSU sources still
requires **one explicitly requested** new build.

## Manual run

```bash
gh workflow run r0s-kernel-zip.yml \
  --repo t3st0st3r0n4s/UN1CA \
  --ref sixteen-r0s-kernel-ci
```

No changes to A15 TachyonOS or to the stable A16 branch.
