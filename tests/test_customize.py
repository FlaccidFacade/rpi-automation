"""Tests for pi_automation.customize."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from pi_automation.config import LocaleConfig, PiConfig
from pi_automation.customize import (
    ImageCustomizer,
    _boot_config_updates,
    _render_firstrun_sh,
    _render_wpa_supplicant,
    _update_cmdline_for_firstrun,
    _update_config_txt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_config() -> PiConfig:
    return PiConfig.from_dict(
        {
            "customization": {
                "hostname": "test-pi",
                "ssh": {"enabled": True},
                "wifi": {"enabled": False},
                "user": {"name": "pi", "password_hash": ""},
                "boot": {"arm_64bit": True, "gpu_mem": 76, "enable_uart": False},
                "locale": {
                    "timezone": "UTC",
                    "keyboard_layout": "us",
                    "language": "en_US.UTF-8",
                },
            }
        }
    )


@pytest.fixture
def full_config() -> PiConfig:
    return PiConfig.from_dict(
        {
            "customization": {
                "hostname": "full-pi",
                "ssh": {"enabled": True},
                "wifi": {
                    "enabled": True,
                    "ssid": "TestNet",
                    "password": "testpass",
                    "country": "US",
                },
                "user": {"name": "pi", "password_hash": "$6$salt$hash"},
                "boot": {"arm_64bit": True, "gpu_mem": 76},
                "locale": {
                    "timezone": "America/New_York",
                    "keyboard_layout": "us",
                    "language": "en_US.UTF-8",
                },
            }
        }
    )


# ---------------------------------------------------------------------------
# _render_wpa_supplicant
# ---------------------------------------------------------------------------


class TestRenderWpaSupplicant:
    def test_contains_ssid(self):
        content = _render_wpa_supplicant("MySSID", "mypassword", "US")
        assert 'ssid="MySSID"' in content

    def test_contains_psk(self):
        content = _render_wpa_supplicant("MySSID", "mypassword", "US")
        assert 'psk="mypassword"' in content

    def test_contains_country(self):
        content = _render_wpa_supplicant("Net", "pass", "GB")
        assert "country=GB" in content

    def test_contains_ctrl_interface(self):
        content = _render_wpa_supplicant("Net", "pass", "US")
        assert "ctrl_interface=" in content

    def test_network_block_present(self):
        content = _render_wpa_supplicant("Net", "pass", "US")
        assert "network={" in content


# ---------------------------------------------------------------------------
# _boot_config_updates
# ---------------------------------------------------------------------------


class TestBootConfigUpdates:
    def test_arm_64bit_enabled(self):
        from pi_automation.config import BootConfig
        boot = BootConfig(arm_64bit=True, gpu_mem=76)
        updates = _boot_config_updates(boot)
        assert updates["arm_64bit"] == "1"

    def test_arm_64bit_disabled_not_in_updates(self):
        from pi_automation.config import BootConfig
        boot = BootConfig(arm_64bit=False, gpu_mem=76)
        updates = _boot_config_updates(boot)
        assert "arm_64bit" not in updates

    def test_gpu_mem_present(self):
        from pi_automation.config import BootConfig
        boot = BootConfig(gpu_mem=128)
        updates = _boot_config_updates(boot)
        assert updates["gpu_mem"] == "128"

    def test_enable_uart(self):
        from pi_automation.config import BootConfig
        boot = BootConfig(enable_uart=True)
        updates = _boot_config_updates(boot)
        assert updates["enable_uart"] == "1"

    def test_extra_params_merged(self):
        from pi_automation.config import BootConfig
        boot = BootConfig(extra_params={"over_voltage": 2, "arm_freq": 1800})
        updates = _boot_config_updates(boot)
        assert updates["over_voltage"] == "2"
        assert updates["arm_freq"] == "1800"


# ---------------------------------------------------------------------------
# _update_config_txt
# ---------------------------------------------------------------------------


class TestUpdateConfigTxt:
    def test_appends_to_empty(self):
        result = _update_config_txt("", {"arm_64bit": "1", "gpu_mem": "76"})
        assert "arm_64bit=1" in result
        assert "gpu_mem=76" in result

    def test_updates_existing_key(self):
        result = _update_config_txt("gpu_mem=128\n", {"gpu_mem": "76"})
        assert "gpu_mem=76" in result
        assert "gpu_mem=128" not in result

    def test_updates_multiple_existing_keys(self):
        existing = "gpu_mem=128\narm_64bit=0\n"
        result = _update_config_txt(existing, {"gpu_mem": "76", "arm_64bit": "1"})
        assert "gpu_mem=76" in result
        assert "arm_64bit=1" in result
        assert "gpu_mem=128" not in result
        assert "arm_64bit=0" not in result

    def test_preserves_comments(self):
        existing = "# A comment\ngpu_mem=128\n"
        result = _update_config_txt(existing, {"gpu_mem": "76"})
        assert "# A comment" in result

    def test_preserves_section_headers(self):
        existing = "[all]\ngpu_mem=128\n"
        result = _update_config_txt(existing, {"gpu_mem": "76"})
        assert "[all]" in result

    def test_preserves_unrelated_keys(self):
        existing = "dtparam=audio=on\ngpu_mem=128\n"
        result = _update_config_txt(existing, {"gpu_mem": "76"})
        assert "dtparam=audio=on" in result

    def test_no_duplicate_keys_on_append(self):
        result = _update_config_txt("gpu_mem=76\n", {"gpu_mem": "76"})
        assert result.count("gpu_mem=") == 1


# ---------------------------------------------------------------------------
# _render_firstrun_sh
# ---------------------------------------------------------------------------


class TestRenderFirstrunSh:
    def test_starts_with_shebang(self):
        locale = LocaleConfig()
        assert _render_firstrun_sh("my-pi", locale).startswith("#!/bin/bash")

    def test_contains_hostname(self):
        locale = LocaleConfig()
        script = _render_firstrun_sh("custom-host", locale)
        assert "custom-host" in script

    def test_contains_timezone(self):
        locale = LocaleConfig(timezone="America/New_York")
        script = _render_firstrun_sh("pi", locale)
        assert "America/New_York" in script

    def test_contains_language(self):
        locale = LocaleConfig(language="en_GB.UTF-8")
        script = _render_firstrun_sh("pi", locale)
        assert "en_GB.UTF-8" in script

    def test_contains_keyboard(self):
        locale = LocaleConfig(keyboard_layout="gb")
        script = _render_firstrun_sh("pi", locale)
        assert "gb" in script

    def test_removes_itself_on_completion(self):
        locale = LocaleConfig()
        script = _render_firstrun_sh("pi", locale)
        assert "rm -f" in script
        assert "firstrun.sh" in script


# ---------------------------------------------------------------------------
# _update_cmdline_for_firstrun
# ---------------------------------------------------------------------------


class TestUpdateCmdlineForFirstrun:
    def test_adds_systemd_run_param(self):
        result = _update_cmdline_for_firstrun("root=/dev/mmcblk0p2 rootwait")
        assert "systemd.run=" in result

    def test_does_not_duplicate_existing_param(self):
        existing = "root=/dev/mmcblk0p2 systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot"
        result = _update_cmdline_for_firstrun(existing)
        assert result.count("systemd.run=") == 1

    def test_ends_with_newline(self):
        result = _update_cmdline_for_firstrun("root=/dev/mmcblk0p2 rootwait")
        assert result.endswith("\n")

    def test_preserves_existing_params(self):
        result = _update_cmdline_for_firstrun("console=serial0,115200 rootwait")
        assert "console=serial0,115200" in result
        assert "rootwait" in result


# ---------------------------------------------------------------------------
# ImageCustomizer
# ---------------------------------------------------------------------------


class TestImageCustomizerApplySsh:
    def test_creates_ssh_file_when_enabled(self, tmp_path, basic_config):
        ImageCustomizer(basic_config, tmp_path).apply_ssh()
        assert (tmp_path / "ssh").exists()

    def test_removes_ssh_file_when_disabled(self, tmp_path, basic_config):
        (tmp_path / "ssh").touch()
        basic_config.customization.ssh.enabled = False
        ImageCustomizer(basic_config, tmp_path).apply_ssh()
        assert not (tmp_path / "ssh").exists()

    def test_no_error_if_ssh_file_absent_and_disabled(self, tmp_path, basic_config):
        basic_config.customization.ssh.enabled = False
        ImageCustomizer(basic_config, tmp_path).apply_ssh()  # must not raise


class TestImageCustomizerApplyWifi:
    def test_skips_when_disabled(self, tmp_path, basic_config):
        ImageCustomizer(basic_config, tmp_path).apply_wifi()
        assert not (tmp_path / "wpa_supplicant.conf").exists()

    def test_creates_wpa_conf_when_enabled(self, tmp_path, full_config):
        ImageCustomizer(full_config, tmp_path).apply_wifi()
        wpa_conf = tmp_path / "wpa_supplicant.conf"
        assert wpa_conf.exists()
        assert 'ssid="TestNet"' in wpa_conf.read_text()

    def test_wpa_conf_contains_password(self, tmp_path, full_config):
        ImageCustomizer(full_config, tmp_path).apply_wifi()
        assert 'psk="testpass"' in (tmp_path / "wpa_supplicant.conf").read_text()


class TestImageCustomizerApplyBootConfig:
    def test_creates_config_txt_from_scratch(self, tmp_path, basic_config):
        ImageCustomizer(basic_config, tmp_path).apply_boot_config()
        content = (tmp_path / "config.txt").read_text()
        assert "arm_64bit=1" in content
        assert "gpu_mem=76" in content

    def test_updates_existing_config_txt(self, tmp_path, basic_config):
        (tmp_path / "config.txt").write_text("# config\ngpu_mem=128\n")
        ImageCustomizer(basic_config, tmp_path).apply_boot_config()
        content = (tmp_path / "config.txt").read_text()
        assert "gpu_mem=76" in content
        assert "gpu_mem=128" not in content


class TestImageCustomizerApplyUser:
    def test_no_userconf_when_no_hash(self, tmp_path, basic_config):
        ImageCustomizer(basic_config, tmp_path).apply_user()
        assert not (tmp_path / "userconf.txt").exists()

    def test_creates_userconf_with_hash(self, tmp_path, full_config):
        ImageCustomizer(full_config, tmp_path).apply_user()
        userconf = tmp_path / "userconf.txt"
        assert userconf.exists()
        assert "pi:$6$salt$hash" in userconf.read_text()


class TestImageCustomizerApplyFirstrun:
    def test_creates_firstrun_sh(self, tmp_path, basic_config):
        (tmp_path / "cmdline.txt").write_text("root=/dev/mmcblk0p2 rootwait\n")
        ImageCustomizer(basic_config, tmp_path).apply_firstrun()
        assert (tmp_path / "firstrun.sh").exists()

    def test_firstrun_sh_is_executable(self, tmp_path, basic_config):
        (tmp_path / "cmdline.txt").write_text("root=/dev/mmcblk0p2 rootwait\n")
        ImageCustomizer(basic_config, tmp_path).apply_firstrun()
        mode = (tmp_path / "firstrun.sh").stat().st_mode
        assert mode & stat.S_IXUSR

    def test_firstrun_sh_contains_hostname(self, tmp_path, basic_config):
        (tmp_path / "cmdline.txt").write_text("root=/dev/mmcblk0p2 rootwait\n")
        ImageCustomizer(basic_config, tmp_path).apply_firstrun()
        assert "test-pi" in (tmp_path / "firstrun.sh").read_text()

    def test_cmdline_updated(self, tmp_path, basic_config):
        (tmp_path / "cmdline.txt").write_text("root=/dev/mmcblk0p2 rootwait\n")
        ImageCustomizer(basic_config, tmp_path).apply_firstrun()
        assert "systemd.run=" in (tmp_path / "cmdline.txt").read_text()

    def test_creates_cmdline_if_missing(self, tmp_path, basic_config):
        ImageCustomizer(basic_config, tmp_path).apply_firstrun()
        assert (tmp_path / "cmdline.txt").exists()


class TestImageCustomizerApplyAll:
    def test_creates_expected_files(self, tmp_path, basic_config):
        (tmp_path / "config.txt").write_text("[all]\n")
        (tmp_path / "cmdline.txt").write_text("root=/dev/mmcblk0p2 rootwait\n")
        ImageCustomizer(basic_config, tmp_path).apply_all()
        assert (tmp_path / "ssh").exists()
        assert (tmp_path / "config.txt").exists()
        assert (tmp_path / "firstrun.sh").exists()
        assert (tmp_path / "cmdline.txt").exists()
