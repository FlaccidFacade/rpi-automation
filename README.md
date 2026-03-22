# pi-automation

Tools for customizing Raspberry Pi OS images and flashing SD cards, targeting first-boot setup of Raspberry Pi devices (4B, Zero, Pico, and more).

## Features

- **Customize a Raspberry Pi OS image** for first boot — no interactive setup needed
  - Enable/disable SSH
  - Configure WiFi
  - Set hostname, locale, timezone, and keyboard layout
  - Configure the initial user account
  - Tune `config.txt` hardware parameters (64-bit mode, GPU memory, UART, overclocking, etc.)
- **Flash the image to an SD card** with safety checks (guards against accidentally targeting system disks)
- **YAML-based configuration** — one file per device type, easy to version-control

## Requirements

- Python 3.9+
- Linux host (uses `losetup`, `mount`, and `dd`)
- `pyyaml` (`pip install -r requirements.txt`)
- Root privileges for image mounting and SD card flashing

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your configuration

Copy and edit the bundled configuration for RPi 4B 8GB:

```bash
cp config/rpi4b_8gb.yaml config/my_pi.yaml
```

Key settings to customise:

```yaml
customization:
  hostname: my-pi

  ssh:
    enabled: true          # enable SSH on first boot

  wifi:
    enabled: true          # enable WiFi
    ssid: "MyNetwork"
    password: "s3cret"
    country: US

  user:
    name: pi
    # generate with: openssl passwd -6 yourpassword
    password_hash: "$6$..."

  locale:
    timezone: America/New_York
    keyboard_layout: us
    language: en_US.UTF-8
```

See `config/template.yaml` for all available options with documentation.

### 3. Customize the image

**Option A — let the tool mount the image** (requires root):

```bash
sudo python3 customize_image.py raspios.img --config config/my_pi.yaml
```

**Option B — point the tool at an already-mounted image** (no root for this step):

```bash
# mount manually first, then:
python3 customize_image.py raspios.img \
    --no-mount --boot /mnt/boot --config config/my_pi.yaml
```

### 4. List available SD card devices

```bash
python3 flash_sd.py raspios.img
```

### 5. Flash to SD card (requires root)

```bash
sudo python3 flash_sd.py raspios.img --device /dev/sdb
```

The tool will display a confirmation prompt before writing. Use `--yes` to skip it in scripts.

## Project structure

```
pi-automation/
├── customize_image.py      # CLI: customize a Raspberry Pi OS image
├── flash_sd.py             # CLI: flash an image to an SD card
├── pi_automation/
│   ├── config.py           # configuration dataclasses + YAML loading
│   ├── customize.py        # image customization logic (ImageCustomizer, ImageMounter)
│   └── flash.py            # SD card flashing logic (validate, flash)
├── config/
│   ├── rpi4b_8gb.yaml      # ready-to-use config for Raspberry Pi 4B 8GB
│   └── template.yaml       # fully-documented template for any Pi variant
├── tests/
│   ├── test_config.py
│   ├── test_customize.py
│   └── test_flash.py
├── requirements.txt
└── requirements-dev.txt
```

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Generating a password hash

```bash
openssl passwd -6 yourpassword
```

Paste the output into `password_hash` in your YAML config.

## Supported devices

| Device | `device` value | Recommended `arch` |
|---|---|---|
| Raspberry Pi 4B | `rpi4b` | `arm64` |
| Raspberry Pi 3 | `rpi3` | `arm64` |
| Raspberry Pi Zero 2W | `rpizero2w` | `arm64` |
| Raspberry Pi Zero | `rpizero` | `armhf` |
| Raspberry Pi Pico | `rpipico` | n/a |
