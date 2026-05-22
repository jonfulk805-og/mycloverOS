# CloverStack Module Deployment Guide

> **CloverOS R1** — Complete reference for deploying every CloverStack module

Each module is a Docker Compose stack managed by `cloverstack-ctl`. This guide covers prerequisites, deployment, first-login setup, and common issues for every module.

---

## Table of Contents

- [Core Infrastructure](#core-infrastructure)
  - [Portainer (Container Management)](#portainer-container-management)
  - [Traefik (Reverse Proxy)](#traefik-reverse-proxy)
  - [Ollama (AI Engine)](#ollama-ai-engine)
- [Default Modules](#default-modules)
  - [NetMon — Network Monitoring (Zabbix)](#netmon--network-monitoring)
  - [SentryLog — Security & Log Management](#sentrylog--security--log-management)
  - [MyClover Vault — Password Manager](#myclover-vault--password-manager)
  - [Chappie AI — Local AI Assistant](#chappie-ai--local-ai-assistant)
  - [CloverMarket — App Marketplace](#clovermarket--app-marketplace)
- [Optional Modules](#optional-modules)
  - [CloverBot — AI Customer Support](#cloverbot--ai-customer-support)
  - [CloverDesign — AI Design Studio](#cloverdesign--ai-design-studio)
  - [CloverDesktop — Containerized GUI](#cloverdesktop--containerized-gui)
  - [CloverDrone — UAV Control](#cloverdrone--uav-control)
  - [CloverGuard — DNS Filtering & Proxy](#cloverguard--dns-filtering--proxy)
  - [CloverMedia — Smart TV & Music](#clovermedia--smart-tv--music)
  - [CloverMesh — WireGuard Mesh Networking](#clovermesh--wireguard-mesh-networking)
  - [CloverMesh Radio — LoRa Communications](#clovermesh-radio--lora-communications)
  - [CloverMine — Crypto Mining](#clovermine--crypto-mining)
  - [CloverPOS — Point of Sale & ERP](#cloverpos--point-of-sale--erp)
  - [CloverSign — Digital Signage](#cloversign--digital-signage)
  - [StreamServer — Live Streaming](#streamserver--live-streaming)
- [Module Management Commands](#module-management-commands)

---

## Core Infrastructure

These services are deployed automatically during first-boot provisioning.

---

### Portainer (Container Management)

| | |
|---|---|
| **Port** | `9443` (HTTPS, self-signed cert) |
| **URL** | `https://<ip>:9443` |
| **Image** | `portainer/portainer-ce:latest` |
| **Network** | `cloverstack` |

#### Access

Navigate to `https://<ip>:9443`. Accept the self-signed certificate warning.

#### First-Login Setup

1. Create your admin username and password
2. Click **"Get Started"** to connect to the local Docker environment
3. You'll see all CloverStack containers, networks, and volumes

#### ⚠️ Timeout Issue

Portainer locks itself if you don't create an admin account within ~5 minutes:

```
"Your Portainer instance timed out for security purposes."
```

**Fix:**
```bash
sudo docker restart portainer
```

Then immediately navigate to the URL and create your admin account.

---

### Traefik (Reverse Proxy)

| | |
|---|---|
| **Ports** | `80` (HTTP), `443` (HTTPS), `8082` (Dashboard) |
| **URL** | `http://<ip>:8082` (dashboard) |
| **Image** | `traefik:v3.0` |
| **Config** | `/opt/cloverstack/traefik/config/` |

#### How It Works

Traefik automatically discovers Docker containers with the label `traefik.enable=true` and routes traffic to them. It handles:
- HTTP → HTTPS redirect
- TLS termination
- Path-based routing to modules

#### Manual Start

If Traefik shows as "Created" but not running:
```bash
sudo docker start traefik
sudo docker logs traefik
```

#### Adding Custom Routes

Edit `/opt/cloverstack/traefik/config/dynamic/cloverstack.yml` to add custom routing rules.

---

### Ollama (AI Engine)

| | |
|---|---|
| **Port** | `11434` (API) |
| **URL** | `http://localhost:11434` |
| **Install** | Native (not containerized, for GPU access) |

#### Check Status

```bash
sudo systemctl status ollama
ollama list          # Show installed models
```

#### Model Management

```bash
# Pull a model
ollama pull llama3.1

# Pull Dolphin-X1 (CloverOS default for 16GB+ systems)
ollama pull hf.co/dphn/Dolphin-X1-8B-GGUF:Q4_K_M

# Interactive chat
ollama run llama3.1

# API call
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1",
  "prompt": "What is CloverOS?"
}'
```

#### GPU Detection

Ollama auto-detects NVIDIA (CUDA) and AMD (ROCm) GPUs. Verify with:
```bash
ollama ps    # Shows which device (CPU/GPU) is active
```

---

## Default Modules

Enabled automatically on first boot. Start them with `cloverstack-ctl`.

---

### NetMon — Network Monitoring

| | |
|---|---|
| **Port** | `8081` (Web UI), `10051` (Zabbix Server) |
| **URL** | `http://<ip>:8081` |
| **Upstream** | Zabbix 7.0 |
| **RAM** | 1 GB minimum |
| **Disk** | 10 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl start netmon
```

#### First-Login

1. Navigate to `http://<ip>:8081`
2. Default credentials: `Admin` / `zabbix`
3. **Change the default password immediately**

#### What It Monitors

- Host uptime and availability
- CPU, memory, disk utilization
- Network interface traffic
- Docker container health
- Custom SNMP/IPMI checks

#### Add a Host

1. Go to **Data collection → Hosts → Create host**
2. Enter hostname and IP
3. Assign a template (e.g., "Linux by Zabbix agent")
4. Click **Add**

#### Services

| Container | Role |
|-----------|------|
| `zabbix-server` | Monitoring engine |
| `zabbix-web` | Web dashboard |
| `zabbix-agent` | Local agent |
| `zabbix-postgres` | Database |

---

### SentryLog — Security & Log Management

| | |
|---|---|
| **Port** | `9000` (Graylog), `1514` (Syslog), `12201` (GELF), `55000` (Wazuh API) |
| **URL** | `http://<ip>:9000` |
| **Upstream** | Graylog 6.0 + Wazuh 4.9 |
| **RAM** | 2 GB minimum |
| **Disk** | 20 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl start sentrylog
```

#### First-Login

1. Navigate to `http://<ip>:9000`
2. Default Graylog credentials: `admin` / `admin`
3. **Change the default password immediately**

#### Log Sources

SentryLog accepts logs via:
- **Syslog** (port 1514) — network devices, Linux servers
- **GELF** (port 12201) — Docker containers, applications
- **Wazuh agents** (port 1515 registration) — endpoint security

#### Send Docker Logs to SentryLog

Add to any Docker Compose service:
```yaml
logging:
  driver: gelf
  options:
    gelf-address: "udp://localhost:12201"
    tag: "my-service"
```

#### Services

| Container | Role |
|-----------|------|
| `graylog` | Log search & dashboard |
| `wazuh-manager` | Security event manager |
| `graylog-opensearch` | Search engine |
| `graylog-mongo` | Metadata database |

---

### MyClover Vault — Password Manager

| | |
|---|---|
| **Port** | `8082` (Web), `3012` (WebSocket) |
| **URL** | `http://<ip>:8082` |
| **Upstream** | Vaultwarden |
| **RAM** | 256 MB minimum |
| **Disk** | 2 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl start myclover-vault
```

#### First-Login

1. Navigate to `http://<ip>:8082`
2. Click **"Create Account"**
3. Set your master email and password

#### Browser Extension

Install the [Bitwarden browser extension](https://bitwarden.com/download/) and configure the server URL:
```
http://<ip>:8082
```

#### Services

| Container | Role |
|-----------|------|
| `vaultwarden` | Password vault server |

---

### Chappie AI — Local AI Assistant

| | |
|---|---|
| **Port** | `8083` |
| **URL** | `http://<ip>:8083` |
| **Upstream** | Open WebUI + Ollama |
| **RAM** | 4 GB minimum (8 GB+ recommended) |
| **Disk** | 20 GB minimum |
| **GPU** | Recommended for fast inference |

#### Deploy

```bash
sudo cloverstack-ctl start chappie
```

#### First-Login

1. Navigate to `http://<ip>:8083`
2. Create your account
3. Select an AI model from the model picker (top of chat)
4. Start chatting

#### Model Selection

Chappie uses whatever models are installed in Ollama:
```bash
ollama list                    # See available models
ollama pull llama3.1           # Add a model
```

Models appear automatically in Chappie's UI.

#### Services

| Container | Role |
|-----------|------|
| `open-webui` | Chat interface |

> **Note:** Chappie connects to the host's Ollama instance (port 11434), not a containerized one.

---

### CloverMarket — App Marketplace

| | |
|---|---|
| **Port** | `8095` |
| **URL** | `http://<ip>:8095` |
| **Upstream** | CloverMarket (custom) |
| **RAM** | 512 MB minimum |
| **Disk** | 5 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl start clovermarket
```

#### What It Does

- Browse and install CloverApps from the marketplace registry
- Manage installed apps (update, remove, configure)
- Theme engine with 5 built-in themes
- CloverCoin digital wallet for marketplace transactions

#### CLI

```bash
clovermarket-ctl list          # List available apps
clovermarket-ctl install <app> # Install an app
clovermarket-ctl update <app>  # Update an app
clovermarket-ctl remove <app>  # Remove an app
clovermarket-ctl theme list    # List themes
clovermarket-ctl theme apply <theme>  # Apply a theme
```

#### Services

| Container | Role |
|-----------|------|
| `clovermarket` | Marketplace server |

---

## Optional Modules

Enable and deploy as needed.

---

### CloverBot — AI Customer Support

| | |
|---|---|
| **Port** | `8089` |
| **URL** | `http://<ip>:8089` |
| **Upstream** | LibreChat |
| **RAM** | 1 GB minimum |
| **Disk** | 10 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable cloverbot
sudo cloverstack-ctl start cloverbot
```

#### First-Login

1. Navigate to `http://<ip>:8089`
2. Create an account
3. Configure AI providers (Ollama is auto-detected)

#### Services

| Container | Role |
|-----------|------|
| `librechat` | Chat application |
| `librechat-mongo` | Database |

---

### CloverDesign — AI Design Studio

| | |
|---|---|
| **Port** | `8088` |
| **URL** | `http://<ip>:8088` |
| **Upstream** | ComfyUI |
| **RAM** | 4 GB minimum |
| **Disk** | 50 GB minimum |
| **GPU** | *Required* |

#### Deploy

```bash
sudo cloverstack-ctl enable cloverdesign
sudo cloverstack-ctl start cloverdesign
```

#### Requirements

A CUDA or ROCm-capable GPU is required. ComfyUI will not run on CPU alone.

#### First-Login

1. Navigate to `http://<ip>:8088`
2. The node-based workflow editor loads automatically
3. Load a workflow or build one from scratch

#### Services

| Container | Role |
|-----------|------|
| `comfyui` | AI image generation |

---

### CloverDesktop — Containerized GUI

| | |
|---|---|
| **Port** | `3000` (Web), `3001` (VNC) |
| **URL** | `https://<ip>:3000` |
| **Upstream** | LinuxServer Webtop (KasmVNC) |
| **RAM** | 2 GB minimum (4 GB+ for KDE) |

#### Deploy

```bash
# Using the CLI
sudo cloverdesktop deploy kde --port 3000

# Or via cloverstack-ctl
sudo cloverstack-ctl enable cloverdesktop
sudo cloverstack-ctl start cloverdesktop
```

#### Available Desktops

| Desktop | RAM | Best For |
|---------|-----|----------|
| `xfce` | 1 GB | Low-resource devices (Puck) |
| `mate` | 2 GB | Balanced |
| `kde` | 4 GB | Full desktop experience |

Hardware auto-selection: systems with <2 GB get XFCE, 2-4 GB get MATE, 4 GB+ get KDE.

#### Access

Open `https://<ip>:3000` in a browser. Full Linux desktop runs in the browser tab via KasmVNC.

#### Export & Share

```bash
sudo cloverdesktop export my-desktop    # Export as Docker image
sudo cloverdesktop list                 # List running desktops
sudo cloverdesktop stop kde             # Stop a desktop
```

---

### CloverDrone — UAV Control

| | |
|---|---|
| **Ports** | `8090` (Web), `14550` (MAVLink), `8554` (RTSP) |
| **URL** | `http://<ip>:8090` |
| **Upstream** | MAVProxy + MediaMTX |
| **RAM** | 1 GB minimum |
| **Disk** | 5 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable cloverdrone
sudo cloverstack-ctl start cloverdrone
```

#### Connect a Drone

1. Connect your flight controller via USB or configure UDP MAVLink on port `14550`
2. Open `http://<ip>:8090` for the web dashboard
3. RTSP video feed available at `rtsp://<ip>:8554/drone`

#### Services

| Container | Role |
|-----------|------|
| `mavproxy` | MAVLink proxy |
| `cloverdrone-web` | Web dashboard |
| `cloverdrone-video` | Video relay (MediaMTX) |

---

### CloverGuard — DNS Filtering & Proxy

| | |
|---|---|
| **Ports** | `8085` (Pi-hole Admin), `53` (DNS), `3128` (Squid) |
| **URL** | `http://<ip>:8085/admin` |
| **Upstream** | Pi-hole + Squid |
| **RAM** | 512 MB minimum |
| **Disk** | 5 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable cloverguard
sudo cloverstack-ctl start cloverguard
```

#### First-Login

1. Navigate to `http://<ip>:8085/admin`
2. Default Pi-hole password is shown in the container logs:
   ```bash
   sudo docker logs pihole 2>&1 | grep "password"
   ```

#### Configure DNS

Point your network's DHCP to use `<cloverstack-ip>` as the DNS server. All DNS queries route through Pi-hole for ad/tracker blocking.

#### Services

| Container | Role |
|-----------|------|
| `pihole` | DNS filtering |
| `squid` | Web proxy |

---

### CloverMedia — Smart TV & Music

| | |
|---|---|
| **Ports** | `8096` (Jellyfin), `4533` (Navidrome), `1900` (DLNA) |
| **URL** | `http://<ip>:8096` (video), `http://<ip>:4533` (music) |
| **Upstream** | Jellyfin + Navidrome |
| **RAM** | 1 GB minimum |
| **Disk** | 10 GB minimum (+ media storage) |

#### Deploy

```bash
sudo cloverstack-ctl enable clovermedia
sudo cloverstack-ctl start clovermedia
```

#### First-Login (Jellyfin)

1. Navigate to `http://<ip>:8096`
2. Follow the setup wizard
3. Add media libraries (point to `/media/videos`, `/media/movies`, etc.)

#### First-Login (Navidrome)

1. Navigate to `http://<ip>:4533`
2. Create admin account
3. Music library scans from `/media/music`

#### DLNA

Jellyfin broadcasts via DLNA (port 1900). Smart TVs on the same network will auto-discover it.

#### Services

| Container | Role |
|-----------|------|
| `jellyfin` | Video streaming |
| `navidrome` | Music streaming |

---

### CloverMesh — WireGuard Mesh Networking

| | |
|---|---|
| **Ports** | `8091` (API), `8092` (Web UI), `51821` (WireGuard) |
| **URL** | `http://<ip>:8092` |
| **Upstream** | Netmaker |
| **RAM** | 512 MB minimum |
| **Disk** | 5 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable clovermesh
sudo cloverstack-ctl start clovermesh
```

#### First-Login

1. Navigate to `http://<ip>:8092`
2. Create your admin account
3. Create a network (e.g., "clover-mesh")
4. Add nodes by installing the Netclient on each device

#### Add a Node

On each CloverOS device you want to mesh:
```bash
# Install netclient
curl -sL https://raw.githubusercontent.com/gravitl/netmaker/master/scripts/netclient-install.sh | sudo bash

# Join the mesh
sudo netclient join -t <enrollment-token>
```

#### Services

| Container | Role |
|-----------|------|
| `netmaker-server` | Mesh controller |
| `netmaker-mq` | Message queue |
| `netmaker-ui` | Web dashboard |

---

### CloverMesh Radio — LoRa Communications

| | |
|---|---|
| **Ports** | `8093` (Web), `1884` (MQTT) |
| **URL** | `http://<ip>:8093` |
| **Upstream** | Meshtastic |
| **RAM** | 256 MB minimum |
| **Disk** | 2 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable clovermesh-radio
sudo cloverstack-ctl start clovermesh-radio
```

#### Requirements

A Meshtastic-compatible LoRa radio connected via USB (e.g., Heltec, LILYGO T-Beam, RAK).

#### First-Login

1. Navigate to `http://<ip>:8093`
2. The web UI shows connected radios and mesh topology
3. MQTT bridge on port 1884 for integration with other CloverStack modules

#### Services

| Container | Role |
|-----------|------|
| `meshtastic-web` | Web interface |
| `meshtastic-mqtt` | MQTT bridge |

---

### CloverMine — Crypto Mining

| | |
|---|---|
| **Port** | `8086` |
| **URL** | `http://<ip>:8086` |
| **Upstream** | XMRig |
| **RAM** | 512 MB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable clovermine
sudo cloverstack-ctl start clovermine
```

> **⚠️ Opt-in only.** CloverMine never runs unless explicitly enabled.

#### Configure

Edit the mining config before starting:
```bash
sudo nano /opt/cloverstack/modules/clovermine/config.json
```

Set your wallet address and pool.

#### Services

| Container | Role |
|-----------|------|
| `xmrig` | Mining engine |
| `clovermine-dashboard` | Stats dashboard |

---

### CloverPOS — Point of Sale & ERP

| | |
|---|---|
| **Port** | `8087` |
| **URL** | `http://<ip>:8087` |
| **Upstream** | ERPNext v15 |
| **RAM** | 4 GB minimum |
| **Disk** | 20 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable cloverpos
sudo cloverstack-ctl start cloverpos
```

> **Note:** First start takes 5-10 minutes — ERPNext initializes its database.

#### First-Login

1. Navigate to `http://<ip>:8087`
2. Default credentials: `Administrator` / `admin`
3. Follow the setup wizard (company name, currency, fiscal year)
4. **Change the default password immediately**

#### Services

| Container | Role |
|-----------|------|
| `erpnext` | Web application |
| `erpnext-worker` | Background jobs |
| `erpnext-scheduler` | Scheduled tasks |
| `erpnext-mariadb` | Database |
| `erpnext-redis-cache` | Cache |
| `erpnext-redis-queue` | Job queue |

---

### CloverSign — Digital Signage

| | |
|---|---|
| **Port** | `8084` |
| **URL** | `http://<ip>:8084` |
| **Upstream** | Anthias |
| **RAM** | 512 MB minimum |
| **Disk** | 5 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable cloversign
sudo cloverstack-ctl start cloversign
```

#### First-Login

1. Navigate to `http://<ip>:8084`
2. Add media assets (images, videos, web pages)
3. Create playlists with scheduling
4. Connect display screens to the viewer URL

#### Services

| Container | Role |
|-----------|------|
| `anthias-server` | Signage manager |
| `anthias-viewer` | Display renderer |

---

### StreamServer — Live Streaming

| | |
|---|---|
| **Ports** | `8094` (Web), `1935` (RTMP), `8555` (RTSP), `9710` (SRT) |
| **URL** | `http://<ip>:8094` |
| **Upstream** | Owncast + MediaMTX |
| **RAM** | 1 GB minimum |
| **Disk** | 20 GB minimum |

#### Deploy

```bash
sudo cloverstack-ctl enable streamserver
sudo cloverstack-ctl start streamserver
```

#### Start Streaming

1. Open OBS Studio (or any RTMP encoder)
2. Set the stream URL to: `rtmp://<ip>:1935/live`
3. Set the stream key to: `cloverstream` (change in settings)
4. Click "Start Streaming"
5. Viewers watch at: `http://<ip>:8094`

#### Multi-Protocol

| Protocol | URL | Use Case |
|----------|-----|----------|
| RTMP | `rtmp://<ip>:1935/live` | OBS / encoder ingest |
| RTSP | `rtsp://<ip>:8555/stream` | IP cameras |
| SRT | `srt://<ip>:9710` | Low-latency ingest |
| HLS | `http://<ip>:8094` | Browser playback |

#### Services

| Container | Role |
|-----------|------|
| `owncast` | Streaming server + web player |
| `mediamtx` | Multi-protocol relay |

---

## Module Management Commands

### Quick Reference

```bash
# Status
cs-status                              # All modules
sudo cloverstack-ctl status <module>   # Single module

# Lifecycle
sudo cloverstack-ctl enable <module>   # Enable at boot
sudo cloverstack-ctl disable <module>  # Disable
sudo cloverstack-ctl start <module>    # Start (pulls images if needed)
sudo cloverstack-ctl stop <module>     # Stop
sudo cloverstack-ctl restart <module>  # Restart

# Logs
sudo cloverstack-ctl logs <module>     # View module logs
sudo docker logs <container-name>      # View specific container logs

# Updates
sudo cloverstack-ctl update <module>   # Pull latest images and restart
```

### Troubleshooting Module Startup

If a module fails to start:

```bash
# 1. Check the module's Docker Compose logs
cd /opt/cloverstack/modules/<module-name>
sudo docker compose logs

# 2. Verify images are pulled
sudo docker compose pull

# 3. Check system resources
free -h        # RAM
df -h          # Disk
sudo docker system df   # Docker disk usage

# 4. Check network
sudo docker network ls   # cloverstack network exists?
sudo docker network inspect cloverstack

# 5. Check provision log for errors
cat /var/log/cloverstack/provision.log
```

### Port Conflicts

If a module's port is already in use:
```bash
# Find what's using the port
sudo ss -tlnp | grep :<port>

# Stop the conflicting service
sudo docker stop <container-name>
# or
sudo systemctl stop <service>
```

See [PORT-MAP.md](PORT-MAP.md) for the complete port allocation table.

---

<p align="center">
  <strong>MyClover.Tech</strong> — Own Your Stack<br>
  <a href="https://myclover.tech">myclover.tech</a> · <a href="https://github.com/jonfulk805-og/mycloverOS">GitHub</a>
</p>
