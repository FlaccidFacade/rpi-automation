#!/usr/bin/env bash
#
# run.sh - End-to-end Raspberry Pi provisioning workflow.
#
# Flow:
# 1) Resolve profile (argument or interactive selector)
# 2) Resolve IMAGE and DEVICE (from profile.env or prompt)
# 3) Run flash.sh
# 4) Mount boot partition and run setup.sh
#
# Usage:
#   sudo ./run.sh [profile]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIGS_DIR="$SCRIPT_DIR/configs"
DEFAULT_IMAGE_URL="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2025-12-04/2025-12-04-raspios-trixie-arm64-lite.img.xz"

PROFILE_NAME="${1:-}"
PROFILE_DIR=""
PROFILE_ENV=""

IMAGE=""
IMAGE_URL=""
DEVICE=""
BOOT_PARTITION=""

MOUNT_DIR=""

cleanup() {
	if [ -n "$MOUNT_DIR" ] && mountpoint -q "$MOUNT_DIR"; then
		umount "$MOUNT_DIR" || true
	fi
	if [ -n "$MOUNT_DIR" ] && [ -d "$MOUNT_DIR" ]; then
		rmdir "$MOUNT_DIR" || true
	fi
}
trap cleanup EXIT

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
	echo "Error: run this as root (e.g. sudo ./run.sh [profile])."
	exit 1
fi

resolve_profile_dir() {
	local arg="$1"

	if [ -z "$arg" ]; then
		echo ""
		return 0
	fi

	if [ -d "$CONFIGS_DIR/$arg" ]; then
		echo "$CONFIGS_DIR/$arg"
		return 0
	fi

	if [ -d "$arg" ]; then
		echo "$(cd "$arg" && pwd)"
		return 0
	fi

	return 1
}

if [ -n "$PROFILE_NAME" ]; then
	if ! PROFILE_DIR="$(resolve_profile_dir "$PROFILE_NAME")"; then
		echo "Error: profile not found: $PROFILE_NAME"
		echo "Expected directory: $CONFIGS_DIR/<profile>"
		exit 1
	fi
	PROFILE_NAME="$(basename "$PROFILE_DIR")"
else
	PROFILE_NAME="$("$SCRIPT_DIR/select-profile.sh")"
	PROFILE_DIR="$CONFIGS_DIR/$PROFILE_NAME"
fi

if [ ! -d "$PROFILE_DIR" ]; then
	echo "Error: resolved profile directory does not exist: $PROFILE_DIR"
	exit 1
fi

PROFILE_ENV="$PROFILE_DIR/profile.env"
if [ -f "$PROFILE_ENV" ]; then
	# shellcheck disable=SC1090
	source "$PROFILE_ENV"
fi

# Pull values from profile.env if set there.
IMAGE="${IMAGE:-}"
IMAGE_URL="${IMAGE_URL:-$DEFAULT_IMAGE_URL}"
DEVICE="${DEVICE:-}"
BOOT_PARTITION="${BOOT_PARTITION:-}"

if [ -z "$IMAGE" ]; then
	read -r -p "Image file path: " IMAGE
fi

# Image paths are treated as relative to this script unless absolute.
if [[ "$IMAGE" != /* ]]; then
	IMAGE="$SCRIPT_DIR/$IMAGE"
fi

if [ ! -f "$IMAGE" ]; then
	if [[ "$IMAGE" == *.xz ]]; then
		if ! command -v curl >/dev/null 2>&1; then
			echo "Error: image file not found and curl is not installed: $IMAGE"
			exit 1
		fi
		mkdir -p "$(dirname "$IMAGE")"
		echo "Image not found at $IMAGE"
		echo "Downloading: $IMAGE_URL"
		curl -fL --progress-bar "$IMAGE_URL" -o "$IMAGE"
	else
		echo "Error: image file not found: $IMAGE"
		exit 1
	fi
fi

if [ -z "$DEVICE" ]; then
	echo "Available block devices:"
	lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,HOTPLUG,MODEL | awk 'NR==1 || $3=="disk"'
	echo ""
	read -r -p "Target device (e.g. /dev/sdb): " DEVICE
fi
if [ ! -b "$DEVICE" ]; then
	echo "Error: target is not a block device: $DEVICE"
	exit 1
fi

echo "Selected profile: $PROFILE_NAME"
echo "Image: $IMAGE"
echo "Device: $DEVICE"
echo ""

"$SCRIPT_DIR/flash.sh" "$IMAGE" "$DEVICE"

if [ -z "$BOOT_PARTITION" ]; then
	case "$DEVICE" in
		*mmcblk*|*nvme*) BOOT_PARTITION="${DEVICE}p1" ;;
		*) BOOT_PARTITION="${DEVICE}1" ;;
	esac
fi

echo "Waiting for boot partition node: $BOOT_PARTITION"
for _ in $(seq 1 20); do
	if [ -b "$BOOT_PARTITION" ]; then
		break
	fi
	sleep 1
done

if [ ! -b "$BOOT_PARTITION" ]; then
	echo "Error: boot partition not found: $BOOT_PARTITION"
	echo "Tip: set BOOT_PARTITION in $PROFILE_ENV if your layout differs."
	exit 1
fi

BOOT_SOURCE="$PROFILE_DIR"

MOUNT_DIR="$(mktemp -d)"
mount "$BOOT_PARTITION" "$MOUNT_DIR"

"$SCRIPT_DIR/setup.sh" "$MOUNT_DIR" "$BOOT_SOURCE"

sync
echo "Provisioning complete for profile: $PROFILE_NAME"
