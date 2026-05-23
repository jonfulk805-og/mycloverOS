# Chappie AI — Quick Start Guide

> **CloverOS R1 (Seedling)**  
> **Last updated:** 2026-05-23  
> **Audience:** Anyone running CloverOS — no AI or Linux experience required

---

## What Is Chappie?

Chappie is CloverOS's built-in AI assistant. It runs 100% locally on your hardware — no cloud, no subscriptions, no data leaving your box. Under the hood it's powered by two components:

| Component | What It Does | Port |
|-----------|-------------|------|
| **Ollama** | AI engine — downloads, manages, and runs models | `11434` |
| **Open WebUI** | Chat interface — the web UI you talk to Chappie through | `8083` |

Ollama runs natively on the host. Open WebUI runs as a Docker container managed by CloverStack.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Start Chappie](#2-start-chappie)
3. [Open the Chat UI](#3-open-the-chat-ui)
4. [Create Your Account](#4-create-your-account)
5. [Add AI Models](#5-add-ai-models)
6. [Select a Model & Start Chatting](#6-select-a-model--start-chatting)
7. [Model Recommendations by Hardware](#7-model-recommendations-by-hardware)
8. [Manage Models](#8-manage-models)
9. [Advanced: Ollama Configuration](#9-advanced-ollama-configuration)
10. [Advanced: Connect Apps to Chappie](#10-advanced-connect-apps-to-chappie)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

- A running CloverOS box (installed and provisioned)
- SSH access to the CloverOS box (via PuTTY or terminal) — see [Setup Companion](SETUP-COMPANION.md)
- Another device on the same network with a web browser
- **Minimum:** 4 GB RAM (8 GB+ recommended for good performance)
- **Minimum:** 20 GB free disk space (models range from 2–40 GB each)

---

## 2. Start Chappie

SSH into your CloverOS box and run:

```bash
sudo cloverstack-ctl start chappie
```

Verify it's running:

```bash
sudo cloverstack-ctl status
```

You should see `chappie` listed as `ENABLED: yes` and `RUNNING: yes`.

You can also confirm the Docker container is up:

```bash
sudo docker ps | grep open-webui
```

> **Note:** Chappie is one of the default modules — it's enabled automatically during provisioning. If it's not enabled, run:
> ```bash
> sudo cloverstack-ctl enable chappie
> sudo cloverstack-ctl start chappie
> ```

---

## 3. Open the Chat UI

On your other computer or phone, open a web browser and go to:

```
http://<your-cloverOS-ip>:8083
```

Replace `<your-cloverOS-ip>` with the actual IP address of your CloverOS box. If you don't know the IP, use Angry IP Scanner or run `ip a` via SSH.

> **Tip:** Bookmark this URL — you'll use it every time you want to chat with Chappie.

---

## 4. Create Your Account

The first time you visit the Chappie UI:

1. Click **Sign Up**
2. Enter your name, email, and a password
3. Click **Create Account**

> **First account = Admin.** The first account created automatically becomes the administrator. You can manage users, models, and settings from the admin panel.

---

## 5. Add AI Models

Chappie needs at least one AI model to work. Models are downloaded and managed through Ollama on the command line.

### Pull Your First Model

SSH into your CloverOS box and run:

```bash
ollama pull llama3.2:3b
```

This downloads the Llama 3.2 3B model (~2 GB). It's a great starting model for most hardware.

### Pull Additional Models

```bash
ollama pull llama3.1          # 8B parameters — solid all-rounder (~4.7 GB)
ollama pull mistral            # 7B — fast and capable (~4.1 GB)
ollama pull phi3               # 3.8B — Microsoft's compact model (~2.3 GB)
ollama pull gemma2             # 9B — Google's model (~5.4 GB)
ollama pull codellama          # 7B — optimized for code (~3.8 GB)
ollama pull llama3.1:70b       # 70B — heavy, needs 64 GB+ RAM (~40 GB)
```

### See Available Models

Browse all available models at: **https://ollama.com/library**

---

## 6. Select a Model & Start Chatting

1. Open Chappie's web UI: `http://<your-cloverOS-ip>:8083`
2. At the top of the chat window, click the **model picker dropdown**
3. Select any model you've pulled — they appear automatically
4. Type your message and hit Enter

That's it — you're chatting with a fully private, local AI.

---

## 7. Model Recommendations by Hardware

Not sure which model to pull? Use this guide based on your hardware:

### Micro Appliances / GMKTek Mini (8–16 GB RAM)

| Model | Size | Best For |
|-------|------|----------|
| `phi3` | 2.3 GB | Quick answers, lightweight tasks |
| `gemma2:2b` | 1.6 GB | Ultra-light, fast responses |
| `llama3.2:3b` | 2.0 GB | Best balance of size and quality |

> **Tip:** Stick to models under 4B parameters. Larger models will be very slow or run out of memory.

### Edge / Desktop (32 GB RAM)

| Model | Size | Best For |
|-------|------|----------|
| `llama3.1` | 4.7 GB | General-purpose — great default |
| `mistral` | 4.1 GB | Fast, good at reasoning |
| `gemma2` | 5.4 GB | Solid alternative to Llama |
| `codellama` | 3.8 GB | Writing and debugging code |

### Rack / High-End (64 GB+ RAM or GPU)

| Model | Size | Best For |
|-------|------|----------|
| `llama3.1:70b` | 40 GB | Top-tier quality, needs big iron |
| `mixtral` | 26 GB | Mixture of experts — fast for its size |
| `command-r` | 20 GB | Great for RAG and retrieval tasks |

### With a Dedicated GPU

If your CloverOS box has an NVIDIA GPU, Ollama automatically uses it for inference. This dramatically speeds up larger models. Check GPU detection:

```bash
ollama ps
nvidia-smi    # If NVIDIA GPU is installed
```

---

## 8. Manage Models

### List Installed Models

```bash
ollama list
```

Output shows model name, size, and when it was last modified.

### Remove a Model

```bash
ollama rm <model-name>
```

Example: `ollama rm codellama`

### Update a Model

Pull it again to get the latest version:

```bash
ollama pull llama3.1
```

### Check What's Currently Loaded in Memory

```bash
ollama ps
```

Shows which model(s) are actively loaded and using RAM/VRAM.

---

## 9. Advanced: Ollama Configuration

### Ollama Service

Ollama runs as a systemd service on the host (not in Docker):

```bash
sudo systemctl status ollama     # Check status
sudo systemctl restart ollama    # Restart
sudo journalctl -u ollama -f     # View logs
```

### Environment Variables

Edit the Ollama service to change settings:

```bash
sudo systemctl edit ollama
```

Useful variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `0.0.0.0` | Listen address |
| `OLLAMA_MODELS` | `/usr/share/ollama/.ollama/models` | Model storage path |
| `OLLAMA_NUM_PARALLEL` | `1` | Concurrent requests |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Models kept in memory |

After editing, reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Move Model Storage

If you want models on a different drive (e.g., a larger data disk):

```bash
sudo systemctl edit ollama
```

Add:
```ini
[Service]
Environment="OLLAMA_MODELS=/mnt/data/ollama/models"
```

Then move existing models and restart:

```bash
sudo mv /usr/share/ollama/.ollama/models /mnt/data/ollama/models
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

---

## 10. Advanced: Connect Apps to Chappie

Other CloverStack modules and CloverApps can use Chappie's AI via the Ollama API.

### API Endpoint

```
http://localhost:11434
```

From Docker containers on the `cloverstack` network:

```
http://host.docker.internal:11434
```

### Example: CloverApp Integration

In your `cloverapp.yml`:

```yaml
integrations:
  chappie:
    enabled: true
    description: AI-powered features
    models:
      - name: llama3.2:3b
        purpose: Content generation
```

In your `docker-compose.yml`:

```yaml
services:
  myapp:
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### API Quick Test

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Hello, Chappie!",
  "stream": false
}'
```

---

## 11. Troubleshooting

### Chappie UI won't load (port 8083)

```bash
# Check if the container is running
sudo docker ps | grep open-webui

# If not running, start it
sudo cloverstack-ctl start chappie

# Check container logs
sudo docker logs open-webui
```

### No models appear in the dropdown

Models must be pulled via `ollama pull` first. The UI only shows installed models.

```bash
ollama list              # Check what's installed
ollama pull llama3.2:3b  # Pull a model
```

Refresh the Chappie web page — models appear automatically.

### Model is very slow

- Check available RAM: `free -h`
- Check if the model fits in memory — a model should be smaller than your available RAM
- Use a smaller model (see [recommendations](#7-model-recommendations-by-hardware))
- Check CPU usage: `htop`
- If you have a GPU, verify Ollama sees it: `ollama ps`

### "Connection refused" or Ollama errors in UI

```bash
# Check if Ollama is running
sudo systemctl status ollama

# Restart Ollama
sudo systemctl restart ollama

# Check Ollama logs
sudo journalctl -u ollama --no-pager -n 50
```

### Out of disk space

```bash
df -h                     # Check disk space
ollama list               # See model sizes
ollama rm <model-name>    # Remove models you don't need
```

### Reset Chappie (start fresh)

```bash
sudo cloverstack-ctl stop chappie
sudo docker rm open-webui
sudo cloverstack-ctl start chappie
```

> **Warning:** This removes your chat history and user accounts. Models in Ollama are not affected.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start Chappie | `sudo cloverstack-ctl start chappie` |
| Stop Chappie | `sudo cloverstack-ctl stop chappie` |
| Check status | `sudo cloverstack-ctl status` |
| List models | `ollama list` |
| Pull a model | `ollama pull <model>` |
| Remove a model | `ollama rm <model>` |
| Check loaded models | `ollama ps` |
| Restart Ollama engine | `sudo systemctl restart ollama` |
| View Ollama logs | `sudo journalctl -u ollama -f` |
| View Open WebUI logs | `sudo docker logs open-webui` |
| Chappie Web UI | `http://<ip>:8083` |
| Ollama API | `http://<ip>:11434` |

---

## Related Docs

- [CloverOS Quick Start](QUICKSTART.md) — Full CloverOS install & setup
- [Setup Companion](SETUP-COMPANION.md) — Apps you need on your other computer
- [Module Guide](MODULE-GUIDE.md) — All CloverStack modules
- [Port Map](PORT-MAP.md) — Complete port reference
- [Creator Guide](CREATOR-GUIDE.md) — Build apps that integrate with Chappie

---

*Built with 🍀 by MyClover.Tech*
