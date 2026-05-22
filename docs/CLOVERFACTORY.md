# 🏭 CloverFactory Industrial Edition

**Monitor. Automate. Protect. Scale.**

SCADA/ICS/OT platform: Mosquitto MQTT broker, Modbus TCP/RTU gateway, Node-RED automation, InfluxDB time-series historian, Grafana dashboards, OT/IT network segmentation, IEC 62443 audit logging, and CloverMesh sub-second HA failover.

## Quick Start

```bash
sudo ./build.sh industrial

# Check status
cloverfactory status

# Subscribe to sensor data
cloverfactory mqtt subscribe "sensors/#"

# Scan a Modbus device
cloverfactory modbus scan 192.168.100.10

# Open Node-RED in browser
cloverfactory nodered open

# Trigger a test alarm
cloverfactory alarm test
```

## Architecture

```
┌───────────────────────────────────────────────────┐
│               CloverFactory Industrial             │
├───────────┬───────────┬───────────┬───────────────┤
│  Modbus   │  OPC-UA   │   MQTT    │   CAN Bus     │
│  TCP/RTU  │  Server   │  Broker   │   (opt)       │
├───────────┴───────────┴───────────┴───────────────┤
│              Node-RED Flow Engine (:1880)           │
│  Industrial palettes: Modbus/OPC-UA/S7/BACnet      │
├───────────────────────────────────────────────────┤
│   InfluxDB Historian  │  Grafana Dashboards (:3000)│
├───────────────────────────────────────────────────┤
│   Alarm Engine (MQTT-based, multi-channel alerts)  │
├───────────────────────────────────────────────────┤
│   OT/IT Network Segmentation (nftables)            │
│   OT → Internet: BLOCKED  │  OT → IT: limited     │
├───────────────────────────────────────────────────┤
│   Cockpit Web UI (:8443) — CloverFactory Branding  │
├───────────────────────────────────────────────────┤
│   Audit Logging (IEC 62443) │ Watchdog │ AppArmor  │
├───────────────────────────────────────────────────┤
│        CloverMesh HA (sub-second failover)         │
│  500ms heartbeat · 1.5s timeout · data replication │
├───────────────────────────────────────────────────┤
│                 mycloverOS Base                    │
└───────────────────────────────────────────────────┘
```

## Protocols Supported

| Protocol | Port | Use Case |
|----------|------|----------|
| MQTT | 1883 (TCP), 9001 (WS), 8883 (TLS) | IoT messaging |
| Modbus TCP | 502 | PLC/sensor polling |
| Modbus RTU | Serial | RS-485 devices |
| OPC-UA | 4840 | Industrial automation |
| CAN Bus | Hardware | Automotive/industrial |
| BACnet | 47808 | Building automation |
| S7 (Siemens) | 102 | Siemens PLCs |
| EtherNet/IP | 44818 | Allen-Bradley PLCs |

## Features

### Data Collection
- **Mosquitto MQTT** — production-grade broker with auth, ACL, TLS, bridging
- **Modbus Gateway** — polls Modbus TCP/RTU devices, publishes to MQTT
- **Node-RED** — visual flow editor with 30+ industrial palettes

### Data Storage
- **InfluxDB** — time-series historian with configurable retention (default 365 days)
- **Grafana** — pre-built factory overview dashboard

### Alarm System
- **Rule-based** — condition evaluation on MQTT topics
- **Multi-channel** — MQTT, email, webhook alerts
- **Severity levels** — info, warning, critical, emergency

### Security
- **OT/IT segmentation** — nftables isolation between OT and IT networks
- **OT internet blocked** — OT devices cannot reach internet by default
- **Audit logging** — IEC 62443 compliant (config changes, auth, network, privileged commands)
- **AppArmor** — mandatory access control
- **AIDE/Tripwire** — file integrity monitoring

### Reliability
- **Watchdog** — hardware watchdog with service monitoring
- **CloverMesh HA** — 500ms heartbeat, sub-second failover
- **PTP/chrony** — precision time synchronization

## CLI Reference

```
cloverfactory mqtt status|topics|subscribe|publish|clients|user|bridge
cloverfactory modbus scan|read|write|gateway|devices
cloverfactory opcua status|browse|read
cloverfactory nodered status|flows|open
cloverfactory tsdb status|query|retention|export|import
cloverfactory grafana status|open|dashboards|snapshot
cloverfactory alarm list|history|ack|test|rules
cloverfactory net status|scan|segment|firewall
cloverfactory mesh init|join|status|failover
cloverfactory status|audit|health|config
```

## Hardware Recommendations

| Tier | CPU | RAM | Storage | Use Case |
|------|-----|-----|---------|----------|
| Edge Gateway | ARM/x86 | 4GB | 64GB eMMC | Single machine monitoring |
| Factory Floor | Xeon/Ryzen | 8GB | 256GB SSD | Production line |
| Plant Server | Xeon | 16GB+ | 1TB SSD | Full plant SCADA |
| HA Cluster | 2× Xeon | 32GB+ | RAID SSD | Mission-critical 24/7 |

## Compliance

- **IEC 62443** — Industrial automation security
- **NIST 800-82** — Guide to ICS security
- **ISA/IEC 62443-3-3** — System security requirements

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | MQTT, Node-RED, Modbus, single node |
| Pro | $49/mo | InfluxDB, Grafana, alarms, OPC-UA |
| Enterprise | $149/mo | HA clustering, audit logging, compliance reports |
| Plant | $499/mo | Multi-site, central management, SLA support |
