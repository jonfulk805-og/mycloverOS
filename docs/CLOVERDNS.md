# CloverDNS -- Privacy-First DNS

Every mycloverOS installation ships with **encrypted DNS by default**. Your ISP cannot see, log, or tamper with your DNS queries.

## How It Works

CloverDNS configures `systemd-resolved` to send all DNS queries over **DNS-over-TLS (DoT)** to privacy-respecting upstream providers. No extra software needed — it's baked into the OS.

| Feature | Default |
|---------|---------|
| Primary DNS | Cloudflare (1.1.1.1) |
| Fallback DNS | Quad9 (9.9.9.9) |
| Encryption | DNS-over-TLS (opportunistic) |
| DNSSEC | Enabled (allow-downgrade) |
| ISP can see queries? | **No** |

## DNS Profiles

Switch providers with one command:

```bash
# List all profiles
clover-dns list

# Switch to a profile
sudo clover-dns use quad9

# Check current config
clover-dns status

# Verify privacy
clover-dns test
```

### Available Profiles

| Profile | Provider | IPs | Features |
|---------|----------|-----|----------|
| `cloudflare` | Cloudflare | 1.1.1.1, 1.0.0.1 | Fastest, zero-logging, KPMG-audited |
| `quad9` | Quad9 | 9.9.9.9, 149.112.112.112 | Swiss non-profit, malware blocking |
| `adguard` | AdGuard DNS | 94.140.14.14, 94.140.15.15 | Blocks ads, trackers at DNS level |
| `adguard-family` | AdGuard Family | 94.140.14.15, 94.140.15.16 | Ads + trackers + adult content + safe search |
| `controld` | Control D | 76.76.2.2, 76.76.10.2 | Customizable filtering, strict no-logging |
| `cloudflare-family` | Cloudflare Families | 1.1.1.3, 1.0.0.3 | Malware + adult content blocking |
| `max-privacy` | Quad9 (strict) | 9.9.9.9 | Strict DoT (refuses plain DNS) + full DNSSEC |

## Encryption Modes

```bash
# Opportunistic (default): use TLS when available, fallback to plain
sudo clover-dns opportunistic

# Strict: TLS or nothing (most private, may break captive portals)
sudo clover-dns strict

# Disable encryption (not recommended)
sudo clover-dns off
```

**Note:** `strict` mode will fail to resolve DNS on networks with captive portals (hotel/airport WiFi). Use `opportunistic` when traveling.

## Custom DNS

```bash
# Single server
sudo clover-dns custom 1.1.1.1

# Primary + fallback
sudo clover-dns custom 1.1.1.1 9.9.9.9

# With DoT hostname for TLS verification
sudo clover-dns custom 1.1.1.1 9.9.9.9 cloudflare-dns.com
```

## Privacy Verification

```bash
# Quick local check
clover-dns test

# Full external leak test
clover-dns test --external
```

For a visual DNS leak test, visit [dnsleaktest.com](https://dnsleaktest.com) from your CloverOS machine.

## How CloverDNS Integrates

- **All editions**: CloverDNS is a base feature — server, desktop, micro, kiosk, hypervisor, NAS, firewall, industrial, creator
- **CloverWall (Firewall edition)**: Runs AdGuard Home on top of CloverDNS for full network-wide ad/tracker blocking with a web dashboard
- **CloverGuard module**: Uses CloverDNS as upstream when deployed
- **NetworkManager**: Configured to defer DNS to systemd-resolved and ignore DHCP-provided DNS servers
- **Setup Wizard**: Users can select their preferred DNS profile during first-boot setup

## Technical Details

- **Implementation**: `systemd-resolved` with drop-in config at `/etc/systemd/resolved.conf.d/00-cloverdns.conf`
- **Profiles stored at**: `/etc/myclover/dns-profiles/*.conf`
- **Active profile**: `/etc/myclover/dns-profiles/.active`
- **Build hook**: `0210-privacy-dns.hook.chroot`
- **CLI tool**: `/usr/local/bin/clover-dns` (symlinked from scripts)

## Why These Providers?

Every provider in CloverDNS was selected for:
1. **Zero IP logging** — verified by independent audits or legal jurisdiction
2. **Encrypted transport** — DoT and/or DoH support
3. **Privacy audits** — third-party verification (KPMG for Cloudflare, Swiss law for Quad9)
4. **Reliability** — global anycast networks with 99.99%+ uptime
5. **No data selling** — none of these providers monetize DNS query data
