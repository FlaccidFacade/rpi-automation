"""Tests for pi_automation.flash."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pi_automation.flash import (
    _get_mountpoints,
    list_block_devices,
    validate_device,
)

# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

_LSBLK_OUTPUT = {
    "blockdevices": [
        {
            "name": "sda",
            "size": "500G",
            "type": "disk",
            "mountpoint": None,
            "hotplug": False,
            "model": "Samsung SSD",
            "vendor": "Samsung",
            "children": [
                {"name": "sda1", "type": "part", "mountpoint": "/", "children": []},
                {"name": "sda2", "type": "part", "mountpoint": "/home", "children": []},
            ],
        },
        {
            "name": "sdb",
            "size": "32G",
            "type": "disk",
            "mountpoint": None,
            "hotplug": True,
            "model": "SD Card",
            "vendor": "SanDisk",
            "children": [],
        },
    ]
}


# ---------------------------------------------------------------------------
# _get_mountpoints
# ---------------------------------------------------------------------------


class TestGetMountpoints:
    def test_no_mountpoints(self):
        assert _get_mountpoints({"mountpoint": None, "children": []}) == []

    def test_single_mountpoint(self):
        assert _get_mountpoints({"mountpoint": "/mnt/boot", "children": []}) == ["/mnt/boot"]

    def test_nested_mountpoints(self):
        dev = {
            "mountpoint": None,
            "children": [
                {"mountpoint": "/", "children": []},
                {"mountpoint": "/boot", "children": []},
            ],
        }
        result = _get_mountpoints(dev)
        assert "/" in result
        assert "/boot" in result

    def test_deeply_nested(self):
        dev = {
            "mountpoint": None,
            "children": [
                {
                    "mountpoint": None,
                    "children": [
                        {"mountpoint": "/deep", "children": []},
                    ],
                }
            ],
        }
        assert "/deep" in _get_mountpoints(dev)

    def test_ignores_none_mountpoints(self):
        dev = {
            "mountpoint": None,
            "children": [{"mountpoint": None, "children": []}],
        }
        assert _get_mountpoints(dev) == []


# ---------------------------------------------------------------------------
# list_block_devices
# ---------------------------------------------------------------------------


class TestListBlockDevices:
    def _mock_run(self, output: dict) -> MagicMock:
        mock = MagicMock()
        mock.stdout = json.dumps(output)
        return mock

    def test_returns_only_disk_type(self):
        with patch("subprocess.run", return_value=self._mock_run(_LSBLK_OUTPUT)):
            devices = list_block_devices()
        assert all(d["name"].startswith("/dev/") for d in devices)
        assert len(devices) == 2

    def test_device_names_prefixed_with_dev(self):
        with patch("subprocess.run", return_value=self._mock_run(_LSBLK_OUTPUT)):
            devices = list_block_devices()
        names = {d["name"] for d in devices}
        assert "/dev/sda" in names
        assert "/dev/sdb" in names

    def test_hotplug_field_preserved(self):
        with patch("subprocess.run", return_value=self._mock_run(_LSBLK_OUTPUT)):
            devices = list_block_devices()
        sdb = next(d for d in devices if d["name"] == "/dev/sdb")
        assert sdb["hotplug"] is True
        sda = next(d for d in devices if d["name"] == "/dev/sda")
        assert sda["hotplug"] is False

    def test_mountpoints_collected_from_children(self):
        with patch("subprocess.run", return_value=self._mock_run(_LSBLK_OUTPUT)):
            devices = list_block_devices()
        sda = next(d for d in devices if d["name"] == "/dev/sda")
        assert "/" in sda["mountpoints"]
        assert "/home" in sda["mountpoints"]

    def test_empty_blockdevices(self):
        with patch("subprocess.run", return_value=self._mock_run({"blockdevices": []})):
            assert list_block_devices() == []


# ---------------------------------------------------------------------------
# validate_device
# ---------------------------------------------------------------------------


def _make_device_list(name: str, hotplug: bool, mountpoints: list[str]) -> list[dict]:
    return [{"name": name, "hotplug": hotplug, "mountpoints": mountpoints}]


class TestValidateDevice:
    def test_rejects_nonexistent_path(self):
        is_valid, reason = validate_device("/dev/sdXYZNONEXISTENT_abc")
        assert not is_valid
        assert "does not exist" in reason

    def test_rejects_path_outside_dev(self, tmp_path):
        fake = tmp_path / "notadevice"
        fake.touch()
        is_valid, reason = validate_device(str(fake))
        assert not is_valid
        assert "block device" in reason

    def test_accepts_valid_removable_device(self, tmp_path):
        fake_dev = tmp_path / "sdb"
        fake_dev.touch()
        with (
            patch("pi_automation.flash.list_block_devices") as mock_list,
            patch("pi_automation.flash.os.path.exists", return_value=True),
        ):
            mock_list.return_value = _make_device_list("/dev/sdb", hotplug=True, mountpoints=[])
            is_valid, reason = validate_device("/dev/sdb")
        assert is_valid, reason

    def test_rejects_device_mounted_at_root(self):
        with (
            patch("pi_automation.flash.list_block_devices") as mock_list,
            patch("pi_automation.flash.os.path.exists", return_value=True),
        ):
            mock_list.return_value = _make_device_list(
                "/dev/sda", hotplug=False, mountpoints=["/"]
            )
            is_valid, reason = validate_device("/dev/sda", allow_non_removable=True)
        assert not is_valid
        assert "critical" in reason.lower()

    def test_rejects_device_mounted_at_home(self):
        with (
            patch("pi_automation.flash.list_block_devices") as mock_list,
            patch("pi_automation.flash.os.path.exists", return_value=True),
        ):
            mock_list.return_value = _make_device_list(
                "/dev/sda", hotplug=False, mountpoints=["/home"]
            )
            is_valid, reason = validate_device("/dev/sda", allow_non_removable=True)
        assert not is_valid

    def test_rejects_non_removable_without_flag(self):
        with (
            patch("pi_automation.flash.list_block_devices") as mock_list,
            patch("pi_automation.flash.os.path.exists", return_value=True),
        ):
            mock_list.return_value = _make_device_list(
                "/dev/sdb", hotplug=False, mountpoints=[]
            )
            is_valid, reason = validate_device("/dev/sdb")
        assert not is_valid
        assert "removable" in reason.lower()

    def test_allows_non_removable_with_flag(self):
        with (
            patch("pi_automation.flash.list_block_devices") as mock_list,
            patch("pi_automation.flash.os.path.exists", return_value=True),
        ):
            mock_list.return_value = _make_device_list(
                "/dev/sdb", hotplug=False, mountpoints=[]
            )
            is_valid, reason = validate_device("/dev/sdb", allow_non_removable=True)
        assert is_valid, reason

    def test_rejects_device_not_in_lsblk(self):
        with (
            patch("pi_automation.flash.list_block_devices") as mock_list,
            patch("pi_automation.flash.os.path.exists", return_value=True),
        ):
            mock_list.return_value = []
            is_valid, reason = validate_device("/dev/sdc")
        assert not is_valid
        assert "not found" in reason.lower()

    def test_handles_lsblk_failure(self):
        import subprocess
        with (
            patch("pi_automation.flash.list_block_devices") as mock_list,
            patch("pi_automation.flash.os.path.exists", return_value=True),
        ):
            mock_list.side_effect = subprocess.CalledProcessError(1, "lsblk")
            is_valid, reason = validate_device("/dev/sdb")
        assert not is_valid
        assert "failed" in reason.lower()
