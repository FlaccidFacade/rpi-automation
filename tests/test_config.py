"""Tests for pi_automation.config."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pi_automation.config import (
    BootConfig,
    LocaleConfig,
    PiConfig,
    SSHConfig,
    UserConfig,
    WiFiConfig,
)


class TestDefaults:
    def test_device(self):
        assert PiConfig.from_dict({}).device == "rpi4b"

    def test_hostname(self):
        assert PiConfig.from_dict({}).customization.hostname == "raspberrypi"

    def test_ssh_enabled_by_default(self):
        assert PiConfig.from_dict({}).customization.ssh.enabled is True

    def test_wifi_disabled_by_default(self):
        assert PiConfig.from_dict({}).customization.wifi.enabled is False

    def test_arm_64bit_by_default(self):
        assert PiConfig.from_dict({}).customization.boot.arm_64bit is True

    def test_gpu_mem_default(self):
        assert PiConfig.from_dict({}).customization.boot.gpu_mem == 76

    def test_user_name_default(self):
        assert PiConfig.from_dict({}).customization.user.name == "pi"


class TestFromDict:
    def test_top_level_fields(self):
        config = PiConfig.from_dict({"device": "rpizero2w", "model": "RPi Zero 2W"})
        assert config.device == "rpizero2w"
        assert config.model == "RPi Zero 2W"

    def test_image_fields(self):
        config = PiConfig.from_dict({
            "image": {"os": "raspios", "variant": "desktop", "arch": "armhf", "version": "2024-11-19"},
        })
        assert config.image.variant == "desktop"
        assert config.image.arch == "armhf"
        assert config.image.version == "2024-11-19"

    def test_ssh_disabled(self):
        config = PiConfig.from_dict({"customization": {"ssh": {"enabled": False}}})
        assert config.customization.ssh.enabled is False

    def test_wifi_full(self):
        config = PiConfig.from_dict({
            "customization": {
                "wifi": {
                    "enabled": True,
                    "ssid": "MyNet",
                    "password": "s3cr3t",
                    "country": "GB",
                }
            }
        })
        wifi = config.customization.wifi
        assert wifi.enabled is True
        assert wifi.ssid == "MyNet"
        assert wifi.country == "GB"

    def test_user_fields(self):
        config = PiConfig.from_dict({
            "customization": {"user": {"name": "admin", "password_hash": "$6$abc"}}
        })
        assert config.customization.user.name == "admin"
        assert config.customization.user.password_hash == "$6$abc"

    def test_locale_fields(self):
        config = PiConfig.from_dict({
            "customization": {
                "locale": {
                    "timezone": "Europe/London",
                    "keyboard_layout": "gb",
                    "language": "en_GB.UTF-8",
                }
            }
        })
        locale = config.customization.locale
        assert locale.timezone == "Europe/London"
        assert locale.keyboard_layout == "gb"
        assert locale.language == "en_GB.UTF-8"

    def test_boot_fields(self):
        config = PiConfig.from_dict({
            "customization": {
                "boot": {
                    "arm_64bit": True,
                    "gpu_mem": 128,
                    "enable_uart": True,
                    "extra_params": {"over_voltage": 2},
                }
            }
        })
        boot = config.customization.boot
        assert boot.gpu_mem == 128
        assert boot.enable_uart is True
        assert boot.extra_params == {"over_voltage": 2}

    def test_empty_dict_uses_all_defaults(self):
        config = PiConfig.from_dict({})
        assert config.device == "rpi4b"
        assert config.customization.hostname == "raspberrypi"


class TestFromYaml:
    def test_roundtrip(self, tmp_path):
        data = {
            "device": "rpi4b",
            "customization": {
                "hostname": "yaml-pi",
                "wifi": {"enabled": False},
            },
        }
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml.dump(data))
        config = PiConfig.from_yaml(config_file)
        assert config.customization.hostname == "yaml-pi"

    def test_bundled_rpi4b_yaml_loads(self):
        yaml_path = Path(__file__).parent.parent / "config" / "rpi4b_8gb.yaml"
        config = PiConfig.from_yaml(yaml_path)
        assert config.device == "rpi4b"
        assert config.customization.boot.arm_64bit is True
        assert config.customization.ssh.enabled is True

    def test_bundled_template_yaml_loads(self):
        yaml_path = Path(__file__).parent.parent / "config" / "template.yaml"
        config = PiConfig.from_yaml(yaml_path)
        assert config.customization.boot.gpu_mem == 76


class TestValidate:
    def test_valid_config_returns_no_errors(self):
        assert PiConfig.from_dict({}).validate() == []

    def test_empty_hostname_is_invalid(self):
        config = PiConfig.from_dict({"customization": {"hostname": ""}})
        errors = config.validate()
        assert any("hostname" in e.lower() for e in errors)

    def test_wifi_missing_ssid(self):
        config = PiConfig.from_dict({
            "customization": {"wifi": {"enabled": True, "ssid": "", "password": "secret"}}
        })
        errors = config.validate()
        assert any("ssid" in e.lower() for e in errors)

    def test_wifi_missing_password(self):
        config = PiConfig.from_dict({
            "customization": {"wifi": {"enabled": True, "ssid": "Net", "password": ""}}
        })
        errors = config.validate()
        assert any("password" in e.lower() for e in errors)

    def test_gpu_mem_too_low(self):
        config = PiConfig.from_dict({"customization": {"boot": {"gpu_mem": 8}}})
        errors = config.validate()
        assert any("gpu" in e.lower() for e in errors)

    def test_wifi_disabled_does_not_require_ssid(self):
        config = PiConfig.from_dict({
            "customization": {"wifi": {"enabled": False, "ssid": "", "password": ""}}
        })
        assert config.validate() == []

    def test_multiple_errors_returned(self):
        config = PiConfig.from_dict({
            "customization": {
                "hostname": "",
                "wifi": {"enabled": True, "ssid": "", "password": ""},
                "boot": {"gpu_mem": 8},
            }
        })
        assert len(config.validate()) >= 3
