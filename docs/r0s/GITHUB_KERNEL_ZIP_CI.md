# UN1CA A16 r0s — one GitHub kernel build pipeline

Branch: `sixteen-r0s-kernel-ci`. Stable `sixteen-r0s` unchanged.

## Proven cloud compilation

The previously pinned A16 ExtremeKRNL `build.sh -m r0s -k` completed successfully
in [Actions run 38706744894](https://github.com/t3st0st3r0n4s/UN1CA/actions/runs/38706744894).
No replacement kernel builder was introduced.

- ExtremeKRNL: `78f891e1d3cfbd8095bebdc6cb51f5c80cc52d95` (v2.5 / 5.10.269)
- KernelSU Next: the newest **stable GitHub Release** of `KernelSU-Next/KernelSU-Next`, resolved once per workflow run to its immutable commit (built-in `CONFIG_KSU=y`). At the 15 October 2026 upgrade: **v3.4.2**, commit `4c706b5938665866ebe16944a481a7b91e3396af`.

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
   `ExtremeKRNL-v2.5_r0s_KSUNext-<resolved-release>_<build-date>.zip`,
   SHA256SUMS and provenance **as an Actions artifact**, not a GitHub Release.

Commands unchanged in the original host production path.
The cloud-specific path avoids needing or inventing a full ROM workdir
or synthetic GZH3 firmware extraction marker.

**Qualification:** the cloud **compiler** has passed once; the
reconciliation → AVB → canonical packaging integration has been committed
but is not host/board-qualified until a complete new Actions run succeeds.
Even then **A16 physical boot and KSU/runtime remains BOARD DEFERRED**.
Do not flash based solely on an Actions green check.

## Reuse compilation automatically

There is **one** workflow; the compiler cache is keyed by the unchanged ExtremeKRNL source commit, **resolved KernelSU Next commit**, and runner environment. Updating KernelSU automatically creates a new cache entry.

- **Cache hit** for pinned ExtremeKRNL/KernelSU + runner environment: skip `build.sh`,
  reconcile and package directly.
- **Cache miss** (including first run or GitHub cache eviction): run the original
  `build.sh -m r0s -k` **once**, save `build/out/r0s` and `out/.config`
  immediately, and continue reconciliation/packaging.
- A failed packaging step does **not** discard the saved compilation.
- An actual kernel/KernelSU source or compiler environment update requires
  a new cache key and one new compilation.

No permanent compiled-kernel Release, separate host seeding procedure,
or missing-asset failure. `workflow_dispatch` and the explicit
`ci_inputs/r0s_a16_kernel_ci.run` marker trigger builds, not ordinary
packaging-script commits. Keep the native GZH3 donor Release unchanged.

## Manual run

```bash
gh workflow run r0s-kernel-zip.yml \
  --repo t3st0st3r0n4s/UN1CA \
  --ref sixteen-r0s-kernel-ci
```

No changes to A15 TachyonOS or to the stable A16 branch.
