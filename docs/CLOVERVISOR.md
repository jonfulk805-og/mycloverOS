# CloverVisor — Hypervisor Blackbox Edition

> **Your private cloud. No license fees. No phone home. AI manages your VMs.**

CloverVisor is a bare-metal Type 1 hypervisor built on CloverOS. It boots
straight into a sealed VM management platform — plug in, power on, deploy VMs.
Zero desktop, zero bloat, zero attack surface. The **blackbox** — it just works.

## Quick Start

```bash
# Build the Hypervisor Blackbox ISO
sudo ./build.sh hypervisor

# After install — check system status
clovervisor status

# Create your first VM
clovervisor vm create my-server debian12

# Attach an ISO and boot
clovervisor vm attach-iso my-server /var/lib/clovervisor/isos/debian-12-amd64.iso
clovervisor vm start my-server

# Open the web UI
# https://<server-ip>:8006
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CloverVisor Web UI (:8006)                 │
│          Cockpit + CloverStack Skin + Chappie AI             │
├──────────────────────────────────────────────────────────────┤
│  VM Management  │  Storage  │  Network  │  Cluster  │ Backup │
│  (libvirt)      │ (ZFS/LVM) │  (OVS)   │  (Coro+Pace)│(Restic)│
├──────────────────────────────────────────────────────────────┤
│              KVM / QEMU Hypervisor Engine                     │
├──────────────────────────────────────────────────────────────┤
│              CloverOS Kernel (Debian Bookworm)                │
│         IOMMU / VFIO / Hugepages / KSM / tuned              │
├──────────────────────────────────────────────────────────────┤
│                   Bare Metal Hardware                         │
│         CPU (VT-x/AMD-V) + RAM + NVMe/SSD + GPU             │
└──────────────────────────────────────────────────────────────┘
```

## Core Components

### Hypervisor Engine
- **KVM** — Linux kernel-based Virtual Machine (same tech as AWS, GCP, Azure)
- **QEMU** — hardware emulation layer
- **libvirt** — unified VM management API
- **CPU passthrough** — near-native performance (`host-passthrough` mode)

### Storage Backends
- **ZFS** (recommended) — checksums, compression, snapshots, RAID
- **LVM thin** — thin-provisioned logical volumes
- **Directory** — simple qcow2 files (default fallback)
- **Ceph** — distributed storage for multi-node clusters (Enterprise)

### Virtual Networking
- **Open vSwitch (OVS)** — software-defined networking
- **VLAN trunking** — isolate VM traffic by VLAN
- **WireGuard mesh** — encrypted tunnel between hypervisors (CloverMesh)
- **Virtual bridges** — libvirt managed for simple setups

### GPU Passthrough
- **VFIO/IOMMU** — pass physical GPUs directly to VMs
- **Use cases**: AI/ML workloads, gaming VMs, CAD/rendering
- **Setup**: Enable VT-d/AMD-Vi in BIOS → `clovervisor gpu bind <pci-id>`

### High Availability
- **Corosync + Pacemaker** — cluster quorum and resource management
- **DRBD** — synchronous block-level replication between nodes
- **Live migration** — move running VMs between nodes with zero downtime
- **Auto-failover** — VMs restart on surviving node within seconds
- **CloverMesh** — WireGuard-tunneled multi-site clustering

### AI Integration (Chappie)
- **VM right-sizing** — monitors CPU/RAM/disk usage, suggests optimal allocations
- **Anomaly detection** — alerts on unusual resource patterns
- **Predictive alerts** — disk failure forecasting, capacity planning
- **Natural language** — "Chappie, create a Ubuntu VM with 8GB RAM"
- **Auto-optimization** — KSM tuning, hugepage allocation, CPU pinning suggestions

## Blackbox Security Model

CloverVisor is designed as a sealed appliance:

| Feature | Description |
|---------|-------------|
| **No SSH** | SSH disabled by default. All management via web UI. |
| **Read-only root** | Root filesystem is immutable. Config on separate partition. |
| **Watchdog** | Monitors critical services, auto-restarts on failure. |
| **Integrity checks** | SHA256 baseline of system files, verified every 6 hours. |
| **Tamper alerts** | Immediate notification if any system file changes. |
| **Emergency console** | Physical-access-only console for disaster recovery. |
| **OTA updates** | Automatic security patches from stable channel. |

### Enable SSH (when needed)
```bash
# From emergency console or web UI
clovervisor ssh enable    # Turn on SSH
clovervisor ssh disable   # Turn off SSH
clovervisor ssh status    # Check current state
```

## CLI Reference

### VM Commands
```bash
clovervisor vm list                        # List all VMs
clovervisor vm create <name> [template]    # Create VM from template
clovervisor vm start <name>                # Start a VM
clovervisor vm stop <name>                 # Graceful shutdown
clovervisor vm kill <name>                 # Force stop
clovervisor vm restart <name>              # Reboot
clovervisor vm pause <name>                # Pause (freeze)
clovervisor vm resume <name>               # Resume
clovervisor vm delete <name> [--force]     # Delete VM + disks
clovervisor vm info <name>                 # Detailed info
clovervisor vm console <name>              # VNC console URL
clovervisor vm attach-iso <name> <iso>     # Mount ISO
clovervisor vm snapshot <name> [label]     # Create snapshot
clovervisor vm snapshots <name>            # List snapshots
clovervisor vm restore <name> <label>      # Revert to snapshot
clovervisor vm clone <src> <dst>           # Clone a VM
clovervisor vm migrate <name> <host>       # Live migration

# Create with custom resources
CV_RAM=16384 CV_VCPUS=8 CV_DISK=100 clovervisor vm create bigvm debian12
```

### Storage Commands
```bash
clovervisor storage status                 # Pool overview
clovervisor storage create-pool <n> <devs> # Create ZFS pool

# Examples:
clovervisor storage create-pool data /dev/sdb              # Single disk
clovervisor storage create-pool data /dev/sdb /dev/sdc     # Mirror
clovervisor storage create-pool data /dev/sd{b,c,d}        # RAIDZ1
```

### Network Commands
```bash
clovervisor network status                 # Bridge/VLAN overview
clovervisor network create-vlan <id>       # Create VLAN on OVS bridge
```

### GPU Commands
```bash
clovervisor gpu list                       # List GPUs + IOMMU groups
clovervisor gpu bind <vendor:device>       # Bind GPU to VFIO for passthrough
```

### Cluster Commands
```bash
clovervisor cluster status                 # HA cluster status
clovervisor cluster init <cluster-name>    # Initialize new cluster
clovervisor cluster join <master-ip>       # Join existing cluster
```

### Backup Commands
```bash
clovervisor backup <vm-name> [dest]        # Backup VM (XML + disks)
clovervisor restore <archive.tar.zst>      # Restore from backup
```

## VM Templates

Pre-configured templates for common deployments:

| Template | OS | RAM | vCPU | Disk | Notes |
|----------|----|-----|------|------|-------|
| `cloveros-server` | Linux | 4GB | 4 | 40GB | Full CloverStack in a VM |
| `debian12` | Linux | 2GB | 2 | 20GB | Minimal Debian server |
| `ubuntu2404` | Linux | 2GB | 2 | 25GB | Ubuntu 24.04 LTS |
| `rocky9` | Linux | 2GB | 2 | 20GB | RHEL-compatible |
| `windows-server-2022` | Windows | 4GB | 4 | 60GB | BYO ISO + license |
| `windows-11` | Windows | 8GB | 4 | 64GB | UEFI + TPM |
| `pfsense` | FreeBSD | 2GB | 2 | 10GB | Virtual firewall (2 NICs) |
| `opnsense` | FreeBSD | 2GB | 2 | 10GB | Virtual firewall (2 NICs) |
| `truenas` | FreeBSD | 8GB | 4 | 16GB | Virtual NAS |
| `docker-host` | Linux | 2GB | 2 | 30GB | Docker CE pre-installed |
| `k3s-node` | Linux | 4GB | 4 | 40GB | Kubernetes node |

```bash
# Create from template
clovervisor vm create myfw pfsense
clovervisor vm create win-dc windows-server-2022
clovervisor vm create k8s-01 k3s-node
```

## Pricing

| Tier | Price | Nodes | VMs | Key Features |
|------|-------|-------|-----|-------------|
| **Free** | $0 | 1 | 3 | Web UI, snapshots, community |
| **Starter** | $29/mo | 1 | 10 | Full UI, 1 VLAN, email support |
| **Pro** | $79/mo | 3 | Unlimited | HA cluster, live migrate, Ceph |
| **Enterprise** | $149/mo | Unlimited | Unlimited | Fleet, GPU passthrough, API |
| **MSP** | $299/mo | Unlimited | Unlimited | Multi-tenant, white-label, SLA |

No per-CPU licensing. No per-VM fees. Flat rate.

## Hardware Recommendations

| Tier | Use Case | CPU | RAM | Storage | GPU |
|------|----------|-----|-----|---------|-----|
| **Homelab** | 3-5 VMs | 4+ cores | 16GB | 256GB NVMe | - |
| **Small Office** | 10-15 VMs | 8+ cores | 64GB | 1TB NVMe RAID | - |
| **Datacenter** | 50+ VMs | 16+ cores | 128GB+ | ZFS RAIDZ | Optional |
| **AI Workstation** | GPU VMs | 16+ cores | 128GB+ | NVMe | NVIDIA RTX/A-series |

### Citadel Hardware Pairings
- **Citadel Puck Hypervisor** ($349) — homelab entry
- **Citadel Edge Hypervisor** ($599) — small office
- **Citadel Rack R4** ($3,499) — 1U rack mount
- **Citadel Rack R8** ($7,999) — 2U, HA-ready
- **Citadel Rack R16** ($15,999) — 3U, GPU passthrough

## Competitors

| Feature | CloverVisor | Proxmox VE | VMware ESXi | XCP-ng |
|---------|-------------|------------|-------------|--------|
| Price | Flat/free tier | €110/yr/CPU | $$$$ | Free |
| AI Management | ✅ Chappie | ❌ | ❌ | ❌ |
| GPU Passthrough | ✅ | ✅ | ✅ | Partial |
| ZFS Native | ✅ | ✅ | ❌ | ❌ |
| Sealed/Blackbox | ✅ | ❌ | Partial | ❌ |
| WireGuard Mesh HA | ✅ | ❌ | ❌ | ❌ |
| VM Templates Market | ✅ | ❌ | ❌ | ❌ |
| White-label MSP | ✅ | ❌ | ❌ | ❌ |
| Open Source | ✅ | Partial | ❌ | ✅ |

## Building

```bash
# Install build dependencies (Ubuntu 24.04 / Debian 12)
sudo apt install live-build debootstrap xorriso squashfs-tools \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools debian-archive-keyring

# Build the Hypervisor Blackbox ISO
sudo ./build.sh hypervisor

# Output: build/mycloverOS-0.1.0-amd64.iso
```

## Open Source Credits

CloverVisor is built on these excellent open-source projects:

- **KVM/QEMU** — Linux kernel / QEMU contributors (GPL-2.0)
- **libvirt** — Red Hat + community (LGPL-2.1)
- **Open vSwitch** — Linux Foundation (Apache-2.0)
- **OpenZFS** — OpenZFS community (CDDL)
- **Cockpit** — Red Hat + community (LGPL-2.1)
- **Corosync** — Red Hat (BSD-3-Clause)
- **Pacemaker** — ClusterLabs (GPL-2.0)
- **DRBD** — LINBIT (GPL-2.0)
- **Restic** — Alexander Neumann (BSD-2-Clause)
- **WireGuard** — Jason A. Donenfeld (GPL-2.0)
- **Debian** — Debian Project (DFSG)

---

*CloverVisor is part of the MyClover.Tech CloverOS platform.*
*"Your Idea. AI Builds It. You Profit."*
