# Chatbox AI Integration — CloverOS

CloverOS integrates **Chatbox AI** as a native desktop chat client alongside its
existing browser-based AI interfaces (Chappie/Open WebUI and CloverBot/LibreChat).

## Overview

| Component | Type | Port | Edition |
|-----------|------|------|---------|
| **Chatbox Desktop** | Native AppImage | — | Desktop, Field Laptop |
| **Chatbox Team Proxy** | Docker (Caddy) | 8095 | All (opt-in) |
| **AnythingLLM** | Docker (web UI) | 8097 | All (opt-in) |

### Existing AI Chat Modules (unchanged)

| Module | Type | Port | Default |
|--------|------|------|---------|
| Chappie AI (Open WebUI) | Docker | 8083 | ✅ Enabled |
| CloverBot (LibreChat) | Docker | 8089 | Disabled |

---

## 1. Chatbox Desktop (Desktop Editions)

**What:** Native Electron desktop app for chatting with AI models.
**Where:** Pre-installed on Desktop and Field Laptop editions as an AppImage.

### Launch

- Application menu → **Chatbox AI**
- Terminal: `chatbox`

### Connect to Local Ollama

1. Open Chatbox AI
2. Go to **Settings → AI Model Provider**
3. Select **Ollama**
4. Set API Host: `http://localhost:11434`
5. Your locally-installed models appear automatically

### Features

- Chat with local models (Ollama) — fully offline
- Support for cloud providers (OpenAI, Claude, Gemini, Azure)
- Local data storage — conversations never leave the device
- Knowledge Base — RAG over private documents (desktop only)
- Prompt library, markdown/LaTeX rendering, code highlighting
- Team collaboration via shared API proxy

### Upstream

- Website: <https://chatboxai.app>
- GitHub: <https://github.com/chatboxai/chatbox>
- License: GPLv3 (Community Edition)

---

## 2. Chatbox Team Proxy (Docker Module)

**What:** Shared API proxy so multiple Chatbox desktop clients can share one
API key (OpenAI, Anthropic, etc.) without exposing it to end users.

**When useful:** Teams where everyone runs Chatbox desktop but you want a
single billed API key for cloud models.

### Enable

```bash
cloverstack-ctl enable chatbox-team
```

### Configure

Edit `/opt/cloverstack/.env` or set environment variables:

```bash
# Share an OpenAI key across the team:
CHATBOX_OPENAI_KEY=sk-xxxxxxxxxxxxxxxxxx

# Optional: set a domain for HTTPS
CHATBOX_DOMAIN=chatbox.yourdomain.com
```

### Team Setup

1. Enable the module on the CloverOS server
2. Share the server address with team: `http://<cloverOS-ip>:8095`
3. Team members open Chatbox desktop → Settings → API Host → enter the address
4. No API key needed on individual machines

### Upstream

- Docker image: `bensdocker/chatbox-team`
- Docs: <https://github.com/chatboxai/chatbox/tree/main/team-sharing>

---

## 3. AnythingLLM (Docker Module)

**What:** Full-featured browser-based AI chat platform with document
workspaces, RAG, AI agents, and multi-user support. The Docker-native
equivalent of Chatbox desktop — access from any browser on the network.

### Enable

```bash
cloverstack-ctl enable anythingllm
```

Then open: `http://<cloverOS-ip>:8097`

### Configure

Edit `/opt/cloverstack/.env`:

```bash
# Default Ollama model
ANYTHINGLLM_MODEL=phi3:mini

# Embedding model for RAG
ANYTHINGLLM_EMBED_MODEL=nomic-embed-text

# Optional: auth token
ANYTHINGLLM_AUTH=your-secret-token

# JWT secret
ANYTHINGLLM_JWT_SECRET=change-me-in-production
```

### Features

- Browser-based — access from any device on the network
- Document workspaces — upload PDFs, docs, code and chat with them
- Built-in RAG with LanceDB (zero-config vector store)
- AI agents with tool use
- Web scraping and URL ingestion
- Multi-user with auth
- Hot directory: drop files in the `anythingllm-hotdir` volume for auto-ingestion
- Connects to local Ollama (default) or any OpenAI-compatible API

### Upstream

- GitHub: <https://github.com/Mintplex-Labs/anything-llm>
- License: MIT

---

## AI Chat Comparison — Which Module When?

| Need | Best Module |
|------|-------------|
| Desktop power user, native app feel | **Chatbox Desktop** |
| Browser-based chat, any device on network | **Chappie AI** (Open WebUI, port 8083) |
| Document workspaces, RAG, agents | **AnythingLLM** (port 8097) |
| Multi-provider, MCP, admin controls | **CloverBot** (LibreChat, port 8089) |
| Team API key sharing | **Chatbox Team Proxy** (port 8095) |
| AI image generation | **CloverDesign** (ComfyUI, port 8088) |

All connect to the same local **Ollama** instance (port 11434). Same models,
consistent experience, different interfaces for different use cases.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     CloverOS Host                         │
│                                                           │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ Chatbox AI  │   │ Firefox/     │   │ Any browser  │  │
│  │ (AppImage)  │   │ Chromium     │   │ on network   │  │
│  └──────┬──────┘   └──────┬───────┘   └──────┬───────┘  │
│         │                 │                   │          │
│         │    ┌────────────┼───────────────────┤          │
│         │    │            │                   │          │
│         ▼    ▼            ▼                   ▼          │
│  ┌───────────────┐ ┌───────────┐ ┌────────────────────┐ │
│  │  Ollama API   │ │ Open WebUI│ │   AnythingLLM      │ │
│  │  :11434       │ │ (Chappie) │ │   :8097            │ │
│  │  (native)     │ │ :8083     │ │   [Docker]         │ │
│  └───────┬───────┘ └─────┬─────┘ └────────┬───────────┘ │
│          │               │                 │             │
│          └───────────────┴─────────────────┘             │
│                          │                               │
│                   ┌──────▼──────┐                        │
│                   │   Ollama    │                        │
│                   │  (models)   │                        │
│                   │ phi3, llama │                        │
│                   │ dolphin-x1  │                        │
│                   └─────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

## Updating

Chatbox Desktop:
```bash
# Via myclover-update
myclover-update --check

# Manual
curl -fsSL -o /opt/chatbox/Chatbox.AppImage \
  "$(curl -s https://api.github.com/repos/chatboxai/chatbox/releases/latest | \
     python3 -c "import sys,json; [print(a['browser_download_url']) for a in json.load(sys.stdin)['assets'] if 'linux' in a['name'].lower() and a['name'].endswith('.AppImage') and 'arm' not in a['name'].lower()]")"
chmod +x /opt/chatbox/Chatbox.AppImage
```

Docker modules:
```bash
cloverstack-ctl restart chatbox-team
cloverstack-ctl restart anythingllm
# Docker will pull the latest image on restart
```
