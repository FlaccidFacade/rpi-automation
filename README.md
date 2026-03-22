# rpi-automation

Two scripts to set up a Raspberry Pi for headless first-boot and flash the SD card.

## How it works

1. Edit the files in `boot/` — these are the actual files that go onto the boot partition
2. `setup.sh` copies them to a mounted boot partition and wires up the firstrun trigger
3. `flash.sh` writes the image to an SD card

## Quick start

```bash
# 1. Edit boot files to match your setup
nano boot/wpa_supplicant.conf   # WiFi SSID + password
nano boot/firstrun.sh           # hostname, locale, timezone
nano boot/userconf.txt          # username + password hash
nano boot/config.txt            # hardware params

# 2. Mount the boot partition and copy files
LOOPDEV=$(sudo losetup --find --partscan --show raspios.img)   # e.g. /dev/loop0
sudo mkdir -p /mnt/pi-boot
sudo mount "${LOOPDEV}p1" /mnt/pi-boot
sudo ./setup.sh /mnt/pi-boot
sudo umount /mnt/pi-boot
sudo losetup -d "${LOOPDEV}"

# 3. Flash to SD card
sudo ./flash.sh raspios.img /dev/sdb
```

Or if the SD card is already mounted:

```bash
sudo ./setup.sh /media/you/bootfs
```

## Boot files

| File | What to edit |
|---|---|
| `boot/ssh` | Empty file — just enables SSH. Delete it to disable. |
| `boot/wpa_supplicant.conf` | Set your WiFi SSID and password |
| `boot/config.txt` | Set `gpu_mem`, `arm_64bit`, etc. |
| `boot/userconf.txt` | Set username + password hash (`openssl passwd -6 yourpassword`) |
| `boot/firstrun.sh` | Set hostname, locale, timezone at the top of the script |

## Files

```
rpi-automation/
├── setup.sh          # copies boot/ files to mounted partition
├── flash.sh          # flashes image to SD card
└── boot/             # edit these directly
    ├── ssh
    ├── wpa_supplicant.conf
    ├── config.txt
    ├── userconf.txt
    └── firstrun.sh
```
