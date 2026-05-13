# Customizing mycloverOS

mycloverOS is designed to be forked. Whether you're a CloverCreator building your own branded OS or an MSP customizing for clients, here's how.

## Fork It

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/mycloverOS.git
cd mycloverOS
```

## Change the Branding

### 1. Distribution Identity

Edit `config/distro.conf`:

```bash
DISTRO_NAME="myCustomOS"
DISTRO_VERSION="1.0.0"
DISTRO_CODENAME="phoenix"
DEFAULT_HOSTNAME="myserver"
```

### 2. OS Release Info

Edit `overlay/etc/myclover/release` and `config/live-build/hooks/0100-cloverstack.hook.chroot` (the os-release section).

### 3. Boot Screen

Replace files in `branding/`:
- `branding/plymouth/` — boot splash animation
- `branding/grub/` — GRUB bootloader theme
- `branding/wallpapers/` — desktop wallpapers

### 4. Login Banner

Edit `overlay/etc/issue` (pre-login) and `overlay/etc/motd` (post-login).

## Add/Remove Packages

Edit the `.list` files in `packages/`:

```bash
# Add a package
echo "your-package" >> packages/base.list

# Remove a package (comment it out)
sed -i 's/^nano/#nano/' packages/base.list
```

## Add Custom Services

1. Create a Docker Compose stack:

```bash
mkdir -p overlay/opt/cloverstack/modules/myservice/
cat > overlay/opt/cloverstack/modules/myservice/docker-compose.yml <<EOF
version: "3.8"
services:
  myservice:
    image: myimage:latest
    container_name: myservice
    restart: always
    networks:
      - cloverstack
networks:
  cloverstack:
    external: true
EOF
```

2. Add it to default modules in `config/distro.conf`:

```bash
CLOVERSTACK_DEFAULT_MODULES="netmon sentrylog myclover-vault chappie myservice"
```

## Change Default Desktop Environment

Edit `packages/desktop.list` to swap KDE for GNOME, XFCE, etc.

## Create a CloverStick

Build the server or micro edition and write to USB:

```bash
sudo ./build.sh micro
sudo dd if=build/mycloverOS-*-micro-*.iso of=/dev/sdX bs=4M status=progress
```

The live ISO boots directly from USB with CloverStack ready to go.

## Publish Your Fork

CloverCreator participants can publish custom mycloverOS forks to the OS Marketplace. Your fork becomes a downloadable, bootable product that other creators and businesses can use.

See the [CloverCreator docs](https://myclover.tech/creator) for marketplace submission guidelines.
