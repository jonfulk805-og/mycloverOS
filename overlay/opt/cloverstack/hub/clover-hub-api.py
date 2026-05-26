#!/usr/bin/env python3
"""
CloverOS Service Hub -- API Backend
Lightweight REST API that wraps cloverstack-ctl for the web dashboard.
Runs as a systemd service on port 7777.
"""
import http.server
import json
import subprocess
import os
import re
import socketserver
import threading
import time
import socket

PORT = 7777
CLOVERSTACK_ROOT = "/opt/cloverstack"
MODULES_DIR = "/etc/myclover/modules.d"
CATALOG_FILE = "/opt/cloverstack/cloverdeploy/catalog/manifest.json"

# ---- Service registry (modules with web UIs) --------------------------------
# Format: id -> {name, desc, port, category, icon, docker_image, ha}
# Ports sourced from the clovernas catalog + cloverstack-ctl module list

CLOVERSTACK_MODULES = {
    "netmon":         {"name": "NetMon",          "desc": "Network monitoring (Zabbix)",
                       "port": 8081, "category": "CloverStack Core", "icon": "satellite"},
    "sentrylog":      {"name": "SentryLog",       "desc": "Log management (Graylog + Wazuh)",
                       "port": 9000, "category": "CloverStack Core", "icon": "scroll"},
    "myclover-vault": {"name": "MyClover Vault",  "desc": "Password manager (Vaultwarden)",
                       "port": 8082, "category": "CloverStack Core", "icon": "lock"},
    "chappie":        {"name": "Chappie AI",      "desc": "AI assistant (Ollama + Open WebUI)",
                       "port": 8083, "category": "CloverStack Core", "icon": "brain"},
    "chatbox-team":   {"name": "Chatbox Team",    "desc": "Shared AI API proxy",
                       "port": 8095, "category": "CloverStack Core", "icon": "message-square"},
    "anythingllm":    {"name": "AnythingLLM",     "desc": "AI chat + document workspaces",
                       "port": 8097, "category": "CloverStack Core", "icon": "file-text"},
    "clovermarket":   {"name": "CloverMarket",    "desc": "App marketplace",
                       "port": 8090, "category": "CloverStack Core", "icon": "shopping-bag"},
    "clovermedia":    {"name": "CloverMedia",      "desc": "Smart TV + streaming + DJ",
                       "port": 8096, "category": "CloverStack Core", "icon": "tv"},
    "cloversign":     {"name": "CloverSign",      "desc": "Digital signage",
                       "port": 8084, "category": "CloverStack Core", "icon": "monitor"},
    "cloverguard":    {"name": "CloverGuard",     "desc": "DNS ad blocking + web proxy",
                       "port": 8085, "category": "CloverStack Core", "icon": "shield",
                       "extra_ports": {"Squid Proxy": 3128}},
    "clovermine":     {"name": "CloverMine",      "desc": "Crypto mining",
                       "port": 8086, "category": "CloverStack Core", "icon": "cpu"},
    "cloverpos":      {"name": "CloverPOS",       "desc": "Point of sale (ERPNext)",
                       "port": 8087, "category": "CloverStack Core", "icon": "credit-card"},
    "cloverdesign":   {"name": "CloverDesign",    "desc": "AI design studio (ComfyUI)",
                       "port": 8088, "category": "CloverStack Core", "icon": "pen-tool"},
    "cloverbot":      {"name": "CloverBot",       "desc": "AI support chatbot (LibreChat)",
                       "port": 8089, "category": "CloverStack Core", "icon": "bot"},
    "cloverdrone":    {"name": "CloverDrone",     "desc": "UAV control",
                       "port": 8090, "category": "CloverStack Core", "icon": "navigation",
                       "extra_ports": {"MAVLink": 14550}},
    "streamserver":   {"name": "StreamServer",    "desc": "Live streaming platform",
                       "port": 8094, "category": "CloverStack Core", "icon": "video",
                       "extra_ports": {"RTMP": 1935}},
    "clovermesh":     {"name": "CloverMesh",      "desc": "WireGuard mesh networking",
                       "port": 8092, "category": "CloverStack Core", "icon": "globe",
                       "extra_ports": {"API": 8091}},
    "clovermesh-radio": {"name": "CloverMesh Radio", "desc": "LoRa mesh (Meshtastic)",
                       "port": 8093, "category": "CloverStack Core", "icon": "radio"},
}

DEPLOY_CATALOG = {
    # Productivity
    "nextcloud":      {"name": "Nextcloud",       "desc": "File sync, calendar, contacts",
                       "port": 8080, "category": "Productivity", "icon": "cloud",
                       "image": "nextcloud:latest", "ha": True},
    "onlyoffice":     {"name": "OnlyOffice",      "desc": "Document editor suite",
                       "port": 8081, "category": "Productivity", "icon": "file-plus",
                       "image": "onlyoffice/documentserver:latest", "ha": False},
    "vaultwarden":    {"name": "Vaultwarden",     "desc": "Password manager (Bitwarden)",
                       "port": 8082, "category": "Productivity", "icon": "lock",
                       "image": "vaultwarden/server:latest", "ha": True},
    "bookstack":      {"name": "BookStack",       "desc": "Wiki & documentation",
                       "port": 8083, "category": "Productivity", "icon": "book-open",
                       "image": "lscr.io/linuxserver/bookstack:latest", "ha": False},
    # Media
    "plex":           {"name": "Plex",            "desc": "Media server",
                       "port": 32400, "category": "Media", "icon": "play-circle",
                       "image": "plexinc/pms-docker:latest", "ha": False},
    "jellyfin":       {"name": "Jellyfin",        "desc": "Free media server",
                       "port": 8096, "category": "Media", "icon": "film",
                       "image": "jellyfin/jellyfin:latest", "ha": False},
    "photoprism":     {"name": "PhotoPrism",      "desc": "AI-powered photo management",
                       "port": 2342, "category": "Media", "icon": "image",
                       "image": "photoprism/photoprism:latest", "ha": False},
    # Networking
    "pihole":         {"name": "Pi-hole",         "desc": "DNS-level ad blocking",
                       "port": 8084, "category": "Networking", "icon": "x-circle",
                       "image": "pihole/pihole:latest", "ha": True},
    "traefik":        {"name": "Traefik",         "desc": "Reverse proxy + SSL",
                       "port": 8085, "category": "Networking", "icon": "globe",
                       "image": "traefik:latest", "ha": True},
    "wireguard-ui":   {"name": "WireGuard UI",    "desc": "VPN management",
                       "port": 5000, "category": "Networking", "icon": "shield",
                       "image": "ngoduykhanh/wireguard-ui:latest", "ha": False},
    # Databases
    "postgresql":     {"name": "PostgreSQL",      "desc": "Advanced relational database",
                       "port": 5432, "category": "Databases", "icon": "database",
                       "image": "postgres:16", "ha": True, "no_web_ui": True},
    "mariadb":        {"name": "MariaDB",         "desc": "MySQL-compatible database",
                       "port": 3306, "category": "Databases", "icon": "database",
                       "image": "mariadb:latest", "ha": True, "no_web_ui": True},
    "redis":          {"name": "Redis",           "desc": "In-memory data store",
                       "port": 6379, "category": "Databases", "icon": "zap",
                       "image": "redis:latest", "ha": True, "no_web_ui": True},
    "mongodb":        {"name": "MongoDB",         "desc": "Document database",
                       "port": 27017, "category": "Databases", "icon": "database",
                       "image": "mongo:latest", "ha": False, "no_web_ui": True},
    # Monitoring
    "grafana":        {"name": "Grafana",         "desc": "Dashboards & visualization",
                       "port": 3000, "category": "Monitoring", "icon": "bar-chart-2",
                       "image": "grafana/grafana:latest", "ha": False},
    "prometheus":     {"name": "Prometheus",      "desc": "Metrics collection",
                       "port": 9090, "category": "Monitoring", "icon": "activity",
                       "image": "prom/prometheus:latest", "ha": False},
    "uptime-kuma":    {"name": "Uptime Kuma",     "desc": "Uptime monitoring",
                       "port": 3001, "category": "Monitoring", "icon": "heart",
                       "image": "louislam/uptime-kuma:latest", "ha": True},
    "portainer":      {"name": "Portainer",       "desc": "Docker management UI",
                       "port": 9443, "category": "Monitoring", "icon": "box",
                       "image": "portainer/portainer-ce:latest", "ha": False},
    # Security
    "crowdsec":       {"name": "CrowdSec",        "desc": "Collaborative IPS",
                       "port": 8086, "category": "Security", "icon": "shield",
                       "image": "crowdsecurity/crowdsec:latest", "ha": True},
    "authentik":      {"name": "Authentik",       "desc": "Identity provider (SSO/LDAP)",
                       "port": 9443, "category": "Security", "icon": "users",
                       "image": "ghcr.io/goauthentik/server:latest", "ha": True},
    # Home / IoT
    "homeassistant":  {"name": "Home Assistant",  "desc": "Smart home control",
                       "port": 8123, "category": "Home / IoT", "icon": "home",
                       "image": "ghcr.io/home-assistant/home-assistant:stable", "ha": False},
    "mqtt":           {"name": "Mosquitto MQTT",  "desc": "IoT message broker",
                       "port": 1883, "category": "Home / IoT", "icon": "radio",
                       "image": "eclipse-mosquitto:latest", "ha": True, "no_web_ui": True},
    "nodered":        {"name": "Node-RED",        "desc": "Flow-based automation",
                       "port": 1880, "category": "Home / IoT", "icon": "git-branch",
                       "image": "nodered/node-red:latest", "ha": False},
    # Development
    "gitea":          {"name": "Gitea",           "desc": "Self-hosted Git",
                       "port": 3002, "category": "Development", "icon": "git-branch",
                       "image": "gitea/gitea:latest", "ha": True},
    "codeserver":     {"name": "Code Server",     "desc": "VS Code in the browser",
                       "port": 8443, "category": "Development", "icon": "code",
                       "image": "lscr.io/linuxserver/code-server:latest", "ha": False},
    "drone":          {"name": "Drone CI",        "desc": "Continuous integration",
                       "port": 8087, "category": "Development", "icon": "repeat",
                       "image": "drone/drone:latest", "ha": False},
    # AI / ML
    "ollama":         {"name": "Ollama",          "desc": "Local LLM inference",
                       "port": 11434, "category": "AI / ML", "icon": "cpu",
                       "image": "ollama/ollama:latest", "ha": False, "no_web_ui": True},
    "openwebui":      {"name": "Open WebUI",      "desc": "ChatGPT-like UI for Ollama",
                       "port": 3003, "category": "AI / ML", "icon": "message-circle",
                       "image": "ghcr.io/open-webui/open-webui:main", "ha": False},
    "localai":        {"name": "LocalAI",         "desc": "OpenAI-compatible local API",
                       "port": 8088, "category": "AI / ML", "icon": "zap",
                       "image": "localai/localai:latest", "ha": False},
    # Storage
    "minio":          {"name": "MinIO",           "desc": "S3-compatible object storage",
                       "port": 9001, "category": "Storage", "icon": "hard-drive",
                       "image": "minio/minio:latest", "ha": True},
}

DESKTOP_TEMPLATES = {
    "xfce":        {"name": "XFCE Desktop",       "image": "lscr.io/linuxserver/webtop:debian-xfce", "tier": "free"},
    "kde":         {"name": "KDE Plasma Desktop",  "image": "lscr.io/linuxserver/webtop:debian-kde",  "tier": "free"},
    "mate":        {"name": "MATE Desktop",        "image": "lscr.io/linuxserver/webtop:debian-mate", "tier": "free"},
    "i3":          {"name": "i3 Tiling WM",        "image": "lscr.io/linuxserver/webtop:debian-i3",   "tier": "free"},
    "openbox":     {"name": "Openbox Desktop",     "image": "lscr.io/linuxserver/webtop:debian-openbox", "tier": "free"},
    "icewm":       {"name": "IceWM Desktop",       "image": "lscr.io/linuxserver/webtop:debian-icewm",  "tier": "free"},
    "budgie":      {"name": "Budgie Desktop",      "image": "lscr.io/linuxserver/webtop:ubuntu-budgie", "tier": "free"},
    "kasm-desktop":{"name": "Kasm Full Desktop",   "image": "kasmweb/desktop:1.15.0", "tier": "premium"},
    "kasm-chrome": {"name": "Kasm Chrome Browser",  "image": "kasmweb/chrome:1.15.0",  "tier": "premium"},
    "kasm-firefox":{"name": "Kasm Firefox Browser", "image": "kasmweb/firefox:1.15.0", "tier": "premium"},
}


def get_host_ip():
    """Get the primary LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def check_port(port):
    """Check if a port is listening."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result == 0
    except Exception:
        return False


def get_module_status(module_id):
    """Check if a module is enabled and running."""
    enabled = os.path.exists(os.path.join(MODULES_DIR, f"{module_id}.enabled"))
    compose = os.path.join(CLOVERSTACK_ROOT, "modules", module_id, "docker-compose.yml")
    running = False
    if os.path.exists(compose):
        rc, out, _ = run_cmd(
            f"docker compose -f {compose} ps --status running -q 2>/dev/null"
        )
        running = rc == 0 and len(out.strip()) > 0
    return {"enabled": enabled, "running": running}


def get_deploy_app_status(app_id):
    """Check if a CloverDeploy app is installed and running."""
    compose_dir = os.path.join(CLOVERSTACK_ROOT, "cloverdeploy", "compose", app_id)
    installed = os.path.exists(compose_dir)
    running = False
    if installed:
        rc, out, _ = run_cmd(
            f"docker ps --filter 'label=clover.app={app_id}' "
            f"--format '{{{{.Status}}}}' 2>/dev/null"
        )
        running = rc == 0 and "Up" in out
    return {"installed": installed, "running": running}


def get_desktop_status():
    """List running desktop containers."""
    rc, out, _ = run_cmd(
        "docker ps --filter 'name=cloverdesktop-' "
        "--format '{{.Names}} {{.Ports}}' 2>/dev/null"
    )
    desktops = []
    if rc == 0 and out:
        for line in out.split("\n"):
            parts = line.split()
            if parts:
                name = parts[0]
                port_match = re.search(r":(\d+)->", " ".join(parts[1:]))
                port = int(port_match.group(1)) if port_match else None
                desktops.append({"name": name, "port": port})
    return desktops


class HubAPIHandler(http.server.BaseHTTPRequestHandler):
    """API request handler."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.rstrip("/")

        if path == "/api/status":
            self.handle_status()
        elif path == "/api/ip":
            self.send_json({"ip": get_host_ip()})
        elif path == "/api/services":
            self.handle_services()
        elif path == "/api/desktops":
            self.handle_desktops()
        elif path == "" or path == "/":
            self.serve_dashboard()
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = self.path.rstrip("/")
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        if path == "/api/module/enable":
            self.handle_module_action("enable", data)
        elif path == "/api/module/disable":
            self.handle_module_action("disable", data)
        elif path == "/api/module/start":
            self.handle_module_action("start", data)
        elif path == "/api/module/stop":
            self.handle_module_action("stop", data)
        elif path == "/api/module/restart":
            self.handle_module_action("restart", data)
        elif path == "/api/deploy/install":
            self.handle_deploy_install(data)
        elif path == "/api/deploy/remove":
            self.handle_deploy_remove(data)
        elif path == "/api/docker/pull":
            self.handle_docker_pull(data)
        elif path == "/api/desktop/start":
            self.handle_desktop_start(data)
        elif path == "/api/desktop/stop":
            self.handle_desktop_stop(data)
        else:
            self.send_json({"error": "Not found"}, 404)

    # ---- Handlers -----------------------------------------------------------

    def handle_status(self):
        """Full system status."""
        ip = get_host_ip()

        # Modules
        modules = {}
        for mod_id, info in CLOVERSTACK_MODULES.items():
            status = get_module_status(mod_id)
            port_open = check_port(info["port"])
            modules[mod_id] = {
                **info,
                **status,
                "port_open": port_open,
            }

        # Deploy apps
        apps = {}
        for app_id, info in DEPLOY_CATALOG.items():
            status = get_deploy_app_status(app_id)
            port_open = check_port(info["port"])
            apps[app_id] = {
                **info,
                **status,
                "port_open": port_open,
            }

        # Desktops
        desktops = get_desktop_status()

        self.send_json({
            "ip": ip,
            "modules": modules,
            "apps": apps,
            "desktops": desktops,
            "desktop_templates": DESKTOP_TEMPLATES,
        })

    def handle_services(self):
        """List all service definitions (no live status check)."""
        self.send_json({
            "modules": CLOVERSTACK_MODULES,
            "apps": DEPLOY_CATALOG,
            "desktop_templates": DESKTOP_TEMPLATES,
        })

    def handle_desktops(self):
        """List running desktops."""
        self.send_json({
            "running": get_desktop_status(),
            "templates": DESKTOP_TEMPLATES,
        })

    def handle_module_action(self, action, data):
        module_id = data.get("module")
        if not module_id:
            self.send_json({"error": "Missing 'module' parameter"}, 400)
            return
        # Sanitize
        module_id = re.sub(r"[^a-zA-Z0-9_-]", "", module_id)
        rc, out, err = run_cmd(f"cloverstack-ctl {action} {module_id}", timeout=60)
        self.send_json({
            "action": action,
            "module": module_id,
            "success": rc == 0,
            "output": out,
            "error": err,
        })

    def handle_deploy_install(self, data):
        app_id = data.get("app")
        if not app_id:
            self.send_json({"error": "Missing 'app' parameter"}, 400)
            return
        app_id = re.sub(r"[^a-zA-Z0-9_-]", "", app_id)
        rc, out, err = run_cmd(
            f"cloverstack-ctl deploy install {app_id}", timeout=300
        )
        self.send_json({
            "action": "install",
            "app": app_id,
            "success": rc == 0,
            "output": out,
            "error": err,
        })

    def handle_deploy_remove(self, data):
        app_id = data.get("app")
        if not app_id:
            self.send_json({"error": "Missing 'app' parameter"}, 400)
            return
        app_id = re.sub(r"[^a-zA-Z0-9_-]", "", app_id)
        rc, out, err = run_cmd(
            f"cloverstack-ctl deploy remove {app_id}", timeout=60
        )
        self.send_json({
            "action": "remove",
            "app": app_id,
            "success": rc == 0,
            "output": out,
            "error": err,
        })

    def handle_docker_pull(self, data):
        image = data.get("image")
        if not image:
            self.send_json({"error": "Missing 'image' parameter"}, 400)
            return
        # Basic sanitization (allow docker image chars)
        if not re.match(r"^[a-zA-Z0-9_./:@-]+$", image):
            self.send_json({"error": "Invalid image name"}, 400)
            return
        rc, out, err = run_cmd(f"docker pull {image}", timeout=600)
        self.send_json({
            "action": "pull",
            "image": image,
            "success": rc == 0,
            "output": out,
            "error": err,
        })

    def handle_desktop_start(self, data):
        desktop_id = data.get("desktop", "xfce")
        desktop_id = re.sub(r"[^a-zA-Z0-9_-]", "", desktop_id)
        rc, out, err = run_cmd(
            f"cloverdesktop start {desktop_id}", timeout=300
        )
        self.send_json({
            "action": "start_desktop",
            "desktop": desktop_id,
            "success": rc == 0,
            "output": out,
            "error": err,
        })

    def handle_desktop_stop(self, data):
        desktop_id = data.get("desktop", "xfce")
        instance = data.get("instance", "default")
        desktop_id = re.sub(r"[^a-zA-Z0-9_-]", "", desktop_id)
        instance = re.sub(r"[^a-zA-Z0-9_-]", "", instance)
        container = f"cloverdesktop-{desktop_id}-{instance}"
        rc, out, err = run_cmd(f"docker stop {container} && docker rm {container}", timeout=30)
        self.send_json({
            "action": "stop_desktop",
            "desktop": desktop_id,
            "success": rc == 0,
            "output": out,
            "error": err,
        })

    def serve_dashboard(self):
        """Serve the main HTML dashboard."""
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
        if os.path.exists(html_path):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(html_path, "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Dashboard HTML not found")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), HubAPIHandler)
    print(f"[clover-hub] Service Hub API running on port {PORT}")
    print(f"[clover-hub] Dashboard: http://{get_host_ip()}:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[clover-hub] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
