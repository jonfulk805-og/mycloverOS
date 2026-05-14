# CloverNAS + CloverDeploy + CloverMesh

> *"Your Data. Your Metal. Your Rules."*

## Overview

CloverNAS is the storage and infrastructure backbone of mycloverOS — a hyperconverged platform that combines enterprise-grade NAS storage (ZFS), container/VM orchestration, and high-availability clustering into a single elegant system.

Three integrated modules:

| Module | Purpose | CLI |
|--------|---------|-----|
| **CloverNAS** | ZFS storage, file sharing, disk health | `cloverstack-ctl storage` |
| **CloverDeploy** | Docker containers, KVM VMs, app catalog | `cloverstack-ctl deploy` |
| **CloverMesh** | HA clustering, failover, replication | `cloverstack-ctl mesh` |

## Quick Start

### Storage Management
```bash
# Create a ZFS mirror pool
cloverstack-ctl storage pool create tank mirror /dev/sda /dev/sdb

# Create an SMB share
cloverstack-ctl storage share smb tank/data/files --name "Shared Files"

# Create a snapshot
cloverstack-ctl storage snap create tank/data/files

# View health dashboard
cloverstack-ctl storage health
```

### Deploy Apps & VMs
```bash
# Browse 200+ apps
cloverstack-ctl deploy catalog

# Install Nextcloud with HA failover
cloverstack-ctl deploy install nextcloud --ha

# Create a VM
cloverstack-ctl deploy vm create dev-server --ram 4096 --vcpus 4 --disk 50 --iso /path/to/ubuntu.iso

# List GPUs for passthrough
cloverstack-ctl deploy gpu list
```

### Build a Cluster
```bash
# On node 1: Initialize
cloverstack-ctl mesh init --name my-cluster --node-ip 192.168.1.10

# On nodes 2-3: Join
cloverstack-ctl mesh join --token CMESH-xxxx-xxxx-xxxx --node-ip 192.168.1.11

# Check status
cloverstack-ctl mesh status

# Test failover
cloverstack-ctl mesh failover test --dry-run
```

## Cluster Designs

| Design | Hardware | Cost | Storage | Uptime |
|--------|----------|------|---------|--------|
| **Starter** | 3 old PCs | $20-44 | <3 TB | 99.9% |
| **Pro** | 3 Mini PCs | $700-1,100 | 1.5 TB | 99.99% |
| **Enterprise** | 3× rack NAS | $12,500 | 72 TB | 99.99%+ |
| **Datacenter** | 4× 3U servers | $89,000 | 600 TB | 99.999% |
| **Hyperscale** | Multi-site | $400K+ | PB+ | 99.999%+ |

See [full cluster build guide](../temp/clovernas/03-cluster-build-guide.md) for step-by-step instructions.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              CloverStack Platform                │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌──────────────┐ ┌──────────┐ │
│  │ CloverNAS   │ │ CloverDeploy │ │CloverMesh│ │
│  │ ZFS Storage │ │ Docker + KVM │ │ HA Cluster│ │
│  └──────┬──────┘ └──────┬───────┘ └────┬─────┘ │
│         │               │              │        │
│  ┌──────┴───────────────┴──────────────┴─────┐  │
│  │            cloverstack-ctl                │  │
│  └───────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│               mycloverOS (Debian)               │
└─────────────────────────────────────────────────┘
```

## Files

| Path | Description |
|------|-------------|
| `packages/clovernas.list` | Package list (ZFS, NAS daemons, KVM, cluster tools) |
| `config/live-build/hooks/0300-clovernas.hook.chroot` | Build hook (installs ZFS, creates dirs, configures services) |
| `scripts/clovernas` | Storage management CLI |
| `scripts/cloverdeploy` | Container & VM CLI |
| `scripts/clovermesh` | Cluster management CLI |

## License

GPLv3 — see [LICENSE](../LICENSE)

Built on: OpenZFS (CDDL), Corosync (BSD-3), Pacemaker (GPL-2), DRBD (GPL-2), Keepalived (GPL-2), WireGuard (GPL-2), FRRouting (GPL-2), libvirt (LGPL-2.1)
