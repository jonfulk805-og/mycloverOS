# mycloverOS

<p align="center">
  <img src="branding/logo-banner.png" alt="mycloverOS" width="600">
</p>

**The operating system that powers CloverStack.**

mycloverOS is a custom Debian-based Linux distribution purpose-built for the [MyClover.Tech](https://myclover.tech) ecosystem. It ships on every Citadel appliance, powers the CloverStick bootable USB, and can be installed on any x86_64 hardware to instantly deploy the full CloverStack platform.

> *"The OS is the core genius. The hardware is a necessity. Customization is the secret sauce."*

---

## What You Get

- **Minimal, hardened Debian base** — no bloat, no telemetry, just what you need
- **CloverStack pre-installed** — NetMon, SentryLog, MyCloverVault, Chappie AI, and the full module suite
- **myclover-desktop** — branded desktop environment (KDE/GNOME/XFCE/Cinnamon or headless)
- **Ollama AI Engine** — local AI out of the box, GPU-accelerated when available
- **CloverMesh ready** — WireGuard mesh networking built in
- **Docker + Portainer** — containerized services with web management
- **Live boot + install** — boot from USB to try it, install to make it permanent
- **Auto-provisioning** — plug in, power on, CloverStack configures itself

## System Requirements

| Tier | CPU | RAM | Storage | Notes |
|------|-----|-----|---------|-------|
| Minimum | x86_64, 2 cores | 4 GB | 32 GB | Headless only, no AI |
| Recommended | x86_64, 4 cores | 16 GB | 128 GB | Desktop + basic AI (Phi-3) |
| Optimal | x86_64, 8+ cores | 32+ GB | 512+ GB | Full suite + 13B models |
| GPU AI | + NVIDIA/AMD GPU | + 8 GB VRAM | — | 70B models, real-time inference |

## Quick Start

### Boot from USB (CloverStick)

```bash
# Write the ISO to a USB drive (replace /dev/sdX)
sudo dd if=mycloverOS-latest.iso of=/dev/sdX bs=4M status=progress
sync
```

Boot from the USB. CloverStack starts automatically. No installation required.

### Build from Source

```bash
# Clone this repo
git clone https://github.com/jonfulk805-og/mycloverOS.git
cd mycloverOS

# Install build dependencies (Debian/Ubuntu host)
sudo apt install live-build debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin

# Build the ISO
sudo ./build.sh

# Output: build/mycloverOS-<version>-amd64.iso
```

### Install to Disk

Boot the live ISO, then:

```bash
sudo myclover-install
```

The installer guides you through disk selection, partitioning, and initial configuration.

## Repository Structure

```
mycloverOS/
├── build.sh                    # Master build script
├── config/
│   ├── distro.conf             # Distribution settings (name, version, base)
│   ├── live-build/             # Debian live-build configuration
│   │   ├── auto/               # Auto-configuration scripts
│   │   ├── hooks/              # Build hooks (chroot + binary)
│   │   ├── includes.chroot/    # Files overlaid into the live filesystem
│   │   ├── package-lists/      # Package selections by category
│   │   └── preseed/            # Automated install answers
│   └── calamares/              # Graphical installer config (optional)
├── packages/
│   ├── base.list               # Core system packages
│   ├── desktop.list            # Desktop environment packages
│   ├── cloverstack.list        # CloverStack service packages
│   ├── ai.list                 # AI/ML packages (Ollama, models)
│   ├── networking.list         # Network tools + WireGuard + mesh
│   └── hardware.list           # Driver + firmware packages
├── overlay/                    # Root filesystem overlay
│   ├── etc/
│   │   ├── myclover/           # CloverStack configuration
│   │   ├── skel/               # Default user home template
│   │   ├── systemd/system/     # Custom systemd units
│   │   └── default/grub        # GRUB configuration
│   ├── opt/cloverstack/        # CloverStack application root
│   └── usr/share/myclover/     # Branding, wallpapers, themes
├── scripts/
│   ├── myclover-install        # Disk installer
│   ├── myclover-provision      # First-boot auto-provisioning
│   ├── myclover-update         # System + CloverStack updater
│   └── cloverstack-setup       # CloverStack service orchestrator
├── branding/
│   ├── logo-banner.png         # Repo banner image
│   ├── wallpapers/             # Desktop wallpapers
│   ├── plymouth/               # Boot splash theme
│   ├── grub/                   # GRUB bootloader theme
│   └── icons/                  # Application icons
├── docs/
│   ├── ARCHITECTURE.md         # System architecture overview
│   ├── BUILDING.md             # Detailed build instructions
│   ├── HARDWARE.md             # Supported hardware reference
│   └── CUSTOMIZATION.md        # How to fork + customize
├── .github/
│   └── workflows/
│       └── build-iso.yml       # CI/CD: automated ISO builds
├── LICENSE                     # GPLv3
└── CHANGELOG.md                # Release history
```

## Editions

| Edition | Desktop | AI | Target |
|---------|---------|----|---------| 
| **Server** | Headless | Ollama CLI | Citadel NAS, Rack, data center |
| **Desktop** | KDE Plasma | Ollama + ComfyUI | Workstations, Field Laptop |
| **Micro** | XFCE | Ollama (small models) | Puck, Edge, Edge Pro |
| **Kiosk** | Chromium Kiosk | — | POS terminals, signage, media |

## CloverStack Modules

All modules are pre-installed and managed via `cloverstack-ctl`:

| Module | Description |
|--------|-------------|
| NetMon | Network monitoring (Zabbix) |
| SentryLog | Log management (Graylog + Wazuh) |
| MyCloverVault | Password manager (Vaultwarden) |
| Chappie AI | Built-in AI assistant (Ollama) |
| **CloverMarket** | **On-device app marketplace with themes & startup wizards** |
| CloverMedia | Smart TV + streaming + DJ |
| CloverSign | Digital signage |
| CloverGuard | Web proxy + content filter |
| CloverMine | Crypto mining (opt-in) |
| CloverPOS | Point of sale |
| CloverDesign | AI design studio |
| CloverBot | AI support chatbot |
| CloverDrone | UAV control |
| CloverMesh | Distributed node mesh |
| CloverMesh Radio | LoRa mesh comms |
| StreamServer | Live streaming platform |

```bash
# Enable a module
sudo cloverstack-ctl enable netmon

# Disable a module
sudo cloverstack-ctl disable clovermedia

# Check status
sudo cloverstack-ctl status

# CloverMarket: browse & install apps
clovermarket-ctl browse
clovermarket-ctl install <app-id>
clovermarket-ctl theme apply midnight
```

See [docs/CLOVERMARKET.md](docs/CLOVERMARKET.md) for the full CloverMarket guide.

## Contributing

mycloverOS is built on the shoulders of incredible open-source projects. We believe in giving back.

### Open Source Credits

| Project | License | What We Use It For |
|---------|---------|-------------------|
| [Debian](https://debian.org) | DFSG | Base distribution |
| [live-build](https://live-team.pages.debian.net/live-manual/) | GPL-3.0 | ISO build system |
| [Zabbix](https://zabbix.com) | GPL-2.0 | NetMon monitoring |
| [Graylog](https://graylog.org) | SSPL | SentryLog log management |
| [Wazuh](https://wazuh.com) | GPL-2.0 | SentryLog security |
| [Vaultwarden](https://github.com/dani-garcia/vaultwarden) | AGPL-3.0 | MyCloverVault |
| [Ollama](https://ollama.com) | MIT | AI Engine |
| [WireGuard](https://wireguard.com) | GPL-2.0 | CloverMesh VPN |
| [Docker](https://docker.com) | Apache-2.0 | Container runtime |
| [Portainer](https://portainer.io) | Zlib | Container management |
| [ERPNext](https://erpnext.com) | GPL-3.0 | CloverPOS |
| [Kodi](https://kodi.tv) | GPL-2.0 | CloverMedia |
| [Mixxx](https://mixxx.org) | GPL-2.0 | DJ Mode |
| [Screenly OSE](https://www.screenly.io) | AGPL-3.0 | CloverSign |
| [RustDesk](https://rustdesk.com) | AGPL-3.0 | Remote access |

*Thank you to every contributor who makes open source possible.* :four_leaf_clover:

### How to Contribute

1. Fork this repo
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

mycloverOS is licensed under the [GNU General Public License v3.0](LICENSE).

The CloverStack platform modules may have additional licensing terms. See individual module documentation for details.

---

<p align="center">
  <strong>MyClover.Tech</strong> — Own Your Stack<br>
  <a href="https://myclover.tech">Website</a> · <a href="https://github.com/jonfulk805-og">GitHub</a> · <a href="https://myclover.tech/cloverbot">Support</a>
</p>
