# Building mycloverOS

## Prerequisites

- **Ubuntu 24.04 LTS** (Noble) or **Debian 12** (Bookworm) — tested and supported
- Root access (live-build requires it)
- ~10 GB free disk space
- Internet connection (to download packages)

> **Note:** The build host can be Ubuntu 24.04 LTS. The target ISO is always Debian Bookworm-based.
> The build script auto-detects your live-build version and adjusts flags accordingly.

## Install Build Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    grub-pc-bin \
    grub-efi-amd64-bin \
    mtools \
    dosfstools \
    debian-archive-keyring
```

> **Ubuntu hosts:** The `debian-archive-keyring` package is required so debootstrap can verify Debian package signatures. Without it you'll get `keyring file not available` warnings.

## Build an ISO

```bash
# Clone the repo
git clone https://github.com/jonfulk805-og/mycloverOS.git
cd mycloverOS

# Build server edition (default)
sudo ./build.sh

# Or specify an edition
sudo ./build.sh server    # Headless, all CloverStack modules
sudo ./build.sh desktop   # KDE Plasma desktop + AI
sudo ./build.sh micro     # Lightweight XFCE for Puck/Edge
sudo ./build.sh kiosk     # Chromium kiosk for POS/signage

# Clean rebuild
sudo CLEAN=true ./build.sh server
```

Build output: `build/mycloverOS-<version>-<edition>-amd64.iso`

## Build Time

| Host | Edition | Time |
|------|---------|------|
| 4-core, 16 GB, SSD | Server | ~15 min |
| 4-core, 16 GB, SSD | Desktop | ~25 min |
| 8-core, 32 GB, NVMe | Server | ~8 min |
| GitHub Actions | Server | ~20 min |

## Write to USB

```bash
# Find your USB device
lsblk

# Write (replace /dev/sdX with your USB device)
sudo dd if=build/mycloverOS-0.1.0-server-amd64.iso of=/dev/sdX bs=4M status=progress
sync
```

## Verify ISO

```bash
sha256sum -c build/mycloverOS-0.1.0-server-amd64.iso.sha256
```

## CI/CD

GitHub Actions automatically builds the server ISO on every push to `main`. Tagged releases (`v*`) create GitHub Releases with downloadable ISOs.

To trigger a manual build of any edition, use the "Run workflow" button in the Actions tab.

## Customization

See [CUSTOMIZATION.md](CUSTOMIZATION.md) for how to fork and create your own mycloverOS variant.
