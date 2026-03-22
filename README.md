# rpi-automation

Simple shell scripts for customizing a Raspberry Pi OS image and flashing SD cards. Currently targets RPi 4B 8GB — will expand for Zero, Pico, etc.

## What it does

`setup.sh` reads a config file and writes first-boot files to a mounted boot partition:

| File | Purpose |
|---|---|
| `ssh` | Enables SSH on first boot |
| `wpa_supplicant.conf` | WiFi credentials (if enabled) |
| `config.txt` | Hardware params (`arm_64bit`, `gpu_mem`, `enable_uart`, extras) |
| `userconf.txt` | Initial user + hashed password |
| `firstrun.sh` + `cmdline.txt` | Sets hostname, locale, timezone on first boot |

`flash.sh` flashes an `.img` to an SD card via `dd` with a safety check.

## Usage

### 1. Edit the config

```bash
cp config/rpi4b_8gb.conf config/my_pi.conf
nano config/my_pi.conf
```

Key settings:

```bash
HOSTNAME="my-pi"
SSH_ENABLED=true
WIFI_ENABLED=true
WIFI_SSID="MyNetwork"
WIFI_PASSWORD="s3cret"
USER_NAME="pi"
USER_PASSWORD_HASH="$6$..."   # openssl passwd -6 yourpassword
TIMEZONE="America/New_York"
```

### 2. Mount the image and run setup

```bash
# Mount the boot partition (partition 1 of the image)
sudo losetup --find --partscan --show raspios.img   # e.g. /dev/loop0
sudo mkdir -p /mnt/pi-boot
sudo mount /dev/loop0p1 /mnt/pi-boot

# Run setup
sudo ./setup.sh config/my_pi.conf /mnt/pi-boot

# Unmount
sudo umount /mnt/pi-boot
sudo losetup -d /dev/loop0
```

Or if the SD card is already inserted and mounted:

```bash
sudo ./setup.sh config/my_pi.conf /media/you/bootfs
```

### 3. Flash to SD card

```bash
# List devices
sudo ./flash.sh raspios.img

# Flash (will prompt for confirmation)
sudo ./flash.sh raspios.img /dev/sdb
```

## Generate a password hash

```bash
openssl passwd -6 yourpassword
```

Paste the output into `USER_PASSWORD_HASH` in your config file.

## Files

```
rpi-automation/
├── setup.sh                # write first-boot files to boot partition
├── flash.sh                # flash image to SD card
└── config/
    └── rpi4b_8gb.conf      # default config for RPi 4B 8GB
```

