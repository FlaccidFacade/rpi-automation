#!/usr/bin/env python3
"""Flash a Raspberry Pi OS image to an SD card.

Requires root privileges (uses ``dd``).

Examples
--------
List available block devices::

    python3 flash_sd.py raspios.img

Flash to a specific device (interactive confirmation)::

    sudo python3 flash_sd.py raspios.img --device /dev/sdb

Flash non-interactively (CI/scripting)::

    sudo python3 flash_sd.py raspios.img --device /dev/sdb --yes
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pi_automation.flash import flash_image, list_block_devices, validate_device


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flash a Raspberry Pi OS image to an SD card",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to the Raspberry Pi OS image (.img)",
    )
    parser.add_argument(
        "--device",
        "-d",
        metavar="DEV",
        help="Target block device (e.g. /dev/sdb). Omit to list available devices.",
    )
    parser.add_argument(
        "--allow-non-removable",
        action="store_true",
        help="Allow flashing to non-removable devices (dangerous!)",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip the confirmation prompt",
    )
    parser.add_argument(
        "--block-size",
        default="4M",
        metavar="SIZE",
        help="dd block size (default: 4M)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    return parser


def _print_devices(devices: list[dict]) -> None:
    print("\nAvailable block devices:")
    print(f"{'Device':<15} {'Size':<10} {'Model':<30} {'Removable'}")
    print("-" * 68)
    for dev in devices:
        removable = "Yes" if dev["hotplug"] else "No"
        model = dev["model"] or dev["vendor"] or "Unknown"
        print(f"{dev['name']:<15} {dev['size']:<10} {model:<30} {removable}")
    print()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    log = logging.getLogger(__name__)

    if not args.device:
        try:
            devices = list_block_devices()
        except Exception as exc:
            log.error("Failed to list block devices: %s", exc)
            return 1
        _print_devices(devices)
        return 0

    if not args.image.exists():
        log.error("Image file not found: %s", args.image)
        return 1

    is_valid, reason = validate_device(
        args.device, allow_non_removable=args.allow_non_removable
    )
    if not is_valid:
        log.error("Invalid target device: %s", reason)
        return 1

    if not args.yes:
        print(f"\nWARNING: This will permanently erase ALL data on {args.device}!")
        print(f"  Image : {args.image}")
        print(f"  Target: {args.device}")
        confirm = input("\nType 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            return 0

    try:
        flash_image(args.image, args.device, block_size=args.block_size)
    except Exception as exc:
        log.error("Flash failed: %s", exc)
        return 1

    log.info("Successfully flashed %s to %s", args.image, args.device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
