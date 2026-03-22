#!/usr/bin/env bash
#
# setup.sh — Write first-boot config files to a Raspberry Pi OS boot partition.
#
# Usage:
#   sudo ./setup.sh <config_file> <boot_mount>
#
# Example:
#   sudo ./setup.sh config/rpi4b_8gb.conf /mnt/boot
#
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <config_file> <boot_mount>"
    echo "  config_file  Path to a .conf file (see config/rpi4b_8gb.conf)"
    echo "  boot_mount   Path to the mounted boot partition"
    exit 1
fi

CONFIG_FILE="$1"
BOOT="$2"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: config file not found: $CONFIG_FILE"
    exit 1
fi

if [ ! -d "$BOOT" ]; then
    echo "Error: boot mount directory not found: $BOOT"
    exit 1
fi

# Source the config
# shellcheck source=config/rpi4b_8gb.conf
source "$CONFIG_FILE"

# --- SSH ---
if [ "${SSH_ENABLED:-false}" = "true" ]; then
    touch "$BOOT/ssh"
    echo "SSH enabled"
else
    rm -f "$BOOT/ssh"
    echo "SSH disabled"
fi

# --- WiFi ---
if [ "${WIFI_ENABLED:-false}" = "true" ]; then
    cat > "$BOOT/wpa_supplicant.conf" <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=${WIFI_COUNTRY:-US}

network={
    ssid="${WIFI_SSID}"
    psk="${WIFI_PASSWORD}"
}
EOF
    echo "WiFi configured for SSID: ${WIFI_SSID}"
fi

# --- User ---
if [ -n "${USER_PASSWORD_HASH:-}" ]; then
    echo "${USER_NAME:-pi}:${USER_PASSWORD_HASH}" > "$BOOT/userconf.txt"
    echo "User '${USER_NAME:-pi}' configured"
else
    echo "No password hash set — skipping userconf.txt"
fi

# --- config.txt ---
CONFIG_TXT="$BOOT/config.txt"
# Start fresh section at the end, or create the file
{
    if [ -f "$CONFIG_TXT" ]; then
        cat "$CONFIG_TXT"
    fi
} > "$CONFIG_TXT.tmp"

# Helper: set or append a key=value in config.txt
update_config_key() {
    local key="$1" value="$2"
    if grep -q "^${key}=" "$CONFIG_TXT.tmp" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$CONFIG_TXT.tmp"
    else
        echo "${key}=${value}" >> "$CONFIG_TXT.tmp"
    fi
}

if [ "${ARM_64BIT:-true}" = "true" ]; then
    update_config_key "arm_64bit" "1"
fi
update_config_key "gpu_mem" "${GPU_MEM:-76}"
if [ "${ENABLE_UART:-false}" = "true" ]; then
    update_config_key "enable_uart" "1"
fi

# Append extra config lines
if [ -n "${EXTRA_CONFIG:-}" ]; then
    echo -e "$EXTRA_CONFIG" >> "$CONFIG_TXT.tmp"
fi

mv "$CONFIG_TXT.tmp" "$CONFIG_TXT"
echo "config.txt updated"

# --- firstrun.sh ---
cat > "$BOOT/firstrun.sh" <<FIRSTRUN
#!/bin/bash
set -o errexit
set -o nounset

CURRENT_HOSTNAME=\$(cat /etc/hostname | tr -d " \\t\\n\\r")
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname "${HOSTNAME}"
else
    echo "${HOSTNAME}" >/etc/hostname
    sed -i "s/127.0.1.1.*\$CURRENT_HOSTNAME/127.0.1.1\\t${HOSTNAME}/g" /etc/hosts
fi

if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_locale "${LOCALE:-en_US.UTF-8}" "${KEYBOARD_LAYOUT:-us}"
else
    if [ -f /etc/default/locale ]; then
        sed -i "s/LANG=.*/LANG=${LOCALE:-en_US.UTF-8}/" /etc/default/locale
    else
        echo "LANG=${LOCALE:-en_US.UTF-8}" >/etc/default/locale
    fi
fi

rm -f /etc/localtime
echo "${TIMEZONE:-UTC}" >/etc/timezone
dpkg-reconfigure -f noninteractive tzdata

CMDLINE=/boot/firmware/cmdline.txt
if [ -f "\$CMDLINE" ]; then
    sed -i "s| systemd.run=.*||g" "\$CMDLINE"
fi
rm -f /boot/firmware/firstrun.sh
exit 0
FIRSTRUN
chmod +x "$BOOT/firstrun.sh"
echo "firstrun.sh created (hostname=${HOSTNAME})"

# --- cmdline.txt ---
CMDLINE="$BOOT/cmdline.txt"
if [ -f "$CMDLINE" ]; then
    EXISTING=$(cat "$CMDLINE")
else
    EXISTING=""
fi

FIRSTRUN_PARAMS="systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target"
if ! echo "$EXISTING" | grep -q "systemd.run="; then
    echo "${EXISTING} ${FIRSTRUN_PARAMS}" | sed 's/^ //' > "$CMDLINE"
    echo "cmdline.txt updated with firstrun trigger"
else
    echo "cmdline.txt already has systemd.run — skipping"
fi

echo ""
echo "Done! Boot partition files written to ${BOOT}"
