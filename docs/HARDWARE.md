# Supported Hardware

## Citadel Appliance Line

| Model | CPU | RAM | Storage | GPU | Edition |
|-------|-----|-----|---------|-----|---------|
| Puck ($299) | Intel N100, 4C | 16 GB | 256 GB NVMe | iGPU | Micro |
| Edge ($499) | Ryzen 7, 8C | 32 GB | 512 GB NVMe | iGPU | Desktop |
| Edge Pro ($799) | Ryzen 9, 12C | 64 GB | 1 TB NVMe | iGPU | Desktop |
| N5 Pro NAS ($5,499) | AMD Ryzen | 64 GB | Multi-bay | Optional | Server |
| R4 Rack 1U | Xeon/EPYC | 64 GB | 4-bay | Optional | Server |
| R8 Rack 2U | Xeon/EPYC | 128 GB | 8-bay | Optional | Server |
| R16 Rack 3U | Xeon/EPYC | 256 GB | 16-bay | 1-2x GPU | Server |
| Field Laptop | Intel/AMD | 32 GB | 1 TB NVMe | dGPU | Desktop |

## Generic Hardware Requirements

### Minimum (Headless Server)
- x86_64 CPU, 2+ cores
- 4 GB RAM
- 32 GB storage
- 1x Ethernet NIC

### Recommended (Desktop + Basic AI)
- x86_64 CPU, 4+ cores
- 16 GB RAM
- 128 GB SSD/NVMe
- 1x Ethernet NIC
- Wi-Fi (optional)

### Optimal (Full Suite + AI Models)
- x86_64 CPU, 8+ cores
- 32+ GB RAM
- 512+ GB NVMe
- NVIDIA GPU with 8+ GB VRAM (for large AI models)
- 2x Ethernet NIC (management + monitoring)

## GPU Support

### NVIDIA (Recommended for AI)
- Driver: `nvidia-driver` (non-free)
- CUDA: Ollama auto-detects
- Tested: GTX 1060+, RTX 2000+, RTX 3000+, RTX 4000+, Tesla T4, A100

### AMD
- Driver: `amdgpu` (built-in kernel driver)
- ROCm: Manual setup required for Ollama GPU acceleration
- Tested: RX 580+, RX 6000+, RX 7000+

### Intel iGPU
- Driver: `i915` (built-in)
- Used for: Display, basic video processing
- AI: CPU-only with Intel iGPU (no Ollama GPU accel yet)

## Network Interfaces

- Any standard Ethernet NIC (Intel, Realtek, Broadcom)
- USB Ethernet adapters
- Wi-Fi: Intel (iwlwifi), Realtek, Atheros (may need non-free firmware)
- WireGuard: Kernel module (no special hardware needed)

## Industrial Hardware (SCADA/ICS)

- OnLogic Helix series
- Advantech UNO/ARK series
- Axiomtek eBOX series
- DIN-rail mount, wide temp (-40C to +85C)
- Isolated serial (RS-232/485), isolated Ethernet
