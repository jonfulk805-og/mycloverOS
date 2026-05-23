# CloverOS Quick Start Guide

> **Version:** 0.1.0 (Seedling)  
> **Last updated:** 2026-05-22

This guide walks you through booting, installing, and configuring CloverOS from scratch. It covers the full path from ISO to a running CloverStack with Portainer, Traefik, and all modules — plus known issues and how to fix them.

---

## Table of Contents

1. [Prepare the Boot Media](#1-prepare-the-boot-media)
2. [Boot into Live Mode](#2-boot-into-live-mode)
3. [Install to Disk](#3-install-to-disk)
4. [First-Boot Setup Wizard](#4-first-boot-setup-wizard)
5. [Access Portainer](#5-access-portainer)
6. [CloverStack Module Status](#6-cloverstack-module-status)
7. [Start CloverStack Modules](#7-start-cloverstack-modules)
8. [Traefik Reverse Proxy](#8-traefik-reverse-proxy)
9. [Firewall & Network](#9-firewall--network)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prepare the Boot Media

### Option A: Download a Release ISO

Download the latest ISO from the [Releases](https://github.com/jonfulk805-og/mycloverOS/releases) page.

### Option B: Build from Source

```bash
git clone https://github.com/jonfulk805-og/mycloverOS.git
cd mycloverOS

# Install build dependencies (Debian/Ubuntu host)
sudo apt install live-build debootstrap squashfs-tools xorriso \
  grub-pc-bin grub-efi-amd64-bin

# Build the ISO
sudo ./build.sh

# Output: build/mycloverOS-<version>-amd64.iso
```

### Write to USB

```bash
# Replace /dev/sdX with your USB device
sudo dd if=mycloverOS-latest.iso of=/dev/sdX bs=4M status=progress
sync
```

> **Tip:** Use [balenaEtcher](https://etcher.io) or [Rufus](https://rufus.ie) on Windows/Mac for a GUI option.

---

## 2. Boot into Live Mode

1. Insert the USB and boot from it (BIOS/UEFI boot menu — usually F12, F2, or DEL)
2. Select **mycloverOS** from the GRUB menu
3. The system boots into a live environment with CloverStack auto-provisioning

> **Live mode** runs entirely in RAM. Changes are not saved to disk. This is great for testing — but for a permanent deployment, install to disk (next step).

### Live Mode Limitations

- **Storage:** Uses a tmpfs ramdisk — limited by available RAM
- **Docker:** Uses the `vfs` storage driver (slow, space-hungry) — see [Troubleshooting](#overlay-on-overlay-error-live-boot-only)
- **Performance:** Slower than a disk install

---

## 3. Install to Disk

From the live environment, run:

```bash
sudo myclover-install
```

The installer will:
1. Detect available disks
2. Ask you to select a target disk
3. Partition and format the disk
4. Copy the CloverOS filesystem
5. Install the GRUB bootloader
6. Reboot into the installed system

> **⚠️ Warning:** This will erase the target disk. Make sure you select the correct one.

After reboot, you'll see the login prompt:

```
Linux cloverstack 6.1.0-48-amd64 ...

⚙ mycloverOS v0.1.0 (seedling)

First-time setup? Open a browser and visit:
→ http://<this-ip>:8080

mycloverOS 0.1.0
Type 'cs-status' to see CloverStack module status
```

---

## 4. First-Boot Setup Wizard

On first boot after install, the **setup wizard** runs automatically on port `8080`.

1. Find your box's IP address (shown in the MOTD, or run `ip addr`)
2. Open a browser and go to: `http://<your-ip>:8080`
3. Follow the wizard to configure:
   - Hostname
   - Network settings
   - Admin credentials
   - Module selection

The wizard creates `/etc/myclover/.setup-complete` when done. Provisioning waits for this file before deploying containers.

> **Tip:** If you want to skip the wizard and use defaults:
> ```bash
> sudo touch /etc/myclover/.setup-complete
> ```

---

## 5. Access Portainer

Portainer is the web-based Docker management UI. After provisioning completes, access it at:

```
https://<your-ip>:9443
```

> **Note:** You'll see a browser warning about an untrusted certificate. This is Portainer's self-signed SSL cert — click "Advanced" → "Proceed" to continue. This is normal and expected.

### First-Time Portainer Setup

1. **Create your admin account** — set a username and strong password
2. Click **"Get Started"** to connect to the local Docker environment
3. You'll see the Environments dashboard showing your local Docker with containers, images, and system resources

### ⚠️ Portainer Timeout Issue

**Portainer locks itself if you don't create an admin account within ~5 minutes of first start.** If you see:

> *"Your Portainer instance timed out for security purposes. To re-enable your Portainer instance, you will need to restart Portainer."*

**Fix it:**

```bash
sudo docker restart portainer
```

Then immediately navigate to `https://<your-ip>:9443` and create your admin account before the timer expires again.

> **Why this happens:** Portainer enforces a security timeout on fresh installs. If provisioning runs well before you access the web UI, the window can expire. This is a Portainer feature, not a bug.

---

## 6. CloverStack Module Status

Check which modules are enabled and running:

```bash
cs-status
```

Example output:

```
CloverStack Module Status
=========================

MODULE              ENABLED    RUNNING
------              -------    -------
chappie             yes        no
cloverbot           no         no
cloverdesign        no         no
cloverdesktop       no         no
cloverdrone         no         no
cloverguard         no         no
clovermarket        no         no
clovermedia         no         no
clovermesh          no         no
clovermesh-radio    no         no
clovermine          no         no
cloverpos           no         no
cloversign          no         no
myclover-vault      yes        no
netmon              yes        no
sentrylog           yes        no
streamserver        no         no
```

Provisioning enables the default modules (**chappie**, **myclover-vault**, **netmon**, **sentrylog**), but they may not be running yet — they need their Docker images pulled and containers started.

---

## 7. Start CloverStack Modules

Start the enabled modules:

```bash
sudo cloverstack-ctl start netmon
sudo cloverstack-ctl start sentrylog
sudo cloverstack-ctl start myclover-vault
sudo cloverstack-ctl start chappie
```

Enable and start additional modules:

```bash
# Enable a module
sudo cloverstack-ctl enable clovermedia

# Start it
sudo cloverstack-ctl start clovermedia

# Disable a module
sudo cloverstack-ctl disable clovermedia

# Stop a module
sudo cloverstack-ctl stop clovermedia
```

Verify everything is running:

```bash
cs-status
sudo docker ps
```

### Module Web UIs

Once running, access each module's web interface:

| Module | URL | Port |
|--------|-----|------|
| Portainer | `https://<ip>:9443` | 9443 |
| NetMon (Zabbix) | `http://<ip>:8081` | 8081 |
| MyCloverVault | `http://<ip>:8082` | 8082 |
| Chappie AI | `http://<ip>:8083` | 8083 |
| SentryLog (Graylog) | `http://<ip>:9000` | 9000 |

See [docs/PORT-MAP.md](PORT-MAP.md) for the complete port reference.

---

## 8. Traefik Reverse Proxy

Traefik is the reverse proxy that handles HTTP/HTTPS routing and TLS certificates. After provisioning, Traefik is pulled but may show as **"Created"** (not running) because it defers startup until configured.

### Check Traefik Status

```bash
sudo docker ps -a | grep traefik
```

If status shows `Created` (not `Up`):

```bash
# Start Traefik
sudo docker start traefik

# Check logs for errors
sudo docker logs traefik
```

### ⚠️ Traefik Startup Deferral

Traefik intentionally defers startup during provisioning. The provision log will show:

```
Deploying Traefik reverse proxy...
Traefik setup deferred
```

**This is by design.** Traefik needs routing rules and (optionally) TLS certificates before it can meaningfully proxy traffic. To start it manually:

```bash
sudo docker start traefik
```

The Traefik dashboard is available at `http://<your-ip>:8080` (shares port with the setup wizard — the wizard should be stopped after initial setup).

---

## 9. Firewall & Network

CloverOS comes with UFW (Uncomplicated Firewall) pre-configured.

### Check Firewall Status

```bash
sudo ufw status
```

### Default Open Ports

| Port | Service |
|------|---------|
| 22 | SSH |
| 80 | HTTP (Traefik) |
| 443 | HTTPS (Traefik) |
| 8080 | Setup Wizard / Traefik Dashboard |
| 9443 | Portainer |

### Security Status

The MOTD shows the security overview at every login:

```
mycloverOS Security Status
===========================
Firewall:   ● Active
Fail2Ban:   ○ Inactive
AppArmor:   ● 9 profiles loaded
Audit:      ● Logging
Docker:     ● Running (N containers)
Updates:    ● System up to date
```

For a full security audit:

```bash
sudo security-audit
```

### Fail2Ban

Fail2Ban may show as **Inactive** after fresh install. Enable it:

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
sudo systemctl status fail2ban
```

---

## 10. Troubleshooting

### Portainer: "Timed out for security purposes"

**Symptom:** Navigating to `https://<ip>:9443` shows "Your Portainer instance timed out for security purposes."

**Cause:** Portainer locks new installations if the admin account isn't created within ~5 minutes of first container start.

**Fix:**
```bash
sudo docker restart portainer
```
Then immediately go to `https://<ip>:9443` and create your admin account.

---

### Traefik: Status "Created" but Not Running

**Symptom:** `docker ps -a` shows Traefik with status `Created` instead of `Up`.

**Cause:** Traefik startup is intentionally deferred during provisioning — it needs routing configuration.

**Fix:**
```bash
sudo docker start traefik
sudo docker logs traefik    # Check for config errors
```

---

### Provision Log: "Portainer already running" but No Containers

**Symptom:** Provision log says `Portainer already running` but `docker ps -a` is empty.

**Cause:** The provision script uses `2>/dev/null || log "already running"` — this swallows the actual error. If the Docker image pull fails (network, disk space, or overlay driver issue), the error is hidden.

**Fix:**
```bash
# Check what actually happened
cat /var/log/cloverstack/provision.log

# Pull and start Portainer manually
sudo docker pull portainer/portainer-ce:latest
sudo docker network create cloverstack 2>/dev/null; true
sudo docker run -d \
  --name portainer \
  --restart=always \
  -p 9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  --network cloverstack \
  portainer/portainer-ce:latest
```

---

### Overlay-on-Overlay Error (Live Boot Only)

**Symptom:** When running from USB (live boot), containers fail with:
```
failed to mount ... fstype: overlay ... err: invalid argument
```

**Cause:** The live environment runs on an overlayfs root filesystem. Docker defaults to the `overlay2` storage driver, but the Linux kernel does not allow nesting overlayfs on top of overlayfs.

Docker's `daemon.json` sets `vfs` as the storage driver, but **containerd** has a separate snapshotter config that still defaults to `overlayfs`.

**Fix (on a running live system):**
```bash
sudo systemctl stop docker
sudo systemctl stop docker.socket
sudo systemctl stop containerd

# Patch containerd to use the 'native' snapshotter
sudo containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i "s/snapshotter = 'overlayfs'/snapshotter = 'native'/" /etc/containerd/config.toml

# Clear stale state
sudo rm -rf /var/lib/containerd/*
sudo rm -rf /var/lib/docker/*

# Restart everything
sudo systemctl start containerd
sudo systemctl start docker

# Re-pull and run
sudo docker pull portainer/portainer-ce:latest
sudo docker network create cloverstack 2>/dev/null; true
sudo docker run -d --name portainer --restart=always -p 9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data --network cloverstack \
  portainer/portainer-ce:latest
```

**Permanent fix:** Install to disk with `sudo myclover-install`. On real ext4, Docker uses `overlay2` natively and this issue does not occur.

---

### Modules Show "Enabled" but "Not Running"

**Symptom:** `cs-status` shows modules as `enabled: yes` but `running: no`.

**Cause:** Module Docker images need to be pulled from the internet on first start. Provisioning enables the modules (registers them) but may not fully deploy all containers.

**Fix:**
```bash
sudo cloverstack-ctl start <module-name>
```

If that fails, check:
```bash
# Disk space
df -h

# Network connectivity
ping -c 2 8.8.8.8

# DNS
ping -c 2 registry-1.docker.io

# Docker status
sudo docker info
```

---

### No Network / DNS Issues

**Symptom:** `docker pull` hangs or fails. Ping to IPs works but not hostnames.

**Fix:**
```bash
# Check DNS config
cat /etc/resolv.conf

# Test DNS
nslookup registry-1.docker.io

# Temporary fix: add Google DNS
echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf
```

---

### SSH Connection Refused

**Symptom:** Can't SSH into the box.

**Fix:**
```bash
# On the box (via console)
sudo systemctl status sshd
sudo systemctl start sshd
sudo ufw allow 22/tcp
```

---

## Quick Reference

### Essential Commands

```bash
# Module management
cs-status                              # Show all module status
sudo cloverstack-ctl start <module>    # Start a module
sudo cloverstack-ctl stop <module>     # Stop a module
sudo cloverstack-ctl enable <module>   # Enable at boot
sudo cloverstack-ctl disable <module>  # Disable at boot

# Docker
sudo docker ps -a                      # List all containers
sudo docker logs <container>           # View container logs
sudo docker restart <container>        # Restart a container

# System
sudo ufw status                        # Firewall status
sudo security-audit                    # Full Lynis security scan
sudo myclover-update                   # Update system + CloverStack

# AI Engine
ollama list                            # List installed AI models
ollama pull <model>                    # Download a model
ollama run <model>                     # Interactive chat with a model
```

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| SSH | `clover` | Set during install |
| Portainer | (you create) | (you create at first login) |

### Key File Locations

| Path | Description |
|------|-------------|
| `/var/log/cloverstack/provision.log` | First-boot provisioning log |
| `/etc/myclover/.setup-complete` | Setup wizard completion flag |
| `/opt/cloverstack/modules/` | Module Docker Compose stacks |
| `/var/lib/cloverstack/` | Module persistent data |
| `/etc/docker/daemon.json` | Docker configuration |
| `/etc/containerd/config.toml` | Containerd configuration |

---

## Next Steps

- **New to SSH & networking?** — Read [SETUP-COMPANION.md](SETUP-COMPANION.md) for a beginner-friendly guide to PuTTY, Angry IP Scanner, and browser setup
- **Explore Portainer** — manage containers, view logs, deploy stacks
- **Enable more modules** — see `cs-status` for the full list
- **Set up CloverMesh** — connect multiple CloverOS nodes via WireGuard
- **Configure Traefik** — set up domain routing and Let's Encrypt TLS
- **Install AI models** — `ollama pull llama3` for a more capable AI engine

---

<p align="center">
  <strong>MyClover.Tech</strong> — Own Your Stack<br>
  <a href="https://myclover.tech">Website</a> · <a href="https://github.com/jonfulk805-og/mycloverOS">GitHub</a> · <a href="https://myclover.tech/cloverbot">Support</a>
</p>
