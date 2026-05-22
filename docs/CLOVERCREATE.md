# 🍀 CloverOS Creator Edition

**Create. Stream. Publish. Profit.**

A full content creation workstation: video editing, 3D rendering, music production, game dev, AI art, live streaming — all pre-configured with CloverMesh distributed rendering.

## Quick Start

```bash
sudo ./build.sh creator

# Create a project
clovercreate project new youtube-video my-first-video

# Start streaming
clovercreate stream start --key your-stream-key

# Chat with local AI
clovercreate ai chat

# Distributed render across mesh
clovercreate render mesh scene.blend -s 1 -e 500
```

## Pre-Installed Tools

### Video
- **Kdenlive** — Professional video editor
- **Shotcut** — Lightweight video editor
- **OBS Studio** — Streaming + recording
- **FFmpeg** — CLI video processing

### Audio
- **Audacity** — Audio editor
- **Ardour** — DAW (Digital Audio Workstation)
- **LMMS** — Music production
- **JACK** — Low-latency audio server

### 3D / Game Dev
- **Blender** — 3D modeling, animation, rendering
- **Godot** — Game engine (auto-installed)

### Graphics
- **GIMP** — Photo editing
- **Inkscape** — Vector graphics
- **Krita** — Digital painting
- **Darktable** — RAW photo processing

### AI Tools
- **Ollama** — Local LLM (llama3.2, codellama, llava)
- **Whisper** — Audio transcription
- **Stable Diffusion** — AI image generation (optional)

### Publishing
- **Scribus** — Desktop publishing
- **LibreOffice** — Documents/presentations
- **Firefox + Chromium** — Web browsers

## Project Templates

```
clovercreate project new youtube-video <name>
clovercreate project new podcast <name>
clovercreate project new music-production <name>
clovercreate project new 3d-animation <name>
clovercreate project new game-dev <name>
clovercreate project new graphic-design <name>
clovercreate project new photo-editing <name>
clovercreate project new livestream <name>
clovercreate project new web-dev <name>
clovercreate project new ai-art <name>
```

## CloverMesh Render Farm

Distribute Blender renders across multiple Creator nodes:

```bash
# On primary node
clovercreate mesh init my-render-farm

# On additional nodes
clovercreate mesh join 192.168.1.10

# Render across all nodes
clovercreate render mesh animation.blend -s 1 -e 1000
# 1000 frames ÷ 4 nodes = 250 frames each, parallel
```

## Streaming Server

Built-in RTMP server with HLS output:

```bash
clovercreate stream start
# RTMP: rtmp://<ip>:1935/live
# HLS:  http://<ip>:8088/hls/stream.m3u8

# Point OBS to rtmp://localhost:1935/live
```

## CLI Reference

```
clovercreate project new|list|open|templates
clovercreate render local|mesh|status|cancel
clovercreate stream start|stop|status|record
clovercreate ai chat|models|pull|transcribe
clovercreate gpu status|drivers|benchmark
clovercreate audio setup|latency|devices
clovercreate app install godot|vscode|ollama|streaming
clovercreate mesh init|join|status|nodes
clovercreate status
```

## Hardware Recommendations

| Tier | CPU | RAM | GPU | Storage | Use Case |
|------|-----|-----|-----|---------|----------|
| Starter | Ryzen 5 | 16GB | Integrated | 512GB SSD | YouTube, podcasts |
| Pro | Ryzen 7/i7 | 32GB | RTX 3060+ | 1TB NVMe | Video, 3D, streaming |
| Studio | Ryzen 9/i9 | 64GB | RTX 4070+ | 2TB NVMe | 4K video, VFX, AI |
| Render Farm | Multi-node | 128GB+ | Multi-GPU | NVMe | Distributed rendering |

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | All tools, local AI, single node |
| Pro | $29/mo | Streaming server, mesh rendering, priority support |
| Studio | $79/mo | Multi-node render, cloud sync, advanced AI |
