"""SD card flashing logic for Raspberry Pi OS images."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Mountpoints that must never be part of the target device.
_CRITICAL_MOUNTS: frozenset[str] = frozenset({"/", "/boot", "/home", "/usr", "/var"})


def _get_mountpoints(device: dict) -> list[str]:
    """Recursively collect non-None mountpoints from a lsblk device dict."""
    points: list[str] = []
    mp = device.get("mountpoint")
    if mp:
        points.append(mp)
    for child in device.get("children", []):
        points.extend(_get_mountpoints(child))
    return points


def list_block_devices() -> list[dict]:
    """
    Return a list of disk-type block devices reported by ``lsblk``.

    Each entry contains: ``name``, ``size``, ``model``, ``vendor``,
    ``hotplug``, and ``mountpoints``.
    """
    result = subprocess.run(
        [
            "lsblk",
            "--json",
            "--output",
            "NAME,SIZE,TYPE,MOUNTPOINT,HOTPLUG,MODEL,VENDOR",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    devices: list[dict] = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") == "disk":
            devices.append(
                {
                    "name": f"/dev/{dev['name']}",
                    "size": dev.get("size", ""),
                    "model": (dev.get("model") or "").strip(),
                    "vendor": (dev.get("vendor") or "").strip(),
                    "hotplug": bool(dev.get("hotplug", False)),
                    "mountpoints": _get_mountpoints(dev),
                }
            )
    return devices


def validate_device(
    device_path: str,
    allow_non_removable: bool = False,
) -> tuple[bool, str]:
    """
    Validate that *device_path* is safe to flash.

    Returns a ``(is_valid, reason)`` tuple.  When *is_valid* is ``False``,
    *reason* contains a human-readable explanation.
    """
    if not os.path.exists(device_path):
        return False, f"Device {device_path} does not exist"

    if not device_path.startswith("/dev/"):
        return False, f"{device_path} does not look like a block device path"

    try:
        devices = list_block_devices()
    except subprocess.CalledProcessError as exc:
        return False, f"Failed to list block devices: {exc}"

    device_info: Optional[dict] = next(
        (d for d in devices if d["name"] == device_path), None
    )
    if device_info is None:
        return False, f"Device {device_path} not found in block device list"

    conflicts = set(device_info["mountpoints"]) & _CRITICAL_MOUNTS
    if conflicts:
        return (
            False,
            f"Device {device_path} is mounted at critical path(s): "
            + ", ".join(sorted(conflicts)),
        )

    if not allow_non_removable and not device_info["hotplug"]:
        return (
            False,
            f"Device {device_path} does not appear to be removable. "
            "Use --allow-non-removable to override.",
        )

    return True, "OK"


def flash_image(
    image_path: Path,
    device_path: str,
    block_size: str = "4M",
) -> None:
    """
    Flash *image_path* to *device_path* using ``dd``.

    Calls ``sync`` after writing to flush kernel buffers.
    Requires root privileges.
    """
    logger.info("Flashing %s to %s …", image_path, device_path)
    subprocess.run(
        [
            "dd",
            f"if={image_path}",
            f"of={device_path}",
            f"bs={block_size}",
            "status=progress",
            "conv=fsync",
        ],
        check=True,
    )
    subprocess.run(["sync"], check=True)
    logger.info("Flash complete")
