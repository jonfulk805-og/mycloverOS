# CloverStack Port Map

## Core Infrastructure

| Port | Protocol | Service | Module |
|------|----------|---------|--------|
| 80 | TCP | Traefik HTTP (→ HTTPS) | Core |
| 443 | TCP | Traefik HTTPS | Core |
| 8080 | TCP | Traefik Dashboard / Setup Wizard | Core |
| 9443 | TCP | Portainer | Core |

## Module Web UIs

| Port | Service | Module |
|------|---------|--------|
| 8081 | Zabbix Web | NetMon |
| 8082 | Vaultwarden | MyClover Vault |
| 8083 | Open WebUI (Chappie) | Chappie AI |
| 8084 | Anthias (Signage) | CloverSign |
| 8085 | Pi-hole Admin | CloverGuard |
| 8086 | Mining Dashboard | CloverMine |
| 8087 | ERPNext | CloverPOS |
| 8088 | ComfyUI | CloverDesign |
| 8089 | LibreChat | CloverBot |
| 8090 | Drone Dashboard | CloverDrone |
| 8091 | Netmaker API | CloverMesh |
| 8092 | Netmaker UI | CloverMesh |
| 8093 | Meshtastic Web | CloverMesh Radio |
| 8094 | Owncast | StreamServer |
| 8096 | Jellyfin | CloverMedia |
| 4533 | Navidrome (Music) | CloverMedia |
| 9000 | Graylog | SentryLog |

## Service Ports

| Port | Protocol | Service | Module |
|------|----------|---------|--------|
| 22 | TCP | SSH | Core |
| 53 | TCP/UDP | DNS (Pi-hole) | CloverGuard |
| 1514 | TCP/UDP | Syslog | SentryLog |
| 1515 | TCP | Wazuh Agent Registration | SentryLog |
| 1884 | TCP | MQTT (Radio) | CloverMesh Radio |
| 1900 | UDP | DLNA | CloverMedia |
| 1935 | TCP | RTMP Ingest | StreamServer |
| 3012 | TCP | Vaultwarden WebSocket | MyClover Vault |
| 3128 | TCP | Squid Proxy | CloverGuard |
| 8554 | TCP | RTSP | CloverDrone |
| 8555 | TCP | RTSP | StreamServer |
| 8888 | TCP | HLS | StreamServer |
| 9710 | TCP | SRT Ingest | StreamServer |
| 10051 | TCP | Zabbix Server | NetMon |
| 11434 | TCP | Ollama API (native) | Core AI |
| 12201 | TCP/UDP | GELF | SentryLog |
| 14550 | UDP | MAVLink | CloverDrone |
| 51821 | UDP | WireGuard (Mesh) | CloverMesh |
| 55000 | TCP | Wazuh API | SentryLog |
