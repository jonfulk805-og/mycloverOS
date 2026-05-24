# Changelog

All notable changes to mycloverOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Chatbox AI + AnythingLLM Integration
- **Chatbox AI Desktop** — Native AppImage pre-installed on Desktop & Field Laptop editions
  - Build hook `0365-chatbox-desktop.hook.chroot` auto-downloads latest from GitHub Releases
  - Desktop launcher (.desktop file) with icon extraction
  - Connects to local Ollama at `localhost:11434` for offline AI chat
  - Supports Ollama, OpenAI, Claude, Gemini, Azure providers
  - Local data storage, Knowledge Base (RAG), prompt library
  - GPLv3 Community Edition — credit: [chatboxai/chatbox](https://github.com/chatboxai/chatbox)
- **Chatbox Team Proxy** — Docker module for shared API access (port 8095)
  - Share a single OpenAI/Anthropic API key across team without exposing it
  - Team members just set the proxy address in Chatbox settings
  - Based on `bensdocker/chatbox-team` Docker image
- **AnythingLLM** — Docker module for browser-based AI chat + RAG (port 8097)
  - Document workspaces — upload PDFs/docs and chat with them
  - Built-in RAG with LanceDB (zero-config vector store)
  - AI agents, web scraping, multi-user auth
  - Hot directory for automatic file ingestion
  - MIT licensed — credit: [Mintplex-Labs/anything-llm](https://github.com/Mintplex-Labs/anything-llm)
- Updated port map with new modules (8095, 8097)
- Updated `cloverstack-ctl` module list and help text
- Added `docs/CHATBOX-AI.md` — full integration documentation with comparison matrix

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
