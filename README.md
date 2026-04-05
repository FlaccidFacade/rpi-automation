# rpi-automation

Scripts to set up a Raspberry Pi for headless first-boot and flash the SD card.

## How it works

1. Create or edit a profile in `configs/<profile>/` (boot files live directly in that folder)
2. `run.sh` orchestrates profile selection, flashing, and boot configuration in order
3. Internally it calls `flash.sh`, mounts the boot partition, then calls `setup.sh`

## Quick start

```bash
# Run full workflow (interactive profile select)
sudo ./run.sh

# Run full workflow with a specific profile
sudo ./run.sh default
```

If `IMAGE` and `DEVICE` are not defined in the profile, `run.sh` prompts for them.

`IMAGE` can be either a `.img` or `.img.xz` file.
Relative `IMAGE` paths are resolved from the `run.sh` directory.
If a `.img.xz` image is missing locally, `run.sh` can auto-download it (default URL can be overridden with `IMAGE_URL` in `profile.env`).

## Profiles

Profiles live in `configs/<profile>/`.

- `configs/<profile>/profile.env` - optional defaults
- `configs/<profile>/` - place boot files directly here (`ssh`, `wpa_supplicant.conf`, `config.txt`, `userconf.txt`, `firstrun.sh`)

Example `profile.env`:

```bash
IMAGE="/path/to/raspios.img"
DEVICE="/dev/sdb"
# Optional URL to auto-download a missing .img.xz file
# IMAGE_URL="https://downloads.raspberrypi.com/.../raspios.img.xz"
# Optional if auto-detection does not match your device naming
# BOOT_PARTITION="/dev/sdb1"
```

`run.sh` uses `configs/<profile>/` as the boot source directly.

The repository includes a starter profile at `configs/default/`.

## Manual helper usage

```bash
# 1. Edit boot files to match your setup
nano boot/wpa_supplicant.conf   # WiFi SSID + password
nano boot/firstrun.sh           # hostname, locale, timezone
nano boot/userconf.txt          # username + password hash
nano boot/config.txt            # hardware params

# 2. Mount the boot partition and copy files
LOOPDEV=$(sudo losetup --find --partscan --show raspios.img)   # e.g. /dev/loop0
sudo mkdir -p /mnt/rpi-boot
sudo mount "${LOOPDEV}p1" /mnt/rpi-boot
sudo ./setup.sh /mnt/rpi-boot
sudo umount /mnt/rpi-boot
sudo losetup -d "${LOOPDEV}"

# 3. Flash to SD card
sudo ./flash.sh raspios.img /dev/sdb
# or directly from Raspberry Pi download archives
sudo ./flash.sh raspios.img.xz /dev/sdb
```

Or if the SD card is already mounted:

```bash
sudo ./setup.sh /media/you/bootfs
```

## Boot files

| File | What to edit |
| --- | --- |
| `boot/ssh` | Empty file — just enables SSH. Delete it to disable. |
| `boot/wpa_supplicant.conf` | Set your WiFi SSID and password |
| `boot/config.txt` | Set `gpu_mem`, `arm_64bit`, etc. |
| `boot/userconf.txt` | Set username + password hash (`openssl passwd -6 yourpassword`) |
| `boot/firstrun.sh` | Set hostname, locale, timezone at the top of the script |

## Files

```text
rpi-automation/
├── run.sh            # top-level workflow (select profile, flash, configure)
├── setup.sh          # copies boot/ files to mounted partition
├── flash.sh          # flashes image to SD card
├── select-profile.sh # interactive profile chooser
├── configs/          # each profile folder is a full boot source
└── boot/             # edit these directly
    ├── ssh
    ├── wpa_supplicant.conf
    ├── config.txt
    ├── userconf.txt
    └── firstrun.sh
```
