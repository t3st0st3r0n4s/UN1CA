# sixteen-r0s source integration policy

Base: `salvogiangri/UN1CA` `sixteen` at `ce12c6e077fc1865e574873f316c450cdf587bd2`.

- `UN1CA` remains the upstream identity, build system, framework code, ROM modules, installer and CI foundation.
- Do not merge ExtremeROM's abandoned `sixteen` branch history into UN1CA or copy outdated framework patches.
- The new `platform/exynos2200` and `target/r0s` carry **only** the minimum device support; native Samsung Android 16 S901B components are authoritative initially.
- No Android 15 ExtremeKRNL, KernelSU binary, vendor `.ko`, DTBO, Bluetooth APEX, ArcSoft replacement, MIDAS or encryption patch should be copied without a demonstrated Android 16 mismatch.
- Reuse UN1CA's `paradigm`, `knoxpatch`, CSC, settings, OTA packaging and firmware extraction as-is until a precise `r0s` issue is identified.
- Existing TachyonOS `r0s-fyi3` is a **read-only reference**, not this branch's parent.
- Do not modify a public firmware source without an exact pinned version and source hash evidence.
- Do not enable full-build CI or remove the installer abort before host and device evidence is recorded.
- Upstream merges must be reviewed for product-feature, Android API and signing changes.

## Evidence gates

1. CI-generated target configuration (`CONFIG PASS`).
2. Exact Android 16 source release and extracted stock S901B files, SHA256 evidence (`FW PASS`).
3. Native A16 boot/vendor_boot/dtbo/kernel/modules ABI, bootloader/partition geometry (`KERNEL HOST PASS`).
4. Android 16 target-files generation with no unvetted cross-device patches (`ROM HOST PASS`).
5. Controlled full OTA/recovery, clean/dirty data implications, SELinux and Android device tests (`BOARD PASS`).

Current state: `CONFIG PREPARED / HOST UNVERIFIED / BOARD DEFERRED`.
