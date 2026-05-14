# CloverApp Manifest Specification

> Version: 1.0.0 | mycloverOS CloverMarket

## Overview

Every app in the CloverMarket is packaged as a **CloverApp** — a Docker Compose stack with a `cloverapp.yml` manifest that describes the app, its tiers, resource requirements, and CloverStack integrations.

## Directory Structure

A CloverApp package follows this layout:

```
my-awesome-app/
├── cloverapp.yml              # App manifest (required)
├── docker-compose.yml         # Docker Compose stack (required)
├── docker-compose.free.yml    # Override for free tier (optional)
├── docker-compose.pro.yml     # Override for pro tier (optional)
├── docker-compose.ent.yml     # Override for enterprise tier (optional)
├── icon.png                   # App icon, 256x256 PNG (required)
├── screenshots/               # Up to 5 screenshots (optional)
│   ├── 01-dashboard.png
│   └── 02-settings.png
├── hooks/                     # Lifecycle hooks (optional)
│   ├── pre-install.sh
│   ├── post-install.sh
│   ├── pre-upgrade.sh
│   ├── post-upgrade.sh
│   └── pre-remove.sh
├── config/                    # Default config templates (optional)
│   └── app.conf.template
├── README.md                  # User-facing docs (required)
└── LICENSE                    # License file (required)
```

## cloverapp.yml — Full Specification

```yaml
# =============================================================================
# CloverApp Manifest v1
# =============================================================================

# --- Identity ----------------------------------------------------------------
apiVersion: cloverapp/v1           # Manifest version (required)
kind: CloverApp                     # Always "CloverApp" (required)

metadata:
  name: my-awesome-app              # Unique slug, lowercase, hyphens (required)
  displayName: My Awesome App       # Human-readable name (required)
  version: 1.2.0                    # Semver (required)
  description: >-                   # Short description, max 160 chars (required)
    A self-hosted project management tool with Kanban boards,
    time tracking, and AI-powered task prioritization.
  longDescription: |                # Full description, Markdown OK (optional)
    My Awesome App is a complete project management solution...
  author:                           # Creator info (required)
    name: Jane Developer
    email: jane@example.com
    url: https://janedev.com
    creatorId: creator_abc123       # CloverCreator ID (assigned on approval)
  license: MIT                      # SPDX license identifier (required)
  homepage: https://github.com/janedev/awesome-app
  repository: https://github.com/janedev/awesome-app
  icon: icon.png                    # Relative path to icon (required)
  screenshots:                      # Up to 5 (optional)
    - screenshots/01-dashboard.png
    - screenshots/02-settings.png

# --- Categories & Tags -------------------------------------------------------
categories:                         # Primary categories (1-3) (required)
  - productivity
  - business
tags:                               # Search tags (up to 10) (optional)
  - project-management
  - kanban
  - time-tracking
  - ai

# Valid categories:
#   productivity, business, media, security, networking, dev-tools,
#   iot, ai-ml, communication, storage, monitoring, gaming,
#   home-automation, education, finance, health

# --- Tiers -------------------------------------------------------------------
tiers:
  free:                             # Free tier (required — every app must have one)
    description: Basic features for personal use
    limits:
      users: 3                      # Max users (0 = unlimited)
      storage: 1GB                  # Max storage
      features:                     # Feature flags
        - kanban-boards
        - basic-reporting
    compose: docker-compose.yml     # Base compose file
    overrides: docker-compose.free.yml  # Tier-specific overrides (optional)

  pro:                              # Pro tier — unlocked by App Pass (optional)
    description: Full features for teams
    limits:
      users: 25
      storage: 50GB
      features:
        - kanban-boards
        - basic-reporting
        - time-tracking
        - ai-task-priority
        - api-access
        - custom-fields
    compose: docker-compose.yml
    overrides: docker-compose.pro.yml
    standalone_price:               # If sold outside App Pass (optional)
      monthly: 15.00
      yearly: 150.00

  enterprise:                       # Enterprise tier — unlocked by App Pass+ (optional)
    description: Unlimited everything, priority support
    limits:
      users: 0                      # 0 = unlimited
      storage: 0                    # 0 = unlimited
      features:
        - kanban-boards
        - basic-reporting
        - time-tracking
        - ai-task-priority
        - api-access
        - custom-fields
        - sso-saml
        - audit-log
        - white-label
        - priority-support
    compose: docker-compose.yml
    overrides: docker-compose.ent.yml
    standalone_price:
      monthly: 39.00
      yearly: 390.00

# --- Resources ---------------------------------------------------------------
resources:
  minimum:                          # Won't install if not met (required)
    cpu: 1                          # CPU cores
    memory: 512M                    # RAM
    disk: 2G                        # Disk space
  recommended:                      # For optimal performance (optional)
    cpu: 2
    memory: 1G
    disk: 10G
  gpu: false                        # Requires GPU? (default: false)

# --- Networking ---------------------------------------------------------------
networking:
  ports:                            # Ports exposed to Traefik (optional)
    - name: web
      container_port: 8080
      protocol: http
      traefik_route: true           # Auto-create Traefik route
      subdomain: awesome            # Route: awesome.local.cloverstack
  internal_only: false              # If true, no external access (default: false)

# --- Data & Storage -----------------------------------------------------------
storage:
  volumes:                          # Named volumes (optional)
    - name: app-data
      mount: /app/data
      backup: true                  # Include in CloverStack backups
    - name: app-db
      mount: /var/lib/postgresql/data
      backup: true
  config_dir: /etc/myclover/apps/my-awesome-app  # Host config path

# --- CloverStack Integrations ------------------------------------------------
integrations:
  chappie:                          # Ollama AI integration (optional)
    enabled: true
    description: AI-powered task prioritization and natural language queries
    models:                         # Required Ollama models
      - name: llama3.2:3b
        purpose: Task analysis
  vault:                            # MyCloverVault SSO (optional)
    enabled: true
    description: Single sign-on via MyCloverVault
    scopes:
      - openid
      - profile
      - email
  netmon:                           # NetMon monitoring (optional)
    enabled: true
    description: Health checks and uptime monitoring
    healthcheck:
      endpoint: /api/health
      interval: 60
  backup:                           # Citadel Backup integration (optional)
    enabled: true
    description: Automated daily backups
    schedule: "0 3 * * *"
  mesh:                             # CloverMesh sync (optional)
    enabled: false
    description: Multi-node sync for distributed setups
  sentrylog:                        # SentryLog logging (optional)
    enabled: true
    description: Centralized log collection
    log_driver: syslog

# --- Lifecycle Hooks ----------------------------------------------------------
hooks:
  pre_install: hooks/pre-install.sh     # Before Docker pull/up
  post_install: hooks/post-install.sh   # After first successful start
  pre_upgrade: hooks/pre-upgrade.sh     # Before version upgrade
  post_upgrade: hooks/post-upgrade.sh   # After version upgrade
  pre_remove: hooks/pre-remove.sh       # Before Docker down/rm

# --- Health Check -------------------------------------------------------------
healthcheck:
  endpoint: /api/health                 # HTTP health check URL
  port: 8080
  interval: 30                          # Seconds between checks
  timeout: 10                           # Seconds before timeout
  retries: 3                            # Failures before unhealthy
  start_period: 60                      # Grace period after start

# --- Environment Variables ----------------------------------------------------
env:                                    # User-configurable env vars
  - name: APP_SECRET_KEY
    description: Secret key for session encryption
    required: true
    generate: true                      # Auto-generate on install
    length: 64
  - name: APP_ADMIN_EMAIL
    description: Admin email address
    required: true
    prompt: true                        # Ask user during install
  - name: APP_MAX_UPLOAD_MB
    description: Maximum file upload size in MB
    required: false
    default: "100"

# --- Dependencies -------------------------------------------------------------
dependencies:                           # Other CloverApps or modules needed
  - name: postgresql                    # Built-in or marketplace app
    version: ">=15.0"
    optional: false
  - name: redis
    version: ">=7.0"
    optional: true                      # Works without it, just slower

# --- Compatibility ------------------------------------------------------------
compatibility:
  mycloverOS: ">=0.1.0"                # Minimum mycloverOS version
  editions:                             # Which editions support this app
    - server
    - desktop
    - micro                             # Omit kiosk if not applicable
  architectures:
    - amd64
    - arm64                             # If multi-arch images available

# --- Approval & Marketplace ---------------------------------------------------
marketplace:
  status: published                     # draft | submitted | approved | published
  submittedAt: "2026-05-14T00:00:00Z"
  approvedAt: "2026-05-14T12:00:00Z"
  featured: false                       # Highlighted in marketplace
  installCount: 0                       # Updated by CloverMarket API
  rating: 0.0                           # 0-5 stars, updated by reviews
  reviewCount: 0
```

## Manifest Field Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `apiVersion` | string | Always `cloverapp/v1` |
| `kind` | string | Always `CloverApp` |
| `metadata.name` | string | Unique slug (lowercase, hyphens, 3-50 chars) |
| `metadata.displayName` | string | Human-readable name |
| `metadata.version` | string | Semantic version (e.g. `1.2.0`) |
| `metadata.description` | string | Short description (max 160 chars) |
| `metadata.author` | object | Creator identity |
| `metadata.license` | string | SPDX license identifier |
| `metadata.icon` | string | Path to 256x256 PNG icon |
| `categories` | list | 1-3 primary categories |
| `tiers.free` | object | Free tier definition |
| `resources.minimum` | object | Minimum CPU/RAM/disk |

### Tier Compose Merging

When a user activates a paid tier, compose files are merged:

```
docker compose -f docker-compose.yml -f docker-compose.pro.yml up -d
```

The override file typically adds:
- Additional containers (e.g., AI sidecar, worker processes)
- Higher resource limits
- Extra volumes
- Feature-flag environment variables

### Environment Variable Generation

Variables with `generate: true` are auto-generated during install using cryptographically random strings. Variables with `prompt: true` are asked during the interactive install or via the web dashboard.

## Validation

The `clovermarket validate` command checks:
- All required fields present
- `metadata.name` is unique (checks local + remote registry)
- Semver format on version
- Icon exists and is valid PNG
- Docker Compose files are valid YAML
- Resource minimums are reasonable (CPU >= 0.25, memory >= 64M)
- At least one category from the valid list
- Free tier always defined
- Hook scripts are executable
- No `privileged: true` in Docker Compose (security requirement)
- No host networking (except with special approval)
- All container images use pinned tags (no `:latest`)

## Examples

### Minimal CloverApp (Static Website Server)

```yaml
apiVersion: cloverapp/v1
kind: CloverApp
metadata:
  name: static-server
  displayName: Static Site Server
  version: 1.0.0
  description: Lightweight static file server with auto-HTTPS
  author:
    name: Community
    email: community@myclover.tech
  license: MIT
  icon: icon.png
categories:
  - dev-tools
tiers:
  free:
    description: Serve static sites with auto-HTTPS
    limits:
      users: 0
      storage: 10GB
    compose: docker-compose.yml
resources:
  minimum:
    cpu: 0.25
    memory: 64M
    disk: 500M
networking:
  ports:
    - name: web
      container_port: 80
      protocol: http
      traefik_route: true
      subdomain: sites
compatibility:
  mycloverOS: ">=0.1.0"
  editions: [server, desktop, micro, kiosk]
  architectures: [amd64, arm64]
```
