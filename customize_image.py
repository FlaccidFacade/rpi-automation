#!/usr/bin/env python3
"""Customize a Raspberry Pi OS image for first boot.

Requires root privileges when mounting the image.  You can skip mounting
with ``--no-mount`` and point the tool at already-mounted directories.

Examples
--------
Apply customizations by mounting the image (requires root)::

    sudo python3 customize_image.py raspios.img --config config/rpi4b_8gb.yaml

Apply customizations to an already-mounted image (no root needed)::

    python3 customize_image.py raspios.img \\
        --no-mount --boot /mnt/boot --config config/rpi4b_8gb.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path

from pi_automation.config import PiConfig
from pi_automation.customize import ImageCustomizer, ImageMounter


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Customize a Raspberry Pi OS image for first boot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to the Raspberry Pi OS image (.img or .img.xz)",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path("config/rpi4b_8gb.yaml"),
        metavar="FILE",
        help="YAML configuration file (default: config/rpi4b_8gb.yaml)",
    )
    parser.add_argument(
        "--no-mount",
        action="store_true",
        help=(
            "Skip mounting — apply customizations to an already-mounted "
            "image. Requires --boot."
        ),
    )
    parser.add_argument(
        "--boot",
        type=Path,
        metavar="DIR",
        help="Path to the mounted boot partition (required with --no-mount)",
    )
    parser.add_argument(
        "--rootfs",
        type=Path,
        metavar="DIR",
        help="Path to the mounted root filesystem partition (optional)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    log = logging.getLogger(__name__)

    if not args.config.exists():
        log.error("Config file not found: %s", args.config)
        return 1

    config = PiConfig.from_yaml(args.config)
    errors = config.validate()
    if errors:
        for err in errors:
            log.error("Config error: %s", err)
        return 1

    log.info("Loaded config for: %s", config.model or config.device)

    if args.no_mount:
        if not args.boot:
            log.error("--boot is required when using --no-mount")
            return 1
        customizer = ImageCustomizer(config, args.boot, args.rootfs)
        customizer.apply_all()
    else:
        if not args.image.exists():
            log.error("Image file not found: %s", args.image)
            return 1
        with (
            tempfile.TemporaryDirectory(prefix="pi-boot-") as boot_dir,
            tempfile.TemporaryDirectory(prefix="pi-rootfs-") as rootfs_dir,
        ):
            with ImageMounter(args.image, Path(boot_dir), Path(rootfs_dir)):
                customizer = ImageCustomizer(
                    config, Path(boot_dir), Path(rootfs_dir)
                )
                customizer.apply_all()

    log.info("Customization complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
