#!/usr/bin/env bash
#
# setup.sh — Copy boot files to a mounted Raspberry Pi OS boot partition.
#
# Edit the files in boot/ first, then run:
#   sudo ./setup.sh /mnt/boot
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOOT_DIR="$SCRIPT_DIR/boot"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <boot_mount>"
    echo "  Copies files from boot/ to the mounted boot partition"
    echo "  and adds the firstrun trigger to cmdline.txt."
    exit 1
fi

DEST="$1"

if [ ! -d "$DEST" ]; then
    echo "Error: $DEST is not a directory"
    exit 1
fi

cp -v "$BOOT_DIR/ssh"                 "$DEST/"
cp -v "$BOOT_DIR/wpa_supplicant.conf" "$DEST/"
cp -v "$BOOT_DIR/config.txt"          "$DEST/"
cp -v "$BOOT_DIR/userconf.txt"        "$DEST/"
cp -v "$BOOT_DIR/firstrun.sh"         "$DEST/"
chmod +x "$DEST/firstrun.sh"

# Append firstrun trigger to cmdline.txt if not already present
CMDLINE="$DEST/cmdline.txt"
TRIGGER="systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target"
if [ -f "$CMDLINE" ] && ! grep -q "systemd.run=" "$CMDLINE"; then
    sed -i "s|$| ${TRIGGER}|" "$CMDLINE"
    echo "Updated cmdline.txt"
fi

echo "Done."
