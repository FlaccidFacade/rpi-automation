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
    echo "Usage: $0 <boot_mount> [boot_source_dir]"
    echo "  Copies files from boot_source_dir (or boot/) to the mounted boot partition"
    echo "  and adds the firstrun trigger to cmdline.txt."
    exit 1
fi

DEST="$1"
SOURCE_DIR="${2:-$BOOT_DIR}"

if [ ! -d "$DEST" ]; then
    echo "Error: $DEST is not a directory"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: boot source directory not found: $SOURCE_DIR"
    exit 1
fi

for FILE in ssh wpa_supplicant.conf config.txt userconf.txt firstrun.sh; do
    if [ -f "$SOURCE_DIR/$FILE" ]; then
        cp -v "$SOURCE_DIR/$FILE" "$DEST/"
    else
        echo "Skipping $FILE (not found in $SOURCE_DIR)"
    fi
done
if [ -f "$DEST/firstrun.sh" ]; then
    chmod +x "$DEST/firstrun.sh"
fi

# Append firstrun trigger to cmdline.txt if not already present
CMDLINE="$DEST/cmdline.txt"
TRIGGER="systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target"
if [ -f "$CMDLINE" ] && ! grep -q "systemd.run=" "$CMDLINE"; then
    sed -i "s|$| ${TRIGGER}|" "$CMDLINE"
    echo "Updated cmdline.txt"
fi

echo "Done."
