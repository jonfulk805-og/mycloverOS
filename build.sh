#!/usr/bin/env bash
# =============================================================================
# mycloverOS Build Script
# Builds a bootable ISO using Debian live-build
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config/distro.conf"

# --- Defaults ----------------------------------------------------------------
EDITION="${1:-${DEFAULT_EDITION}}"
CLEAN="${CLEAN:-false}"

# --- Colors ------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[mycloverOS]${NC} $*"; }
warn() { echo -e "${YELLOW}[mycloverOS]${NC} $*"; }
err()  { echo -e "${RED}[mycloverOS]${NC} $*" >&2; }

# --- Preflight ---------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    err "Must run as root (live-build requires it)"
    err "Usage: sudo ./build.sh [server|desktop|micro|kiosk]"
    exit 1
fi

REQUIRED_CMDS="lb debootstrap xorriso mksquashfs"
for cmd in ${REQUIRED_CMDS}; do
    if ! command -v "${cmd}" &>/dev/null; then
        err "Missing: ${cmd}"
        err "Install: apt install live-build debootstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin mtools dosfstools debian-archive-keyring"
        exit 1
    fi
done

# Warn if Debian keyring is missing (needed when building on Ubuntu)
if [[ ! -f /usr/share/keyrings/debian-archive-keyring.gpg ]]; then
    warn "Debian archive keyring not found -- debootstrap will skip signature verification"
    warn "Fix: sudo apt install debian-archive-keyring"
fi

log "Building mycloverOS ${DISTRO_VERSION} (${DISTRO_CODENAME}) -- Edition: ${EDITION}"

# --- Workspace ---------------------------------------------------------------
BUILD_WORK="${SCRIPT_DIR}/${BUILD_DIR}/${EDITION}"

if [[ "${CLEAN}" == "true" ]]; then
    log "Cleaning previous build..."
    rm -rf "${BUILD_WORK}"
fi

mkdir -p "${BUILD_WORK}"
cd "${BUILD_WORK}"

# --- Configure live-build ----------------------------------------------------
log "Configuring live-build..."

# Log live-build version for debugging
LB_VERSION_RAW=$(lb --version 2>/dev/null || echo "unknown")
log "live-build version: ${LB_VERSION_RAW}"

LB_ARGS=(
    --distribution "${BASE_CODENAME}"
    --mode debian
    --parent-distribution "bookworm"
    --parent-mirror-bootstrap "http://deb.debian.org/debian"
    --parent-mirror-chroot "http://deb.debian.org/debian"
    --archive-areas "main"
    --architectures "${BASE_ARCH}"
    --mirror-bootstrap "${BASE_MIRROR}"
    --mirror-chroot "${BASE_MIRROR}"
    --mirror-chroot-security "${BASE_SECURITY_MIRROR}"
    --mirror-binary "${BASE_MIRROR}"
    --mirror-binary-security "${BASE_SECURITY_MIRROR}"
    --parent-mirror-chroot-security "${BASE_SECURITY_MIRROR}"
    --parent-mirror-binary "http://deb.debian.org/debian"
    --parent-mirror-binary-security "${BASE_SECURITY_MIRROR}"
    --security true
    --updates false
    --binary-images iso-hybrid
    --iso-application "${DISTRO_NAME}"
    --iso-volume "${ISO_LABEL}"
    --bootappend-live "boot=live components hostname=${DEFAULT_HOSTNAME} username=${DEFAULT_USER} loglevel=3"
    --memtest none
    --apt-recommends false
    --cache true
    --keyring-packages debian-archive-keyring
    --linux-packages "linux-image"
    --linux-flavours "amd64"
    --apt-indices false
    --initramfs live-boot
    --initsystem systemd
    --bootloaders grub-efi
)

# These flags exist in live-build 4.x (Debian Bullseye and older) but were
# removed in 5.x+ (Debian Bookworm / Ubuntu 24.04+)
if lb config --help 2>&1 | grep -q -- '--updates'; then
    LB_ARGS+=(--updates true --backports false)
fi

# Firmware flags changed across versions
if lb config --help 2>&1 | grep -q -- '--firmware-binary'; then
    LB_ARGS+=(--firmware-binary true --firmware-chroot true)
fi

lb config "${LB_ARGS[@]}"

# --- Copy package lists ------------------------------------------------------
log "Installing package lists..."
mkdir -p config/package-lists

# Base packages (always included)
cp "${SCRIPT_DIR}/packages/base.list" config/package-lists/base.list.chroot

# Edition-specific packages
case "${EDITION}" in
    desktop)
        cp "${SCRIPT_DIR}/packages/desktop.list" config/package-lists/desktop.list.chroot
        cp "${SCRIPT_DIR}/packages/ai.list" config/package-lists/ai.list.chroot
        ;;
    micro)
        cp "${SCRIPT_DIR}/packages/desktop-micro.list" config/package-lists/desktop.list.chroot 2>/dev/null || true
        ;;
    kiosk)
        cp "${SCRIPT_DIR}/packages/kiosk.list" config/package-lists/kiosk.list.chroot 2>/dev/null || true
        ;;
    server)
        # Server = base + cloverstack + networking (no desktop)
        ;;
esac

# CloverStack + networking (all editions)
cp "${SCRIPT_DIR}/packages/cloverstack.list" config/package-lists/cloverstack.list.chroot
cp "${SCRIPT_DIR}/packages/networking.list" config/package-lists/networking.list.chroot
cp "${SCRIPT_DIR}/packages/hardware.list" config/package-lists/hardware.list.chroot

# CloverMarket
if [[ -f "${SCRIPT_DIR}/packages/clovermarket.list" ]]; then
    cp "${SCRIPT_DIR}/packages/clovermarket.list" config/package-lists/clovermarket.list.chroot
fi

# --- Copy filesystem overlay -------------------------------------------------
log "Installing filesystem overlay..."
if [[ -d "${SCRIPT_DIR}/overlay" ]]; then
    mkdir -p config/includes.chroot
    cp -a "${SCRIPT_DIR}/overlay/." config/includes.chroot/
fi

# --- Copy scripts as hooks ---------------------------------------------------
log "Installing build hooks..."
mkdir -p config/hooks/normal

# Copy live-build hooks
if [[ -d "${SCRIPT_DIR}/config/live-build/hooks" ]]; then
    cp "${SCRIPT_DIR}/config/live-build/hooks/"*.chroot config/hooks/normal/ 2>/dev/null || true
    cp "${SCRIPT_DIR}/config/live-build/hooks/"*.binary config/hooks/normal/ 2>/dev/null || true
fi

# --- Copy installer scripts into the live filesystem ------------------------
log "Installing mycloverOS scripts..."
mkdir -p config/includes.chroot/usr/local/bin
cp "${SCRIPT_DIR}/scripts/myclover-install" config/includes.chroot/usr/local/bin/
cp "${SCRIPT_DIR}/scripts/myclover-provision" config/includes.chroot/usr/local/bin/
cp "${SCRIPT_DIR}/scripts/myclover-update" config/includes.chroot/usr/local/bin/
cp "${SCRIPT_DIR}/scripts/cloverstack-setup" config/includes.chroot/usr/local/bin/
cp "${SCRIPT_DIR}/scripts/clovermarket-ctl" config/includes.chroot/usr/local/bin/
chmod +x config/includes.chroot/usr/local/bin/myclover-*
chmod +x config/includes.chroot/usr/local/bin/cloverstack-*
chmod +x config/includes.chroot/usr/local/bin/clovermarket-*

# --- Copy preseed (automated installer answers) -----------------------------
if [[ -d "${SCRIPT_DIR}/config/live-build/preseed" ]]; then
    mkdir -p config/preseed
    cp "${SCRIPT_DIR}/config/live-build/preseed/"* config/preseed/ 2>/dev/null || true
fi

# --- Build -------------------------------------------------------------------
log "Starting build (this will take 15-45 minutes)..."
lb build 2>&1 | tee "${SCRIPT_DIR}/${BUILD_DIR}/build-${EDITION}.log"

# --- Output ------------------------------------------------------------------
ISO_PATH=$(find . -maxdepth 1 -name "*.iso" -type f | head -1)
if [[ -n "${ISO_PATH}" ]]; then
    FINAL_ISO="${SCRIPT_DIR}/${BUILD_DIR}/mycloverOS-${DISTRO_VERSION}-${EDITION}-${BASE_ARCH}.iso"
    mv "${ISO_PATH}" "${FINAL_ISO}"
    ISO_SIZE=$(du -h "${FINAL_ISO}" | cut -f1)
    ISO_SHA=$(sha256sum "${FINAL_ISO}" | cut -d' ' -f1)

    log "============================================"
    log "  BUILD COMPLETE"
    log "  Edition:  ${EDITION}"
    log "  ISO:      ${FINAL_ISO}"
    log "  Size:     ${ISO_SIZE}"
    log "  SHA256:   ${ISO_SHA}"
    log "============================================"

    # Write checksum file
    echo "${ISO_SHA}  $(basename "${FINAL_ISO}")" > "${FINAL_ISO}.sha256"
else
    err "Build failed -- no ISO produced. Check ${SCRIPT_DIR}/${BUILD_DIR}/build-${EDITION}.log"
    exit 1
fi
