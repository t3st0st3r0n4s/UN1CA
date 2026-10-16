# KernelSU Next reuse plan — UN1CA sixteen-r0s

Status: **STAGED / INACTIVE / NOT ANDROID-16 QUALIFIED**.

## Proven donor, not a fork parent

TachyonOS `r0s-fyi3` delivered KernelSU Next v3.4.1 and a working
manager installation lifecycle on Android 15. Its two small scripts were
audited directly from the GitHub source:

- `unica/mods/preload/system/etc/tachyon/install_manager.sh`
- `unica/mods/preload/system/etc/init/tachyon_manager.rc`

The installer copies a pinned manager payload to `/data/local/tmp`, calls
`pm install -r` once, and records a per-release marker **only after success**.
A deliberate later uninstall should not resurrect the manager at each boot.

The former `preload/customize.sh` downloaded an APK from an exact v3.4.1
release URL and checked SHA256 `f41778ee812512ae96bf53e7265114de5e0414bc5cb92397f49e1052d77da118`.
The APK **is not committed**, and the current UN1CA Android 16 preload
implementation is untouched.

## Staged UN1CA adaptation

- `staging/r0s/ksunext/install_manager.sh`: same installer lifecycle but
  future location `/system/etc/unica/ksunext`, not `/etc/tachyon`.
- `staging/r0s/ksunext/unica_ksunext_manager.rc`: retained
  `exec_background u:r:ksu:s0` design; **not loaded by init**.
- `staging/r0s/ksunext/manifest.env`: manager URL, SHA256, A15
  kernel/KernelSU source pins for provenance and explicit A16=false flags.
- `scripts/ci/check_r0s_ksu_staging.sh`: syntax, provenance and inactive
  integration guards. No Android runtime simulation or active module.

This folder is outside UN1CA's `platform/*/patches`, `target/*/patches`,
and `unica/mods` module runners. The manager is therefore **not included in
ROM output**. No active Android init or SELinux policy was changed.

## Promotion to active r0s support — blocked

1. Identify exact matched Samsung S901B A16 kernel source and extracted
   boot/vendor_boot/dtbo + vendor kernel module ABI.
2. Port KernelSU Next to that source, pin commit and needed patch SHA, build
   and verify host image/module compatibility. **Do not reuse A15 binaries.**
3. Validate `u:r:ksu:s0` SELinux domain and init `exec_background` on A16.
4. Verify manager artifact release SHA256 again and the appropriate package
   installer permissions, metadata and one-shot install behavior.
5. Only after A16 kernel + ROM HOST PASS promote the staged files into a
   dedicated `r0s` device module. Physical board validation must confirm
   boot, enforcing SELinux, manager install and root before publication.
6. Never overwrite UN1CA's current generic `unica/mods/preload` while
   integrating; preserve the upstream Samsung Internet preload behavior.

A15 kernel evidence:

- ExtremeKRNL commit `9ac30b43ebf74a607bf778d479609ab7ccf0797b`
- KernelSU Next source pin `8f902aeb16033024143ae36cf711df902cf02fae`
- Compatibility patch: `platform/exynos2200/patches/extremekrnl/ksunext-v3.4.0-compat.patch`
  in TachyonOS `r0s-fyi3`. **Not imported**: only qualified with the A15 kernel.

`scripts/ci/check_r0s_ksu_staging.sh` proves *staging boundaries*, not
an Android 16 runtime implementation. the normal UN1CA installer
contains no test-only abort.
