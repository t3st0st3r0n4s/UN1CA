#!/system/bin/sh
# STAGED ONLY — NOT INSTALLED IN ANY UN1CA PARTITION.
# Derived from TachyonOS r0s-fyi3's proven v3.4.1 one-shot installer.
PAYLOAD="/system/etc/unica/ksunext/manager_payload.bin"
TEMP="/data/local/tmp/.unica_ksunext_manager.apk"
MARKER="/data/local/tmp/.unica_ksunext_manager_33333_installed"

# Exactly one automatic install per manager release for the lifetime of /data.
# If deliberately uninstalled later, do not reinstall on each subsequent boot.
[ -f "$MARKER" ] && exit 0
[ -r "$PAYLOAD" ] || exit 1

/system/bin/rm -f "$TEMP"
/system/bin/cp "$PAYLOAD" "$TEMP" || exit 1

if /system/bin/pm install -r "$TEMP"; then
    /system/bin/rm -f "$TEMP"
    : > "$MARKER"
    exit 0
fi

/system/bin/rm -f "$TEMP"
exit 1
