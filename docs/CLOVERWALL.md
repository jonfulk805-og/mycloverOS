# 🛡️ CloverWall Firewall Edition

**Protect. Route. Filter. Secure.**

Enterprise firewall/router: nftables stateful firewall, Suricata IDS/IPS, AdGuard Home DNS filtering, WireGuard VPN, multi-WAN failover, traffic shaping, CloverMesh HA clustering.

## Quick Start

```bash
sudo ./build.sh firewall

# Check status
cloverwall status

# Add a VPN peer
cloverwall vpn add-peer my-phone
cloverwall vpn qr my-phone    # Scan QR code on mobile

# Block an IP
cloverwall block add 1.2.3.4

# Port forward
cloverwall nat add 8080 192.168.1.50:80
```

## Architecture

```
┌───────────────────────────────────────────────────┐
│                   CloverWall                       │
├──────────┬────────────┬──────────┬────────────────┤
│  WAN(s)  │  LAN/VLANs │ VPN Mesh │  DMZ (opt)    │
├──────────┴────────────┴──────────┴────────────────┤
│           nftables Stateful Firewall               │
│  blacklists · rate limits · GeoIP · NAT · QoS     │
├───────────────────────────────────────────────────┤
│   Suricata IDS/IPS  │  AdGuard Home DNS Filter    │
├───────────────────────────────────────────────────┤
│   WireGuard VPN     │  OpenVPN  │  IPsec (opt)    │
├───────────────────────────────────────────────────┤
│   Multi-WAN Failover/Load Balance                  │
├───────────────────────────────────────────────────┤
│   DHCP Server  │  FRR Dynamic Routing  │  Captive │
├───────────────────────────────────────────────────┤
│   Cockpit Web UI (:8443) — CloverWall Branding    │
├───────────────────────────────────────────────────┤
│         CloverMesh HA (active/standby pair)        │
│   WireGuard · Corosync · Conntrack sync · VRRP    │
├───────────────────────────────────────────────────┤
│                 mycloverOS Base                    │
└───────────────────────────────────────────────────┘
```

## Features

### Firewall
- **nftables** — modern kernel-native firewall with dynamic blacklists
- **Rate limiting** — per-IP connection rate limits
- **GeoIP blocking** — block/allow by country
- **NAT / Port forwarding** — easy CLI and web UI management

### Intrusion Detection
- **Suricata IDS/IPS** — real-time traffic analysis
- **Auto-updating rules** — ET Open + OISF traffic ID (daily)
- **Alert logging** — JSON event log for SIEM integration

### DNS Filtering
- **AdGuard Home** — ad/tracker/malware blocking with web dashboard
- **DNS-over-HTTPS** — encrypted upstream DNS
- **Custom blocklists** — add your own block/allow rules

### VPN
- **WireGuard** — modern, fast VPN with QR code provisioning
- **OpenVPN** — compatibility VPN (optional)
- **IPsec/IKEv2** — site-to-site tunnels (optional)

### Routing
- **Multi-WAN** — failover and load-balance across ISPs
- **FRR** — BGP, OSPF, RIP dynamic routing
- **Policy routing** — route by source/destination/service
- **DHCP server** — static leases, DNS integration

### High Availability
- **Active/standby pair** via CloverMesh
- **Conntrack sync** — seamless failover without dropping connections
- **Configuration sync** — rules, DHCP, DNS sync between peers

## CLI Reference

```
cloverwall rule list|reload|export|import
cloverwall nat add|list|remove
cloverwall block add|remove|list|country
cloverwall vpn setup|add-peer|remove-peer|list|qr|status
cloverwall dns status|block|allow|stats|flush
cloverwall ids status|alerts|rules|mode|suppress
cloverwall dhcp leases|static|range
cloverwall traffic live|top|stats|capture
cloverwall wan status|failover|balance
cloverwall mesh init|join|status|failover
cloverwall status|interfaces|routes|connections
```

## Web UI

Cockpit on port **8443** with CloverWall branding. AdGuard Home on port **3000**.

## Hardware Recommendations

| Tier | CPU | RAM | NICs | Throughput | Use Case |
|------|-----|-----|------|-----------|----------|
| Home | Any dual-core | 4GB | 2 | 1 Gbps | Home network |
| SMB | Xeon/Ryzen | 8GB | 4 | 2.5 Gbps | Small office |
| Enterprise | Xeon | 16GB+ | 4-8 | 10 Gbps | Branch office |
| HA Pair | 2× Xeon | 16GB+ | 4+ each | 10+ Gbps | Mission-critical |

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | Single WAN, nftables, DNS, WireGuard, Suricata |
| Pro | $29/mo | Multi-WAN, GeoIP, traffic shaping, QoS |
| Enterprise | $79/mo | HA pair, captive portal, SIEM integration |
| MSP | $149/mo | Multi-site management, central policy, reporting |
