"""Image customization logic for Raspberry Pi OS."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from pi_automation.config import BootConfig, LocaleConfig, PiConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure helper functions (easily unit-testable)
# ---------------------------------------------------------------------------


def _render_wpa_supplicant(ssid: str, password: str, country: str) -> str:
    """Render a wpa_supplicant.conf file content string."""
    return (
        f"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        f"update_config=1\n"
        f"country={country}\n"
        f"\n"
        f"network={{\n"
        f'    ssid="{ssid}"\n'
        f'    psk="{password}"\n'
        f"}}\n"
    )


def _boot_config_updates(boot: BootConfig) -> dict[str, str]:
    """Return config.txt key=value pairs derived from a BootConfig."""
    params: dict[str, str] = {}
    if boot.arm_64bit:
        params["arm_64bit"] = "1"
    params["gpu_mem"] = str(boot.gpu_mem)
    if boot.enable_uart:
        params["enable_uart"] = "1"
    for key, value in boot.extra_params.items():
        params[str(key)] = str(value)
    return params


def _update_config_txt(content: str, updates: dict[str, str]) -> str:
    """
    Update or append key=value lines in config.txt content.

    Existing keys are updated in place; new keys are appended at the end.
    Comment lines and section headers are preserved unchanged.
    """
    lines = content.splitlines(keepends=True)
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("[") or "=" not in stripped:
            new_lines.append(line)
            continue

        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    return "".join(new_lines)


def _render_firstrun_sh(hostname: str, locale: LocaleConfig) -> str:
    """Render the firstrun.sh script that runs on first boot."""
    return f"""\
#!/bin/bash

set -o errexit
set -o nounset

# Set hostname
CURRENT_HOSTNAME=$(cat /etc/hostname | tr -d " \\t\\n\\r")
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname {hostname}
else
    echo {hostname} >/etc/hostname
    sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\\t{hostname}/g" /etc/hosts
fi

# Set locale
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_locale {locale.language} {locale.keyboard_layout}
else
    if [ -f /etc/default/locale ]; then
        sed -i "s/LANG=.*/LANG={locale.language}/" /etc/default/locale
    else
        echo "LANG={locale.language}" >/etc/default/locale
    fi
fi

# Set timezone
rm -f /etc/localtime
echo "{locale.timezone}" >/etc/timezone
dpkg-reconfigure -f noninteractive tzdata

# Remove firstrun trigger from cmdline.txt and delete this script
CMDLINE=/boot/firmware/cmdline.txt
if [ -f "$CMDLINE" ]; then
    sed -i "s| systemd.run=.*||g" "$CMDLINE"
fi
rm -f /boot/firmware/firstrun.sh
exit 0
"""


def _update_cmdline_for_firstrun(
    content: str,
    firstrun_path: str = "/boot/firmware/firstrun.sh",
) -> str:
    """
    Inject firstrun.sh parameters into cmdline.txt.

    The parameters are only added once; if already present they are not
    duplicated.
    """
    content = content.strip()
    firstrun_param = (
        f"systemd.run={firstrun_path} "
        "systemd.run_success_action=reboot "
        "systemd.unit=kernel-command-line.target"
    )
    if "systemd.run=" not in content:
        content = content + " " + firstrun_param
    return content + "\n"


# ---------------------------------------------------------------------------
# ImageCustomizer
# ---------------------------------------------------------------------------


class ImageCustomizer:
    """
    Applies first-boot customizations to a mounted Raspberry Pi OS image.

    ``boot_path`` must point to the mounted FAT32 boot partition.
    ``rootfs_path`` is optional and points to the mounted ext4 root
    filesystem partition.
    """

    def __init__(
        self,
        config: PiConfig,
        boot_path: Path,
        rootfs_path: Optional[Path] = None,
    ) -> None:
        self.config = config
        self.boot_path = Path(boot_path)
        self.rootfs_path = Path(rootfs_path) if rootfs_path else None

    def apply_all(self) -> None:
        """Apply all configured customizations."""
        self.apply_ssh()
        self.apply_wifi()
        self.apply_boot_config()
        self.apply_user()
        self.apply_firstrun()
        logger.info("All customizations applied successfully")

    def apply_ssh(self) -> None:
        """Enable or disable SSH on first boot via the sentinel file."""
        ssh_file = self.boot_path / "ssh"
        if self.config.customization.ssh.enabled:
            ssh_file.touch()
            logger.info("SSH enabled")
        else:
            ssh_file.unlink(missing_ok=True)
            logger.info("SSH disabled")

    def apply_wifi(self) -> None:
        """Write wpa_supplicant.conf to the boot partition if WiFi is enabled."""
        wifi = self.config.customization.wifi
        if not wifi.enabled:
            logger.info("WiFi not configured, skipping")
            return

        content = _render_wpa_supplicant(wifi.ssid, wifi.password, wifi.country)
        wpa_conf = self.boot_path / "wpa_supplicant.conf"
        wpa_conf.write_text(content)
        logger.info("WiFi configured for SSID: %s", wifi.ssid)

    def apply_boot_config(self) -> None:
        """Update config.txt with hardware settings from BootConfig."""
        config_txt = self.boot_path / "config.txt"
        existing = config_txt.read_text() if config_txt.exists() else ""
        updates = _boot_config_updates(self.config.customization.boot)
        config_txt.write_text(_update_config_txt(existing, updates))
        logger.info("config.txt updated")

    def apply_user(self) -> None:
        """Configure the initial user account via userconf.txt."""
        user = self.config.customization.user
        if not user.password_hash:
            logger.warning("No password_hash set for user '%s'; skipping userconf.txt", user.name)
            return

        userconf = self.boot_path / "userconf.txt"
        userconf.write_text(f"{user.name}:{user.password_hash}\n")
        logger.info("User '%s' configured via userconf.txt", user.name)

    def apply_firstrun(self) -> None:
        """Write firstrun.sh and update cmdline.txt to trigger it on boot."""
        cust = self.config.customization
        script = _render_firstrun_sh(cust.hostname, cust.locale)

        firstrun = self.boot_path / "firstrun.sh"
        firstrun.write_text(script)
        firstrun.chmod(0o755)

        cmdline_txt = self.boot_path / "cmdline.txt"
        existing = cmdline_txt.read_text() if cmdline_txt.exists() else ""
        cmdline_txt.write_text(_update_cmdline_for_firstrun(existing))

        logger.info("Hostname set to: %s", cust.hostname)
        logger.info("firstrun.sh created and cmdline.txt updated")


# ---------------------------------------------------------------------------
# ImageMounter
# ---------------------------------------------------------------------------


class ImageMounter:
    """
    Context manager that mounts a Raspberry Pi OS image via a loop device.

    Requires root privileges (``sudo``) and Linux kernel loopback support.

    Usage::

        with ImageMounter(image, boot_mount, rootfs_mount):
            customizer = ImageCustomizer(config, boot_mount, rootfs_mount)
            customizer.apply_all()
    """

    def __init__(
        self,
        image_path: Path,
        boot_mount: Path,
        rootfs_mount: Optional[Path] = None,
    ) -> None:
        self.image_path = Path(image_path)
        self.boot_mount = Path(boot_mount)
        self.rootfs_mount = Path(rootfs_mount) if rootfs_mount else None
        self._loop_device: Optional[str] = None

    def mount(self) -> None:
        """Set up the loop device and mount the image partitions."""
        result = subprocess.run(
            ["losetup", "--find", "--partscan", "--show", str(self.image_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        self._loop_device = result.stdout.strip()
        logger.info("Image attached as loop device: %s", self._loop_device)

        self.boot_mount.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["mount", f"{self._loop_device}p1", str(self.boot_mount)],
            check=True,
        )
        logger.info("Boot partition mounted at %s", self.boot_mount)

        if self.rootfs_mount is not None:
            self.rootfs_mount.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["mount", f"{self._loop_device}p2", str(self.rootfs_mount)],
                check=True,
            )
            logger.info("Root filesystem mounted at %s", self.rootfs_mount)

    def unmount(self) -> None:
        """Unmount partitions and detach the loop device."""
        if self.rootfs_mount and self.rootfs_mount.exists() and self.rootfs_mount.is_mount():
            subprocess.run(["umount", str(self.rootfs_mount)], check=True)
            logger.info("Root filesystem unmounted")

        if self.boot_mount.exists() and self.boot_mount.is_mount():
            subprocess.run(["umount", str(self.boot_mount)], check=True)
            logger.info("Boot partition unmounted")

        if self._loop_device:
            subprocess.run(["losetup", "--detach", self._loop_device], check=True)
            logger.info("Loop device %s detached", self._loop_device)
            self._loop_device = None

    def __enter__(self) -> ImageMounter:
        self.mount()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.unmount()
        return False
