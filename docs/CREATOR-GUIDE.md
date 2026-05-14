# How to Build a CloverApp

> Your guide to building, packaging, and publishing self-hosted apps on CloverMarket.

## What Is a CloverApp?

A CloverApp is a self-hosted application packaged as a Docker Compose stack with a `cloverapp.yml` manifest. It runs on any mycloverOS installation — from a tiny Puck to a full Citadel rack.

**Key principles:**
- Every app MUST have a free tier (genuinely useful, not a demo)
- Apps run as isolated Docker containers
- No privileged access, no host mounts outside approved paths
- Users own their data — always

## Quick Start (5 Minutes)

### 1. Create Your App Directory

```bash
mkdir my-wiki-app && cd my-wiki-app
```

### 2. Write Your Docker Compose

```yaml
# docker-compose.yml
services:
  wiki:
    image: ghcr.io/yourorg/wiki-app:1.0.0
    ports:
      - "8080:8080"
    volumes:
      - wiki-data:/app/data
    environment:
      - WIKI_TITLE=${WIKI_TITLE:-My Wiki}
      - WIKI_SECRET=${WIKI_SECRET}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  wiki-data:
```

### 3. Write Your Manifest

```yaml
# cloverapp.yml
apiVersion: cloverapp/v1
kind: CloverApp

metadata:
  name: my-wiki-app
  displayName: My Wiki App
  version: 1.0.0
  description: Simple, fast, self-hosted wiki with Markdown support
  author:
    name: Your Name
    email: you@example.com
  license: MIT
  icon: icon.png

categories:
  - productivity

tiers:
  free:
    description: Full wiki with unlimited pages
    limits:
      users: 5
      storage: 1GB
      features:
        - markdown-editor
        - search
        - page-history
    compose: docker-compose.yml

resources:
  minimum:
    cpu: 0.5
    memory: 256M
    disk: 500M

networking:
  ports:
    - name: web
      container_port: 8080
      protocol: http
      traefik_route: true
      subdomain: wiki

env:
  - name: WIKI_SECRET
    description: Encryption key for wiki data
    required: true
    generate: true
    length: 64
  - name: WIKI_TITLE
    description: Your wiki title
    required: false
    default: "My Wiki"
    prompt: true

healthcheck:
  endpoint: /health
  port: 8080
  interval: 30
  timeout: 10
  retries: 3

compatibility:
  mycloverOS: ">=0.1.0"
  editions: [server, desktop, micro]
  architectures: [amd64, arm64]
```

### 4. Add an Icon

Create a 256x256 PNG icon and save it as `icon.png`.

### 5. Add a README

```markdown
# My Wiki App

A simple, fast, self-hosted wiki with Markdown support.

## Features
- Markdown editor with live preview
- Full-text search
- Page history and revisions
- User management (up to 5 on free tier)

## Usage
After installation, access your wiki at:
https://wiki.local.cloverstack

## Configuration
Edit `/etc/myclover/apps/my-wiki-app/.env` to customize:
- WIKI_TITLE: Your wiki name
- WIKI_SECRET: Auto-generated encryption key (don't change)
```

### 6. Validate

```bash
clovermarket validate
```

### 7. Submit

```bash
clovermarket submit
```

That's it! Your app will be reviewed and published to CloverMarket.

---

## Adding Paid Tiers

Want to offer premium features? Add Pro and Enterprise tiers.

### Step 1: Create Tier Overrides

```yaml
# docker-compose.pro.yml
services:
  wiki:
    environment:
      - WIKI_TIER=pro
      - WIKI_MAX_USERS=50
      - WIKI_MAX_STORAGE=25G
      - WIKI_ENABLE_API=true
      - WIKI_ENABLE_PLUGINS=true

  # Add a search sidecar for better full-text search
  wiki-search:
    image: ghcr.io/yourorg/wiki-search:1.0.0
    volumes:
      - wiki-data:/app/data:ro
    restart: unless-stopped
```

```yaml
# docker-compose.ent.yml
services:
  wiki:
    environment:
      - WIKI_TIER=enterprise
      - WIKI_MAX_USERS=0        # unlimited
      - WIKI_MAX_STORAGE=0      # unlimited
      - WIKI_ENABLE_API=true
      - WIKI_ENABLE_PLUGINS=true
      - WIKI_ENABLE_SSO=true
      - WIKI_ENABLE_AUDIT=true
      - WIKI_ENABLE_WHITELABEL=true

  wiki-search:
    image: ghcr.io/yourorg/wiki-search:1.0.0
    volumes:
      - wiki-data:/app/data:ro
    restart: unless-stopped
```

### Step 2: Update Your Manifest

```yaml
tiers:
  free:
    description: Full wiki, 5 users, 1GB storage
    limits:
      users: 5
      storage: 1GB
      features:
        - markdown-editor
        - search
        - page-history
    compose: docker-compose.yml

  pro:
    description: 50 users, 25GB, plugins & API
    limits:
      users: 50
      storage: 25GB
      features:
        - markdown-editor
        - search
        - page-history
        - api-access
        - plugins
        - advanced-search
    compose: docker-compose.yml
    overrides: docker-compose.pro.yml
    standalone_price:
      monthly: 12.00
      yearly: 120.00

  enterprise:
    description: Unlimited everything, SSO, audit log
    limits:
      users: 0
      storage: 0
      features:
        - markdown-editor
        - search
        - page-history
        - api-access
        - plugins
        - advanced-search
        - sso-saml
        - audit-log
        - white-label
    compose: docker-compose.yml
    overrides: docker-compose.ent.yml
    standalone_price:
      monthly: 29.00
      yearly: 290.00
```

### How Tiers Work for Users

- **Free users**: Get your free tier automatically. No payment needed.
- **App Pass ($29/mo)**: Unlocks Pro tier on ALL marketplace apps (including yours).
- **App Pass+ ($49/mo)**: Unlocks Enterprise tier on ALL marketplace apps.
- **Standalone purchase**: Users can buy just your app's Pro/Enterprise tier directly.

You earn revenue from:
1. **Revenue pool** — share of App Pass subscriptions based on your install count
2. **Standalone sales** — 70% of direct purchases

---

## CloverStack Integrations

Connect your app to the CloverStack ecosystem.

### Chappie AI (Ollama)

Give your app AI capabilities via the local Ollama instance.

```yaml
# In cloverapp.yml
integrations:
  chappie:
    enabled: true
    description: AI-powered content suggestions
    models:
      - name: llama3.2:3b
        purpose: Content generation and summarization
```

```yaml
# In docker-compose.yml, your app connects to Ollama via:
services:
  wiki:
    environment:
      - OLLAMA_HOST=http://ollama:11434
    networks:
      - default
      - cloverstack  # Shared network with Ollama

networks:
  cloverstack:
    external: true
```

### MyCloverVault SSO

Let users log in with their MyCloverVault credentials.

```yaml
integrations:
  vault:
    enabled: true
    description: Single sign-on via MyCloverVault
    scopes:
      - openid
      - profile
      - email
```

Your app receives an OIDC configuration at runtime:
- `VAULT_OIDC_ISSUER` — Vaultwarden OIDC endpoint
- `VAULT_OIDC_CLIENT_ID` — Auto-provisioned client ID
- `VAULT_OIDC_CLIENT_SECRET` — Auto-provisioned secret

### NetMon Health Monitoring

Register a health endpoint and NetMon will monitor it.

```yaml
integrations:
  netmon:
    enabled: true
    description: Uptime monitoring and alerts
    healthcheck:
      endpoint: /api/health
      interval: 60
```

### SentryLog Centralized Logging

Send your app's logs to SentryLog automatically.

```yaml
integrations:
  sentrylog:
    enabled: true
    description: Centralized log collection
    log_driver: syslog
```

```yaml
# docker-compose.yml — logging config added automatically
services:
  wiki:
    logging:
      driver: syslog
      options:
        syslog-address: "tcp://sentrylog:514"
        tag: "cloverapp-my-wiki-app"
```

### Citadel Backup

Include your data volumes in CloverStack's backup system.

```yaml
integrations:
  backup:
    enabled: true
    description: Daily automated backups
    schedule: "0 3 * * *"

storage:
  volumes:
    - name: wiki-data
      mount: /app/data
      backup: true      # This volume gets backed up
```

---

## Lifecycle Hooks

Run custom scripts at key moments.

### hooks/pre-install.sh
```bash
#!/bin/bash
# Check for specific system requirements
if ! command -v ffmpeg &>/dev/null; then
    echo "[pre-install] Note: ffmpeg not found. Video features will be limited."
fi
```

### hooks/post-install.sh
```bash
#!/bin/bash
# Initialize database, create admin user, etc.
echo "[post-install] Waiting for database..."
sleep 5
docker exec my-wiki-app-wiki-1 wiki init-db
echo "[post-install] Database initialized."
```

### hooks/pre-upgrade.sh
```bash
#!/bin/bash
# Backup data before upgrading
echo "[pre-upgrade] Creating pre-upgrade backup..."
tar -czf /opt/cloverstack/backups/my-wiki-app-pre-upgrade.tar.gz \
    /opt/cloverstack/marketplace/apps/my-wiki-app/
```

### hooks/post-upgrade.sh
```bash
#!/bin/bash
# Run database migrations
echo "[post-upgrade] Running migrations..."
docker exec my-wiki-app-wiki-1 wiki migrate
```

---

## Security Requirements

Your app MUST follow these rules:

| Rule | Why |
|------|-----|
| No `privileged: true` | Prevents container escape |
| No `network_mode: host` | Apps get isolated networks |
| No bind mounts to `/`, `/etc`, `/var` | Only `/opt/cloverstack` and `/etc/myclover/apps` allowed |
| Pinned image tags | `myimage:1.2.3` not `myimage:latest` — reproducible builds |
| No telemetry without consent | Users must explicitly opt-in to any data collection |
| Run as non-root | Use `USER` directive in Dockerfile when possible |
| Health check required | Apps must respond to health probes |

### Image Security Scanning

All submitted images are scanned with [Trivy](https://trivy.dev/) for:
- Known CVEs (Critical/High must be fixed before approval)
- Embedded secrets or credentials
- Misconfigured file permissions
- Outdated base images

---

## Testing Your App

### Local Testing (Before Submission)

```bash
# 1. Validate manifest
clovermarket validate

# 2. Test free tier
docker compose up -d
curl http://localhost:8080/health

# 3. Test pro tier (if applicable)
docker compose -f docker-compose.yml -f docker-compose.pro.yml up -d

# 4. Test resource limits
# Ensure your app works within declared minimums
docker compose up -d
docker stats  # Watch CPU/RAM usage
```

### Reference Hardware

Test on the smallest target hardware to ensure a good experience:
- **Puck** (N100, 16GB RAM) — if your app targets `micro` edition
- **Edge** (Ryzen 7, 32GB RAM) — standard reference
- **VM** (2 vCPU, 4GB RAM) — minimum viable test

---

## Publishing Updates

```bash
# 1. Bump version in cloverapp.yml
# 2. Update CHANGELOG
# 3. Validate
clovermarket validate

# 4. Submit update
clovermarket submit

# Updates go through expedited review (24hr)
# Existing users get the update via: clovermarket update
```

---

## Earning Revenue

### Revenue Streams

1. **App Pass Pool** — Your share of the monthly subscription pool, based on weighted installs
2. **Standalone Sales** — 70/30 split on direct app purchases
3. **CloverCoin Tips** — Users can tip creators with CloverCoins

### Creator Dashboard

Track your earnings at `creator.myclover.tech/dashboard`:
- Install count (free, pro, enterprise)
- Revenue breakdown (pool share, standalone, tips)
- User ratings and reviews
- Download trends
- Payout history

### Payout Schedule

- Monthly on the 15th
- Minimum payout: $10 (rolls over)
- Payment methods: Stripe Connect (bank transfer, PayPal)

---

## Example Apps for Inspiration

| App Idea | Category | Complexity |
|----------|----------|-----------|
| Static site server | dev-tools | Simple |
| Bookmark manager | productivity | Simple |
| RSS reader | media | Simple |
| Recipe manager | home-automation | Medium |
| Invoice generator | business | Medium |
| Code snippet manager | dev-tools | Medium |
| Home energy monitor | iot | Medium |
| Time tracker | productivity | Medium |
| Git hosting (Gitea) | dev-tools | Complex |
| Photo gallery | media | Complex |
| ERP system | business | Complex |
| Home automation hub | home-automation | Complex |

---

## FAQ

**Q: Do I need to open-source my app?**
A: No. Any valid SPDX license is accepted. Open-source is encouraged but not required.

**Q: Can I use proprietary Docker images?**
A: Yes, as long as they pass security scanning and don't require host-level access.

**Q: What if my app needs a database?**
A: Include it in your Docker Compose stack. PostgreSQL, MySQL, Redis, etc. are all fine. Or declare a dependency on a database CloverApp.

**Q: How do I handle app configuration?**
A: Use environment variables (declared in `cloverapp.yml`). Auto-generated secrets use `generate: true`. User-provided values use `prompt: true`. Config files go in `/etc/myclover/apps/{your-app}/`.

**Q: Can my app use GPUs?**
A: Yes — set `resources.gpu: true` in your manifest. The runtime will pass through NVIDIA GPUs if available.

**Q: What's the review process like?**
A: Automated security scan (instant) + manual functionality review (within 48 hours). Most apps are approved within 24 hours. We'll give specific feedback if anything needs fixing.

**Q: How do I get featured?**
A: High-quality apps with good ratings, active maintenance, and unique functionality get featured. Focus on building something great.

---

## Resources

- [CloverApp Manifest Spec](CLOVERAPP-SPEC.md) — Full YAML reference
- [CloverMarket Overview](CLOVERMARKET.md) — Architecture and revenue model
- [CloverStack Docs](ARCHITECTURE.md) — System architecture
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Trivy Scanner](https://trivy.dev/) — Security scanning tool
- Creator Portal: `creator.myclover.tech`
- Support: `#clovermarket` on Slack or `support@myclover.tech`
