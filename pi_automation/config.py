"""Configuration dataclasses and YAML loading for pi-automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SSHConfig:
    """SSH access configuration."""

    enabled: bool = True


@dataclass
class WiFiConfig:
    """WiFi network configuration."""

    enabled: bool = False
    ssid: str = ""
    password: str = ""
    country: str = "US"


@dataclass
class UserConfig:
    """Primary user account configuration."""

    name: str = "pi"
    # SHA-512 hashed password. Generate with: openssl passwd -6 yourpassword
    password_hash: str = ""


@dataclass
class LocaleConfig:
    """Locale, timezone, and keyboard configuration."""

    timezone: str = "UTC"
    keyboard_layout: str = "us"
    language: str = "en_US.UTF-8"


@dataclass
class BootConfig:
    """Boot-time hardware configuration (config.txt parameters)."""

    arm_64bit: bool = True
    gpu_mem: int = 76
    enable_uart: bool = False
    extra_params: dict = field(default_factory=dict)


@dataclass
class ImageConfig:
    """Raspberry Pi OS image selection parameters."""

    os: str = "raspios"
    variant: str = "lite"
    arch: str = "arm64"
    version: str = "latest"
    url: str = ""


@dataclass
class CustomizationConfig:
    """All first-boot customization settings."""

    hostname: str = "raspberrypi"
    ssh: SSHConfig = field(default_factory=SSHConfig)
    wifi: WiFiConfig = field(default_factory=WiFiConfig)
    user: UserConfig = field(default_factory=UserConfig)
    locale: LocaleConfig = field(default_factory=LocaleConfig)
    boot: BootConfig = field(default_factory=BootConfig)


@dataclass
class PiConfig:
    """Top-level configuration for a Raspberry Pi device."""

    device: str = "rpi4b"
    model: str = ""
    image: ImageConfig = field(default_factory=ImageConfig)
    customization: CustomizationConfig = field(default_factory=CustomizationConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> PiConfig:
        """Load configuration from a YAML file."""
        with open(path) as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data or {})

    @classmethod
    def from_dict(cls, data: dict) -> PiConfig:
        """Build a PiConfig from a plain dictionary (e.g. parsed YAML)."""
        img = data.get("image", {})
        image = ImageConfig(
            os=img.get("os", "raspios"),
            variant=img.get("variant", "lite"),
            arch=img.get("arch", "arm64"),
            version=img.get("version", "latest"),
            url=img.get("url", ""),
        )

        cust = data.get("customization", {})

        ssh_d = cust.get("ssh", {})
        ssh = SSHConfig(enabled=ssh_d.get("enabled", True))

        wifi_d = cust.get("wifi", {})
        wifi = WiFiConfig(
            enabled=wifi_d.get("enabled", False),
            ssid=wifi_d.get("ssid", ""),
            password=wifi_d.get("password", ""),
            country=wifi_d.get("country", "US"),
        )

        user_d = cust.get("user", {})
        user = UserConfig(
            name=user_d.get("name", "pi"),
            password_hash=user_d.get("password_hash", ""),
        )

        locale_d = cust.get("locale", {})
        locale = LocaleConfig(
            timezone=locale_d.get("timezone", "UTC"),
            keyboard_layout=locale_d.get("keyboard_layout", "us"),
            language=locale_d.get("language", "en_US.UTF-8"),
        )

        boot_d = cust.get("boot", {})
        boot = BootConfig(
            arm_64bit=boot_d.get("arm_64bit", True),
            gpu_mem=boot_d.get("gpu_mem", 76),
            enable_uart=boot_d.get("enable_uart", False),
            extra_params=boot_d.get("extra_params", {}),
        )

        customization = CustomizationConfig(
            hostname=cust.get("hostname", "raspberrypi"),
            ssh=ssh,
            wifi=wifi,
            user=user,
            locale=locale,
            boot=boot,
        )

        return cls(
            device=data.get("device", "rpi4b"),
            model=data.get("model", ""),
            image=image,
            customization=customization,
        )

    def validate(self) -> list[str]:
        """Return a list of configuration error strings (empty = valid)."""
        errors: list[str] = []

        if not self.customization.hostname:
            errors.append("Hostname cannot be empty")

        if self.customization.wifi.enabled:
            if not self.customization.wifi.ssid:
                errors.append("WiFi SSID must be set when WiFi is enabled")
            if not self.customization.wifi.password:
                errors.append("WiFi password must be set when WiFi is enabled")

        if self.customization.boot.gpu_mem < 16:
            errors.append("GPU memory must be at least 16 MB")

        return errors
