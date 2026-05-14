# mycloverOS Architecture

## Overview

mycloverOS is a custom Debian-based Linux distribution that serves as the foundation for the MyClover.Tech CloverStack platform. Every Citadel appliance, CloverStick bootable USB, and self-hosted deployment runs mycloverOS.

```
+------------------------------------------------------------------+
|                        mycloverOS                                |
|                                                                  |
|  +-------------------+  +--------------------+  +--------------+ |
|  |  Linux Kernel     |  |  Systemd           |  |  NetworkMgr  | |
|  |  (Debian Bookworm)|  |  (init + services) |  |  + WireGuard | |
|  +-------------------+  +--------------------+  +--------------+ |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  |                    Docker Engine                           |  |
|  |  +----------+ +----------+ +----------+ +----------+      |  |
|  |  | NetMon   | | Sentry   | | Vault    | | Chappie  |      |  |
|  |  | (Zabbix) | | Log      | | warden   | | (Ollama) |      |  |
|  |  +----------+ +----------+ +----------+ +----------+      |  |
|  |  +----------+ +----------+ +----------+ +----------+      |  |
|  |  | Clover   | | Clover   | | Clover   | | Stream   |      |  |
|  |  | Media    | | Sign     | | POS      | | Server   |      |  |
|  |  +----------+ +----------+ +----------+ +----------+      |  |
|  |  +----------+ +------------------------------------------+ |  |
|  |  | Clover   | | CloverApps (user-installed via market)    | |  |
|  |  | Market   | | [App A] [App B] [App C] ...               | |  |
|  |  | (:8090)  | +------------------------------------------+ |  |
|  |  +----------+                                              |  |
|  |                                                            |  |
|  |  +----------+ +----------+                                 |  |
|  |  | Traefik  | | Portainer|  (reverse proxy + management)   |  |
|  |  +----------+ +----------+                                 |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  |  Ollama AI Engine (native, GPU-accelerated)                |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  |  myclover-desktop (KDE/GNOME/XFCE/Cinnamon or headless)   |  |
|  +-----------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## Layer Breakdown

### Layer 1: Base OS
- Debian Bookworm (stable) base
- Minimal package set — no unnecessary services
- Hardened: AppArmor, fail2ban, UFW firewall
- Custom kernel config (future: optimized for NAS/appliance workloads)

### Layer 2: Docker Runtime
- All CloverStack modules run as Docker containers
- Traefik handles reverse proxy + TLS termination
- Portainer provides web-based container management
- `cloverstack` Docker network for inter-service communication

### Layer 3: CloverStack Modules
- Each module = Docker Compose stack in `/opt/cloverstack/modules/<name>/`
- Managed by `cloverstack-ctl` CLI tool
- Enable/disable per deployment
- Shared data in `/var/lib/cloverstack/`

### Layer 3.5: CloverMarket (App Marketplace)
- On-device app marketplace: browse, install, update, remove CloverApps
- Marketplace server runs as Docker container on port 8090
- CLI: `clovermarket-ctl` (or `cloverstack-ctl market`)
- Each app = Docker image + `cloverapp.yml` manifest + optional `wizard.yml`
- Theme engine: 5 built-in `.clover-theme` files (40 CSS tokens each)
- Startup wizard framework: step-by-step setup UI for each app
- CloverCoin digital wallet for in-marketplace transactions
- Registry syncs from `market.myclover.tech` or works offline
- See [docs/CLOVERMARKET.md](CLOVERMARKET.md) for full details

### Layer 4: AI Engine
- Ollama runs natively (not containerized) for GPU access
- Serves all modules that need AI (Chappie, CloverDesign, CloverBot, etc.)
- Model management via `ollama` CLI
- Auto-detects GPU (NVIDIA CUDA, AMD ROCm)

### Layer 5: Desktop (Optional)
- myclover-desktop package adds branded DE
- KDE Plasma (default), GNOME, XFCE, Cinnamon options
- Headless mode for servers/appliances

## Boot Flow

```
Power On
  → GRUB (mycloverOS themed)
    → Linux Kernel
      → Systemd
        → Network Manager
        → Docker Engine
        → Ollama AI Engine
        → myclover-provision (first boot only)
          → Pull containers
          → Configure modules
          → Generate machine identity
          → Setup firewall
        → CloverStack modules (enabled)
        → myclover-desktop (if installed)
```

## Filesystem Layout

```
/
├── etc/
│   ├── myclover/           # CloverStack configuration
│   │   ├── distro.conf     # Distribution settings
│   │   ├── release         # OS release info
│   │   ├── machine-id      # Unique machine identity
│   │   └── modules.d/      # Module enable/disable flags
│   └── os-release          # Standard OS identification
├── opt/
│   ├── cloverstack/        # CloverStack application root
│   │   ├── modules/        # Docker Compose stacks per module
│   │   │   └── clovermarket/  # Marketplace server module
│   │   ├── themes/         # Theme engine
│   │   │   ├── builtin/    # 5 built-in .clover-theme files
│   │   │   └── custom/     # User-imported themes
│   │   ├── traefik/        # Reverse proxy config
│   │   ├── data/           # Shared application data
│   │   ├── config/         # Shared configuration
│   │   └── backups/        # Local backup storage
│   └── clovermarket/       # CloverMarket data
│       ├── apps/           # Installed CloverApps
│       ├── cache/          # Registry cache
│       └── wizards/        # Shared wizard resources
├── var/
│   ├── lib/cloverstack/    # Persistent module state
│   ├── lib/clovermarket/   # Marketplace state (wallet, etc.)
│   └── log/cloverstack/    # Centralized logs
└── usr/
    ├── local/bin/          # mycloverOS scripts
    │   ├── cloverstack-ctl
    │   ├── clovermarket-ctl  # Marketplace CLI
    │   ├── myclover-install
    │   ├── myclover-provision
    │   └── myclover-update
    └── share/myclover/     # Branding, themes, wallpapers
```

## Networking

- **NetworkManager** — primary network management
- **WireGuard** — VPN tunnels and CloverMesh interconnects
- **UFW** — simple firewall management
- **Traefik** — HTTP/HTTPS reverse proxy for all web services
- **Avahi** — mDNS/DNS-SD for local service discovery

## Security Model

1. Minimal attack surface (no unnecessary packages/services)
2. AppArmor mandatory access control
3. fail2ban intrusion prevention
4. UFW firewall (default deny inbound)
5. Docker container isolation
6. WireGuard encrypted tunnels
7. Per-module access control (Traefik middleware)
8. Auto-updates via `myclover-update`
