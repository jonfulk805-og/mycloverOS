# 🖥️ CloverDesktop

**Containerized desktop environments for mycloverOS.**

CloverDesktop runs full desktop environments (XFCE, KDE, MATE, i3, etc.) inside Docker containers, accessible via any web browser. Pick your desktop, customize it, export it, or sell it on the MCTVS Creator Market.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    mycloverOS Host                            │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Portainer (:9443)                      │ │
│  │   Deploy & manage desktop containers from the web UI     │ │
│  │   Browse templates → Click deploy → Desktop streaming    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ XFCE     │ │ KDE      │ │ i3       │ │ Creator       │  │
│  │ :6901    │ │ :6902    │ │ :6903    │ │ Desktop :6904 │  │
│  │ (free)   │ │ (free)   │ │ (free)   │ │ ($9.99/mo)    │  │
│  │ Webtop   │ │ Webtop   │ │ Webtop   │ │ MCTVS Market  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬────────┘  │
│       │            │            │               │            │
│  ┌────┴────────────┴────────────┴───────────────┴──────────┐│
│  │              Docker Engine (vfs driver)                   ││
│  │  Persistent volumes: ~/config per desktop                ││
│  │  GPU passthrough: /dev/dri when available                ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Traefik → TLS termination, subdomain routing            ││
│  │  xfce.local → :6901 | kde.local → :6902                 ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────┴───┐          ┌────┴───┐          ┌────┴───┐
    │ Laptop │          │ Tablet │          │ Phone  │
    │Browser │          │Browser │          │Browser │
    └────────┘          └────────┘          └────────┘
```

## Quick Start

### From CLI

```bash
# List available desktops
cloverdesktop list

# Start XFCE desktop (accessible at https://<ip>:6901)
cloverdesktop start xfce

# Start KDE on a specific port
cloverdesktop start kde work 6902

# Password-protected desktop
DESKTOP_PASSWORD=mysecret cloverdesktop start xfce

# Check status
cloverdesktop status

# Swap from XFCE to KDE (keeps same port + data)
cloverdesktop swap kde

# Stop a desktop
cloverdesktop stop xfce
```

### From Portainer (Web UI)

1. Open Portainer at `https://<server-ip>:9443`
2. Go to **App Templates** or **Custom Templates**
3. Browse CloverDesktop templates (XFCE, KDE, MATE, i3, etc.)
4. Click **Deploy** → configure port, password, resolution
5. Access your desktop at the assigned port

## Available Desktops

### Free Tier (Built-in)

| Desktop | Image Size | Memory | Best For |
|---------|-----------|--------|----------|
| **XFCE** | ~800MB | 512MB | Everyday use, remote admin |
| **KDE Plasma** | ~1.5GB | 1GB | Power users, customization |
| **MATE** | ~900MB | 512MB | Windows users, traditional layout |
| **i3** | ~500MB | 256MB | Developers, keyboard warriors |
| **Openbox** | ~400MB | 256MB | Kiosks, thin clients |
| **IceWM** | ~450MB | 256MB | Low-resource machines |
| **Budgie** | ~1.2GB | 768MB | Modern, clean aesthetic |

### Premium Tier

| Desktop | Image Size | Features |
|---------|-----------|----------|
| **Kasm Full Desktop** | ~2GB | GPU acceleration, audio, file transfer |
| **Kasm Chrome** | ~1GB | Isolated secure browser |
| **Kasm Firefox** | ~1GB | Private browsing environment |

### MCTVS Creator Market

Creators build, customize, and sell desktop environments:

| Example | Creator | Price | What's Included |
|---------|---------|-------|-----------------|
| Video Editor Pro | @filmmaker | $14.99 | DaVinci Resolve, OBS, FFmpeg |
| Developer Workstation | @devops | $9.99 | VS Code, Docker-in-Docker, tmux |
| Home Lab Admin | @sysadmin | $7.99 | Grafana, monitoring, network tools |
| Kids Learning Desktop | @teacher | $4.99/mo | Educational apps, parental controls |
| POS Terminal | @retailpro | $19.99/mo | Checkout, inventory, receipts |
| Music Studio | @producer | $12.99 | Ardour, JACK, synths, MIDI |

## Portable Desktops — Export & Import

### Export Your Desktop

```bash
# Export your customized XFCE desktop
cloverdesktop export xfce

# Export with a custom name
cloverdesktop export xfce default my-perfect-setup

# Output: /opt/cloverstack/modules/cloverdesktop/exports/my-perfect-setup.cloverdesktop.zst
```

The `.cloverdesktop` bundle contains:
- Docker image snapshot (your apps, configs, everything)
- Data volume backup (home directory, settings)
- Manifest with metadata

### Import on Another Machine

```bash
# Copy the bundle to the other CloverOS box, then:
cloverdesktop import my-perfect-setup.cloverdesktop.zst

# Start the imported desktop
cloverdesktop start xfce imported
```

### Share via USB

```bash
# Export to USB drive
cloverdesktop export xfce default my-setup
cp /opt/cloverstack/modules/cloverdesktop/exports/my-setup.cloverdesktop.zst /mnt/usb/

# On the other machine:
cloverdesktop import /mnt/usb/my-setup.cloverdesktop.zst
```

## MCTVS Creator Market

### For Creators — Build & Sell Desktops

The MCTVS (MyClover.Tech Vertical System) Creator Method for desktop environments:

```
┌─────────────────────────────────────────────────────┐
│              MCTVS Desktop Creator Flow              │
│                                                      │
│  1. START      cloverdesktop start xfce              │
│       ↓                                              │
│  2. CUSTOMIZE  Install apps, themes, configs         │
│       ↓        Add your tools, workflows, presets    │
│  3. EXPORT     cloverdesktop export xfce             │
│       ↓        Creates portable .cloverdesktop file  │
│  4. PUBLISH    cloverdesktop publish <file>          │
│       ↓        Set name, description, price          │
│  5. EARN       70% creator / 30% MCT revenue split   │
│                                                      │
│  Buyers: cloverdesktop market install <slug>         │
│  → License validates → Container pulls → Desktop!    │
└─────────────────────────────────────────────────────┘
```

#### Step by Step:

```bash
# 1. Start with a base desktop
cloverdesktop start xfce

# 2. Open in browser, install your apps, configure everything
#    https://<ip>:6901
#    - Install VS Code, Docker CLI, Node.js, Python
#    - Configure .bashrc, tmux, theme
#    - Set up wallpaper, panel layout, keyboard shortcuts

# 3. Export your masterpiece
cloverdesktop export xfce default developer-workstation

# 4. Publish to the MCTVS Creator Market
cloverdesktop publish /opt/cloverstack/modules/cloverdesktop/exports/developer-workstation.cloverdesktop.zst
#    → Set price: $9.99 one-time
#    → Set category: Development
#    → Revenue split: You get 70%

# 5. Users discover and install your desktop
#    cloverdesktop market browse
#    cloverdesktop market install developer-workstation
```

### For Buyers

```bash
# Browse available desktops
cloverdesktop market browse

# Purchase and install (payment via MCTVS/Stripe)
cloverdesktop market install video-editor-pro

# Start the purchased desktop
cloverdesktop start video-editor-pro video-editor-pro
```

### Licensing & Paywall

- Containers stored encrypted in MCTVS registry (not Docker Hub)
- Pull requires a valid license key tied to the buyer's CloverOS machine ID
- License validation on container start — no key, no desktop
- Subscription desktops validate monthly (30-day offline grace period)
- Containers signed by creator + countersigned by MyClover.Tech
- Revenue: 70% to creator, 30% to MyClover.Tech

## Multiple Desktops

Run multiple desktops simultaneously for different users or purposes:

```bash
# Work desktop on :6901
cloverdesktop start xfce work 6901

# Dev desktop on :6902
cloverdesktop start i3 dev 6902

# Kids desktop on :6903
DESKTOP_PASSWORD=kidssafe cloverdesktop start budgie kids 6903

# Check all running
cloverdesktop status
```

## GPU Acceleration

CloverDesktop auto-detects `/dev/dri` for GPU passthrough:

```bash
# GPU is auto-enabled if detected
cloverdesktop start kasm-desktop

# Check GPU status
cloverdesktop status
# → GPU passthrough: true (/dev/dri)
```

For Kasm images, GPU passthrough enables:
- Hardware-accelerated video playback
- WebGL / 3D graphics
- Gaming (Steam, Proton)
- CAD / 3D modeling
- Video editing (DaVinci Resolve)

## Configuration

Edit `/etc/myclover/cloverdesktop.conf`:

```bash
# Default desktop for new instances
CLOVERDESKTOP_DEFAULT="xfce"

# Resolution
CLOVERDESKTOP_RESOLUTION="1920x1080"

# Starting port range
CLOVERDESKTOP_PORT_START=6901

# MCTVS Creator Market
CLOVERDESKTOP_MCTVS_ENABLED=true
CLOVERDESKTOP_MCTVS_REGISTRY="https://market.myclover.tech/api/v1"

# Auto-start a desktop on boot
CLOVERDESKTOP_AUTOSTART="xfce"  # Set to "none" to disable

# Portainer template sync
CLOVERDESKTOP_PORTAINER_SYNC=true
```

## Firewall

CloverDesktop opens ports 6901-6920 by default. Adjust in:
- `/etc/myclover/firewall-rules.d/cloverdesktop.rules`
- Or via `ufw`: `ufw allow 6901:6920/tcp`

## Troubleshooting

### Desktop won't start
```bash
# Check Docker status
systemctl status docker

# Check logs
docker logs cloverdesktop-xfce-default

# CloverDesktop log
cat /var/log/cloverstack/cloverdesktop.log
```

### Black screen in browser
- Increase shared memory: container needs `--shm-size=2g` (default in cloverdesktop)
- Check resolution setting matches your display
- Try a different browser (Chrome recommended)

### Slow performance
- Check Docker storage driver: `docker info | grep Storage`
  - If `vfs`: expected on live-boot, install to disk for `overlay2`
  - After `myclover-install`, performance improves dramatically
- Allocate more RAM to the container
- Enable GPU passthrough for graphics-heavy work

### Export fails
- Ensure enough disk space (export ≈ 2x container size)
- Install `zstd` for compression: `apt install zstd`
