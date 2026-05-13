# Changelog

All notable changes to mycloverOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
