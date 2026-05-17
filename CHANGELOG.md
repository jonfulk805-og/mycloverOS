# Changelog

All notable changes to mycloverOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — CloverNAS + CloverDeploy + CloverMesh
- **CloverNAS** — Full TrueNAS-grade ZFS storage management platform
  - OpenZFS integration: pools, RAIDZ (1/2/3), mirrors, snapshots, clones, encryption, compression
  - Protocol support: SMB/CIFS, NFS v3/v4, iSCSI, S3 (MinIO), FTP/SFTP
  - S.M.A.R.T. disk monitoring with predictive failure alerts
  - Ransomware protection with immutable snapshots (ZFS hold)
  - `cloverstack-ctl storage` CLI for all operations
- **CloverDeploy** — Container & VM orchestration engine
  - Docker container deployment with 200+ app catalog (Nextcloud, Plex, PostgreSQL, Pi-hole, etc.)
  - KVM/QEMU virtual machines with wizard and OS templates
  - GPU passthrough (IOMMU/VT-d) support
  - Live VM migration between cluster nodes
  - noVNC browser-based VM console
  - `cloverstack-ctl deploy` CLI for all operations
- **CloverMesh** — "Fail to Anywhere" HA clustering
  - Corosync + Pacemaker cluster resource management
  - DRBD 9 synchronous block-level replication (zero data loss)
  - ZFS send/receive async replication
  - Keepalived Virtual IP (VIP) failover
  - WireGuard encrypted mesh between all nodes
  - Cloud failover support (Hetzner, Oracle Free, Linode, custom VPS)
  - Zero-downtime rolling updates
  - Maintenance mode (drain + rejoin)
  - `cloverstack-ctl mesh` CLI for all operations
- New package list: `packages/clovernas.list`
- New build hook: `0300-clovernas.hook.chroot` (ZFS install, NAS directories, service config, app catalog)
- New CLI scripts: `clovernas`, `cloverdeploy`, `clovermesh`
- Updated `cloverstack-ctl` with `storage`, `deploy`, `mesh` subcommands
- Updated `build.sh` to include CloverNAS packages and scripts

### Added — Previous
- Initial repository structure
- Debian live-build configuration (Bookworm base)
- Build system (`build.sh`) with edition support (server, desktop, micro, kiosk)
- Package lists for base, desktop, CloverStack, AI, networking, and hardware
- Root filesystem overlay with CloverStack configuration
- `cloverstack-ctl` service management utility
- `myclover-install` disk installer script
- `myclover-provision` first-boot provisioning
- `myclover-update` system updater
- Plymouth boot splash theme (placeholder)
- GRUB bootloader theme (placeholder)
- GitHub Actions CI workflow for automated ISO builds
- GPLv3 license
- Full documentation (architecture, building, hardware, customization)
