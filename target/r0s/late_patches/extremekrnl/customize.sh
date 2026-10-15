SKIPUNZIP=1
# Target-only late patch. Never run before UN1CA fs/proca modifications.
if [[ "$TARGET_CODENAME" != "r0s" || "$TARGET_PLATFORM" != "exynos2200" ]]; then
    ABORT "Wrong device/platform for Android 16 ExtremeKRNL"
    return 1
fi
LOG "- Integrating pinned GZH3/ExtremeKRNL hybrid with KernelSU Next"
UN1CA_R0S_LATE_PATCH=1 PATH="$SRC_DIR/out/tools/bin:$PATH" \
    python3 "$SRC_DIR/scripts/r0s/integrate_extremekrnl_a16.py" --apply || return 1

LOG "- Adding manager for the selected KernelSU Next build"
UN1CA_R0S_LATE_PATCH=1 PATH="$SRC_DIR/out/tools/bin:$PATH" \
    python3 "$SRC_DIR/scripts/r0s/install_ksunext_manager_a16.py" --apply || return 1
