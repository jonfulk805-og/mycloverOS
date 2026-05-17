# 🍀 CloverMarket

**The on-device app marketplace for mycloverOS.**

CloverMarket is a self-hosted app store built into every mycloverOS installation. Creators publish **CloverApps** — Docker-based applications with startup wizards, theme integration, and optional paid tiers via CloverCoin.

## Overview

```
┌──────────────────────────────────────────────┐
│              mycloverOS Host                  │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │         CloverMarket Server (:8090)      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────┐ │ │
│  │  │ Registry │  │  Wizard  │  │ Theme │ │ │
│  │  │   API    │  │  Engine  │  │Engine │ │ │
│  │  └──────────┘  └──────────┘  └───────┘ │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ App A    │ │ App B    │ │ App C    │     │
│  │ (Docker) │ │ (Docker) │ │ (Docker) │     │
│  └──────────┘ └──────────┘ └──────────┘     │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │  Traefik reverse proxy → *.local        │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

## Quick Start

### CLI (`clovermarket-ctl`)

```bash
# Browse available apps
clovermarket-ctl browse

# Search for an app
clovermarket-ctl search "database"

# Install an app
clovermarket-ctl install my-awesome-app

# Run the startup wizard
clovermarket-ctl wizard my-awesome-app

# Check status of all installed apps
clovermarket-ctl status

# Apply a theme
clovermarket-ctl theme apply midnight
```

### Web UI

Open `http://<server-ip>:8090` in a browser for the CloverMarket web interface. From here you can:

- View installed apps and their status
- Launch app wizards
- Browse themes
- Check your CloverCoin wallet

## CloverApp Manifest (`cloverapp.yml`)

Every app includes a `cloverapp.yml` file that defines everything about it:

| Section | Purpose |
|---------|---------|
| `app` | Name, version, author, icon, license |
| `marketplace` | Category, tags, screenshots, pricing tier |
| `pricing` | Free/freemium/paid model, CloverCoin & USD prices |
| `container` | Docker image, ports, env vars, resource limits |
| `networking` | Subdomain, Traefik routing |
| `data` | Volumes, backup config |
| `integrations` | Chappie AI, CloverBase, Vault SSO |
| `theme` | Whether the app accepts CloverMarket themes |
| `wizard` | Points to the `wizard.yml` startup wizard |

See `docs/examples/cloverapp.yml` for a fully annotated example.

## Startup Wizard (`wizard.yml`)

Apps can include a `wizard.yml` that creates a step-by-step setup experience:

```yaml
steps:
  - title: Welcome
    fields:
      - id: app_name
        label: App Name
        type: text
        default: My App

  - title: Choose Layout
    fields:
      - id: layout
        type: layout_picker
        layouts:
          - { value: dashboard, label: Dashboard, preview: "📊" }
          - { value: list, label: List View, preview: "📝" }
```

**Supported field types:**
- `text` — Single-line text input
- `number` — Numeric input with min/max
- `select` — Dropdown selector
- `checkbox` / `checklist` — Multi-select checkboxes
- `color` — Color picker
- `layout_picker` — Visual layout cards
- `theme_picker` — Theme selector with previews

See `docs/examples/wizard.yml` for a complete example.

## Theme Engine

CloverMarket includes a unified theme system with 40 CSS tokens:

### Built-in Themes

| Theme | Description |
|-------|-------------|
| 🍀 Clover Classic | Default dark theme with green accents |
| 🌙 Midnight | Navy blue dark theme |
| ❄️ Nordic | Clean light theme, Scandinavian inspired |
| ⚡ Neon | High-contrast dark with vivid neon accents |
| 🏢 Corporate | Professional light theme with navy brand |

### Theme Files (`.clover-theme`)

Themes are JSON files with a `tokens` object mapping CSS variable names to values:

```json
{
  "name": "My Theme",
  "tokens": {
    "brand": "#22c55e",
    "bg-primary": "#0f1117",
    "text-primary": "#e2e4eb"
  }
}
```

Each token becomes a CSS variable: `--clover-brand`, `--clover-bg-primary`, etc. Apps that set `theme.enabled: true` in their manifest automatically receive the active theme CSS.

### Applying Themes

```bash
# List available themes
clovermarket-ctl theme list

# Apply a theme
clovermarket-ctl theme apply midnight

# Import a custom theme
clovermarket-ctl theme import ~/my-custom.clover-theme
```

## CloverCoin Wallet

Each mycloverOS instance has a local CloverCoin wallet. CloverCoins are the in-marketplace currency used to unlock paid app tiers and features.

```bash
# Check balance
clovermarket-ctl wallet
```

CloverCoin packs can be purchased at [myclover.tech](https://myclover.tech) and are synced to the device wallet.

## Directory Structure

```
/opt/clovermarket/
├── apps/                    # Installed CloverApps
│   └── <app-id>/
│       ├── cloverapp.yml    # App manifest
│       ├── wizard.yml       # Startup wizard (optional)
│       ├── docker-compose.yml  # Generated by clovermarket-ctl
│       └── wizard-config.json  # Saved wizard config
├── cache/
│   └── registry.json        # Cached registry from market.myclover.tech
└── wizards/                 # Shared wizard resources

/opt/cloverstack/
├── modules/clovermarket/    # CloverMarket server
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── server/app.py
└── themes/
    ├── builtin/             # 5 built-in .clover-theme files
    └── custom/              # User-imported themes

/etc/myclover/themes/
├── active                   # Current theme ID
└── active.css               # Generated CSS from current theme

/var/lib/clovermarket/
└── wallet.json              # CloverCoin wallet
```

## For Creators

### Publishing a CloverApp

1. Create your Docker-based application
2. Write a `cloverapp.yml` manifest (see `docs/examples/`)
3. Optionally add a `wizard.yml` for guided setup
4. Package as a `.cloverapp` archive:
   ```bash
   tar -czf my-app.cloverapp cloverapp.yml wizard.yml Dockerfile ...
   ```
5. Submit to the CloverMarket registry at [market.myclover.tech](https://market.myclover.tech)

### Revenue Model

- **Free tier**: Always available, no cost to publish
- **Paid tiers**: Set CloverCoin and/or USD pricing in your manifest
- **Revenue pool**: Subscription bundles (App Pass, App Pass+) distribute revenue across creators based on usage

### Local Development

```bash
# Install from local package
clovermarket-ctl install-local ./my-app.cloverapp

# Or place directly in the apps directory
cp -r my-app/ /opt/clovermarket/apps/my-app/
clovermarket-ctl start my-app
```

## API Endpoints

The marketplace server exposes a REST API at port 8090:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Marketplace web UI |
| GET | `/health` | Health check |
| GET | `/theme.css` | Active theme CSS |
| GET | `/wizard/{app-id}` | App wizard HTML |
| GET | `/api/apps` | List installed apps |
| GET | `/api/themes` | List themes + active |
| GET | `/api/wallet` | Wallet balance |
| GET | `/api/registry` | Cached app registry |
| POST | `/api/wizard/{app-id}/submit` | Submit wizard config |
| POST | `/api/theme/apply` | Apply a theme |
