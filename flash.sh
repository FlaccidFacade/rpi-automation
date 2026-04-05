#!/usr/bin/env bash
#
# flash.sh — Flash a Raspberry Pi OS image to an SD card.
#
# Usage:
#   sudo ./flash.sh <image_file> <device>
#
# Example:
#   sudo ./flash.sh 2024-11-19-raspios-bookworm-arm64-lite.img /dev/sdb
#   sudo ./flash.sh 2024-11-19-raspios-bookworm-arm64-lite.img.xz /dev/sdb
#
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <image_file> [device]"
    echo ""
    echo "  image_file  Path to a .img or .img.xz file"
    echo "  device      Target block device (e.g. /dev/sdb)"
    echo ""
    echo "Omit device to list available devices."
    exit 1
fi

IMAGE="$1"

if [ ! -f "$IMAGE" ]; then
    echo "Error: image file not found: $IMAGE"
    exit 1
fi

# No device specified — list available devices and exit
if [ $# -lt 2 ]; then
    echo "Available block devices:"
    echo ""
    lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,HOTPLUG,MODEL | awk 'NR==1 || $3=="disk"'
    echo ""
    echo "Pick a removable device and run:  sudo $0 $IMAGE /dev/sdX"
    exit 0
fi

DEVICE="$2"

if [ ! -b "$DEVICE" ]; then
    echo "Error: $DEVICE is not a block device"
    exit 1
fi

# Safety: refuse to write to devices mounted at critical paths
MOUNTS=$(lsblk -no MOUNTPOINT "$DEVICE" 2>/dev/null || true)
for CRITICAL in "/" "/boot" "/home" "/usr" "/var"; do
    if echo "$MOUNTS" | grep -qx "$CRITICAL"; then
        echo "Error: $DEVICE has a partition mounted at $CRITICAL — refusing to flash"
        exit 1
    fi
done

echo ""
echo "WARNING: This will ERASE ALL DATA on ${DEVICE}!"
echo "  Image : ${IMAGE}"
echo "  Target: ${DEVICE}"
echo ""
read -r -p "Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo "Flashing ${IMAGE} to ${DEVICE} ..."
if [[ "$IMAGE" == *.xz ]]; then
    if ! command -v xz >/dev/null 2>&1; then
        echo "Error: xz is required to flash .xz images but was not found in PATH"
        exit 1
    fi
    xz -dc -- "$IMAGE" | dd of="$DEVICE" bs=4M status=progress conv=fsync
else
    dd if="$IMAGE" of="$DEVICE" bs=4M status=progress conv=fsync
fi
sync
echo "Done! You can now remove the SD card."
