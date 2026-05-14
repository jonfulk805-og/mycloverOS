# CloverMarket — Self-Hosted App Marketplace

> The App Store for mycloverOS. Every app self-hosted. Every app has a free tier.

## Overview

CloverMarket is the built-in app marketplace for mycloverOS. It lets users browse, install, and manage self-hosted applications — all running as Docker containers on their own hardware. Creators can build and publish CloverApps that reach every mycloverOS user.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        mycloverOS Host                          │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ clovermarket │  │ cloverapp-  │  │  CloverMarket API       │ │
│  │ CLI          │  │ picker TUI  │  │  market.myclover.tech   │ │
│  └──────┬───────┘  └──────┬──────┘  └────────────┬────────────┘ │
│         │                 │                       │              │
│  ┌──────▼─────────────────▼───────────────────────▼────────────┐│
│  │                   App Manager Daemon                        ││
│  │  - Install / remove / upgrade apps                          ││
│  │  - Tier management (free / pro / enterprise)                ││
│  │  - License validation                                       ││
│  │  - Health monitoring                                        ││
│  └──────┬──────────────────────────────────────────────────────┘│
│         │                                                       │
│  ┌──────▼──────────────────────────────────────────────────────┐│
│  │                    Docker Engine                             ││
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          ││
│  │  │ App A   │ │ App B   │ │ App C   │ │ App D   │ ...      ││
│  │  │ (free)  │ │ (pro)   │ │ (free)  │ │ (ent)   │          ││
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          ││
│  │       │           │           │            │                ││
│  │  ┌────▼───────────▼───────────▼────────────▼───────────┐   ││
│  │  │              Traefik Reverse Proxy                   │   ││
│  │  │  Auto-routes: appname.local.cloverstack              │   ││
│  │  └─────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  /opt/cloverstack/marketplace/                                  │
│  ├── apps/{app-name}/          # Installed app files            │
│  ├── registry/catalog.json     # Cached app catalog             │
│  └── cache/                    # Download cache                 │
│                                                                 │
│  /etc/myclover/apps/{app-name}/ # Per-app config + .env         │
└─────────────────────────────────────────────────────────────────┘
```

## Subscription Tiers

| Tier | Price | What You Get |
|------|-------|-------------|
| **Free** | $0/mo | Every app's free tier. No time limit. |
| **App Pass** | $29/mo / $279/yr | Pro features on ALL marketplace apps |
| **App Pass+** | $49/mo / $469/yr | Enterprise features + priority support |
| **Creator Bundle** | $19/mo / $179/yr | Submit + host unlimited apps, analytics dashboard |

### How the Revenue Pool Works

1. All App Pass / App Pass+ subscription revenue goes into the **CloverMarket Revenue Pool**
2. MyClover.Tech takes a **20% platform fee** (covers hosting, review, infrastructure)
3. The remaining **80% is distributed to creators** based on **weighted active installs**:
   - Each active install of a creator's app = 1 point
   - Pro tier installs = 2x weight (users are getting more value)
   - Enterprise tier installs = 3x weight
4. Monthly payout: creator's points ÷ total pool points × 80% of revenue
5. Minimum payout: $10 (rolls over if under threshold)

**Example:**
- Revenue pool: $10,000/mo from App Pass subs
- Platform fee: $2,000 (20%)
- Creator pool: $8,000
- Creator A has 500 weighted installs out of 10,000 total = 5% = $400/mo
- Creator B has 2,000 weighted installs = 20% = $1,600/mo

### Standalone Pricing

Creators can also set standalone prices for their apps (purchased directly, outside the App Pass bundle). These follow a **70/30 split** (70% to creator, 30% to MCT).

## Submission & Approval Flow

### For Creators

```
1. BUILD your app
   └── Docker Compose stack + cloverapp.yml manifest
   └── Free tier required. Pro/Enterprise optional.
   └── See: docs/CREATOR-GUIDE.md

2. VALIDATE locally
   └── clovermarket validate
   └── Checks manifest, compose, resources, security

3. SUBMIT for review
   └── clovermarket submit
   └── Or upload at: creator.myclover.tech/submit

4. REVIEW (MyClover.Tech team)
   ├── Automated checks:
   │   ├── Manifest validation
   │   ├── Docker image security scan (Trivy)
   │   ├── Resource limit enforcement
   │   ├── No privileged containers
   │   ├── No host networking (without approval)
   │   ├── Pinned image tags (no :latest)
   │   └── License compliance check
   └── Manual review:
       ├── Functionality test on reference hardware
       ├── UI/UX quality check
       ├── Description accuracy
       └── Brand/content policy compliance

5. APPROVED → Published to CloverMarket
   └── Appears in catalog within 24 hours
   └── Creator gets notification + dashboard access

6. REJECTED → Feedback provided
   └── Specific issues listed
   └── Creator can fix and resubmit
```

### Review SLA

- **Automated checks**: Instant (< 5 minutes)
- **Manual review**: Within 48 hours (target: 24 hours)
- **Resubmission**: Within 24 hours

### Approval Criteria

| Requirement | Details |
|------------|---------|
| Free tier | Must have a genuinely useful free tier (not just a demo) |
| Security | No privileged containers, no host mounts outside /opt/cloverstack |
| Pinned tags | All Docker images must use specific version tags |
| Health check | Must define a working health check endpoint |
| Documentation | README.md with setup, usage, and troubleshooting |
| License | Valid SPDX license. Open-source preferred but not required. |
| Resources | Must accurately declare minimum resource requirements |
| No malware | Obviously. Scanned with Trivy + manual inspection. |
| No tracking | No phone-home telemetry without explicit user consent |
| Branding | No impersonation of CloverStack or other apps |

## CLI Reference

### clovermarket

```bash
# Browse & discover
clovermarket search "project management"    # Search apps
clovermarket search                          # Browse all
clovermarket info wiki-server                # Detailed app info
clovermarket status                          # Subscription & installed count

# Install & manage
clovermarket install wiki-server             # Install (free tier)
clovermarket install kanban-board pro        # Install with pro tier
clovermarket remove wiki-server              # Uninstall
clovermarket upgrade wiki-server             # Upgrade to latest
clovermarket update                          # Check/upgrade all apps
clovermarket tier kanban-board enterprise    # Switch tier
clovermarket list                            # List installed apps
clovermarket logs wiki-server                # View app logs

# Creator tools
clovermarket validate                        # Validate cloverapp.yml
clovermarket submit                          # Submit for review
```

### cloverapp-picker

```bash
# Interactive TUI (runs during first boot)
cloverapp-picker

# Use a preset
cloverapp-picker --preset msp

# Headless mode (CI/automation)
cloverapp-picker --headless --preset home

# List available presets
cloverapp-picker --list-presets
```

### Available Presets

| Preset | Apps | Use Case |
|--------|------|----------|
| `minimal` | MyCloverVault, Chappie AI | Just the essentials |
| `home` | Vault, Chappie, Media, Guard, StreamServer | Home server |
| `msp` | NetMon, SentryLog, Vault, Chappie, Guard, Mesh, Bot | IT/MSP monitoring |
| `creator` | Chappie, Media, Stream, Design, Bot, Base | Content creation |
| `business` | Vault, Chappie, POS, Sign, Bot, Base, Guard | Retail/office |
| `full` | Everything | The whole CloverStack |

## File Locations

| Path | Purpose |
|------|---------|
| `/opt/cloverstack/marketplace/apps/` | Installed app files |
| `/opt/cloverstack/marketplace/registry/` | Cached catalog |
| `/opt/cloverstack/marketplace/cache/` | Download cache |
| `/etc/myclover/apps/{app}/` | Per-app config & .env |
| `/etc/myclover/license.key` | License / subscription key |
| `/etc/myclover/creator-token` | Creator API token |
| `/usr/local/bin/clovermarket` | CLI binary |
| `/usr/local/bin/cloverapp-picker` | TUI picker |

## API Endpoints (market.myclover.tech)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/catalog` | Full app catalog (cached 1hr) |
| GET | `/api/v1/apps/{name}` | Single app details |
| GET | `/api/v1/apps/{name}/download?tier=free` | Download app package |
| POST | `/api/v1/apps/submit` | Submit app for review |
| GET | `/api/v1/apps/{name}/reviews` | App reviews |
| POST | `/api/v1/apps/{name}/reviews` | Submit review |
| GET | `/api/v1/categories` | List categories |
| GET | `/api/v1/featured` | Featured apps |
| POST | `/api/v1/license/validate` | Validate license key |

## Integration with CloverStack

CloverApps can opt into CloverStack integrations:

| Integration | What It Does |
|------------|-------------|
| **Chappie AI** | App gets access to Ollama API for AI features |
| **MyCloverVault** | SSO — users log in with their Vault credentials |
| **NetMon** | Health check monitoring, uptime tracking, alerts |
| **SentryLog** | Centralized log collection via syslog driver |
| **Citadel Backup** | Automated volume backups on schedule |
| **CloverMesh** | Multi-node data sync for distributed deploys |
| **Traefik** | Auto-routed subdomain with TLS |

## Revenue Projections

| Scenario | App Pass Subs | Monthly Revenue | Creator Pool (80%) |
|----------|--------------|-----------------|-------------------|
| Launch (100 users) | 30 @ $29 | $870 | $696 |
| Growth (1,000 users) | 300 @ $29 | $8,700 | $6,960 |
| Scale (10,000 users) | 3,000 @ $29 | $87,000 | $69,600 |

Plus standalone app sales, CloverCoin transactions, and hardware upsell.

## Roadmap

### Phase 1 — MVP (Weeks 1-4)
- [x] `cloverapp.yml` manifest spec
- [x] `clovermarket` CLI tool
- [x] `cloverapp-picker` TUI for first boot
- [x] Stripe products (App Pass, App Pass+, Creator Bundle)
- [x] Creator Guide documentation
- [ ] CloverMarket API server (FastAPI)
- [ ] Docker image security scanner integration
- [ ] First 5 community apps packaged

### Phase 2 — Creator Portal (Weeks 5-8)
- [ ] creator.myclover.tech web portal
- [ ] App submission web UI
- [ ] Creator analytics dashboard
- [ ] Revenue tracking & payout system
- [ ] App review/rating system
- [ ] Featured apps curation

### Phase 3 — Ecosystem (Weeks 9-16)
- [ ] App auto-update daemon
- [ ] CloverCoin integration (pay-per-use apps)
- [ ] App bundles (themed collections)
- [ ] Community forums per app
- [ ] Developer SDK for CloverStack integrations
- [ ] Hardware bundle deals (Citadel + App Pass)
