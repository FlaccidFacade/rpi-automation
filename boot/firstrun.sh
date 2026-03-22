#!/bin/bash
# This script runs once on first boot, then removes itself.
# Edit the values below to match your setup.

set -o errexit
set -o nounset

HOSTNAME="raspberrypi"
LOCALE="en_US.UTF-8"
KEYBOARD="us"
TIMEZONE="UTC"

# --- Set hostname ---
CURRENT_HOSTNAME=$(cat /etc/hostname | tr -d " \t\n\r")
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname "$HOSTNAME"
else
    echo "$HOSTNAME" >/etc/hostname
    sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$HOSTNAME/g" /etc/hosts
fi

# --- Set locale ---
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_locale "$LOCALE" "$KEYBOARD"
else
    if [ -f /etc/default/locale ]; then
        sed -i "s/LANG=.*/LANG=$LOCALE/" /etc/default/locale
    else
        echo "LANG=$LOCALE" >/etc/default/locale
    fi
fi

# --- Set timezone ---
rm -f /etc/localtime
echo "$TIMEZONE" >/etc/timezone
dpkg-reconfigure -f noninteractive tzdata

# --- Clean up ---
CMDLINE=/boot/firmware/cmdline.txt
if [ -f "$CMDLINE" ]; then
    sed -i 's|[[:space:]]\+systemd.run=[^[:space:]]\+||g' "$CMDLINE"
fi
rm -f /boot/firmware/firstrun.sh
exit 0
