# 🍀 CloverNAS Edition

**Your Data. Your Metal. Your Rules.**

CloverNAS is a standalone NAS appliance built on mycloverOS. ZFS-native storage, enterprise file sharing, ransomware-proof snapshots, one-click apps, and CloverMesh HA clustering — all from bare metal with zero cloud dependency.

## Quick Start

```bash
# Build the ISO
sudo ./build.sh nas

# After install, create your first pool
clovernas pool create tank mirror /dev/sda /dev/sdb

# Share it
clovernas share smb tank/data/files --name shared
clovernas share nfs tank/data/files --network 192.168.1.0/24

# Install Plex
clovernas app install plex
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 CloverNAS Edition                     │
├─────────────┬───────────┬───────────┬───────────────┤
│   SMB/CIFS  │    NFS    │   iSCSI   │   S3 (MinIO)  │
├─────────────┴───────────┴───────────┴───────────────┤
│              ZFS Storage Engine                       │
│    pools · datasets · snapshots · replication         │
├─────────────────────────────────────────────────────┤
│              Docker App Catalog                       │
│  Plex · Jellyfin · Nextcloud · Syncthing · more      │
├─────────────────────────────────────────────────────┤
│     Cockpit Web UI (:8080)  │  SMART Monitoring      │
├─────────────────────────────────────────────────────┤
│             CloverMesh HA Clustering                  │
│   WireGuard · Corosync · DRBD · Keepalived VIP       │
├─────────────────────────────────────────────────────┤
│                 mycloverOS Base                       │
└─────────────────────────────────────────────────────┘
```

## Features

### Storage
- **ZFS** — pools, datasets, compression (LZ4), dedup, quotas
- **Auto-snapshot** — hourly/daily/weekly/monthly with configurable retention
- **Ransomware Shield** — immutable snapshot locks (90-day default)
- **Replication** — ZFS send/receive to remote targets (compressed, incremental)
- **SMART monitoring** — disk health checks every 30 min, email/wall alerts
- **Monthly scrubs** — automatic data integrity verification

### File Sharing
- **SMB/CIFS** — Samba 4 with macOS Time Machine, Windows Shadow Copy (Previous Versions)
- **NFS v4** — Linux/Unix network shares
- **iSCSI** — block-level storage targets
- **S3** — MinIO object storage (API-compatible)
- **FTP/WebDAV** — legacy protocol support

### Apps (Docker)
One-command app installs from the built-in catalog:

| App | Category | Port |
|-----|----------|------|
| Plex | Media | 32400 |
| Jellyfin | Media | 8096 |
| Nextcloud | Productivity | 8081 |
| Syncthing | Sync | 8384 |
| PhotoPrism | Media | 2342 |
| Home Assistant | Home | 8123 |
| Vaultwarden | Security | 8082 |
| Grafana | Monitoring | 3000 |
| Pi-hole | Network | 8083 |
| Gitea | Dev | 3001 |

### CloverMesh HA
- WireGuard encrypted mesh tunnels
- Corosync/Pacemaker quorum + DRBD sync replication
- Keepalived VIP failover
- Storage pool failover between nodes

## CLI Reference

```
clovernas pool create <name> <type> <devs...>   # mirror/raidz/raidz2/raidz3/stripe
clovernas pool status [name]
clovernas snap create <dataset> [label]
clovernas snap lock <dataset@snap>               # Ransomware shield
clovernas share smb <dataset> [--name N]
clovernas share nfs <dataset> [--network CIDR]
clovernas app list / install / remove / running
clovernas disk list / smart / benchmark
clovernas repl run [dataset]
clovernas mesh init / join / status / failover
clovernas status                                  # Full dashboard
```

## Web UI

Cockpit on port **8080** with CloverNAS branding. Manage storage, shares, users, and monitor health from your browser.

## Hardware Recommendations

| Tier | CPU | RAM | Storage | Use Case |
|------|-----|-----|---------|----------|
| Home | Any x86_64 | 8GB+ | 2× HDD | Family NAS, media |
| SMB | Xeon/Ryzen | 16GB+ | 4× HDD + SSD cache | Small office |
| Enterprise | Xeon | 32GB+ | 8× HDD + NVMe | Department storage |
| HA Cluster | 2× Xeon | 64GB+ | 12× HDD + NVMe | Mission-critical |

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | Single node, 4 drives, SMB/NFS, snapshots |
| Pro | $29/mo | Unlimited drives, all protocols, apps, replication |
| Enterprise | $79/mo | HA clustering, S3, priority support |
| Datacenter | $199/mo | Multi-site replication, MSP dashboard |
