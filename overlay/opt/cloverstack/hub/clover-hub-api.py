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
import hashlib
import secrets
import http.cookies

PORT = 7777
CLOVERSTACK_ROOT = "/opt/cloverstack"
MODULES_DIR = "/etc/myclover/modules.d"
CATALOG_FILE = "/opt/cloverstack/cloverdeploy/catalog/manifest.json"
HUB_CONF = "/etc/myclover/hub.conf"
SESSION_TIMEOUT = 86400  # 24 hours

# ---- Authentication --------------------------------------------------------

_sessions = {}       # {token: expiry_timestamp}
_sessions_lock = threading.Lock()


def load_password_hash():
    """Load the admin password hash from hub.conf, or create default config."""
    if os.path.exists(HUB_CONF):
        try:
            with open(HUB_CONF) as f:
                conf = json.load(f)
            if "password_hash" in conf:
                return conf["password_hash"]
            # Migrate plaintext password to hash
            if "password" in conf:
                pw_hash = hashlib.sha256(conf["password"].encode()).hexdigest()
                conf["password_hash"] = pw_hash
                del conf["password"]
                with open(HUB_CONF, "w") as f:
                    json.dump(conf, f, indent=2)
                return pw_hash
        except Exception:
            pass
    # First run — default password is 'cloverOS'
    pw_hash = hashlib.sha256("cloverOS".encode()).hexdigest()
    os.makedirs(os.path.dirname(HUB_CONF), exist_ok=True)
    with open(HUB_CONF, "w") as f:
        json.dump({"password_hash": pw_hash}, f, indent=2)
    try:
        os.chmod(HUB_CONF, 0o600)
    except Exception:
        pass
    return pw_hash


PASSWORD_HASH = load_password_hash()


def verify_password(password):
    return hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH


def create_session():
    token = secrets.token_hex(32)
    with _sessions_lock:
        _sessions[token] = time.time() + SESSION_TIMEOUT
    return token


def validate_session(token):
    if not token:
        return False
    with _sessions_lock:
        expiry = _sessions.get(token)
        if expiry and time.time() < expiry:
            return True
        _sessions.pop(token, None)
    return False


def destroy_session(token):
    with _sessions_lock:
        _sessions.pop(token, None)


def change_password(new_password):
    global PASSWORD_HASH
    PASSWORD_HASH = hashlib.sha256(new_password.encode()).hexdigest()
    try:
        conf = {}
        if os.path.exists(HUB_CONF):
            with open(HUB_CONF) as f:
                conf = json.load(f)
        conf["password_hash"] = PASSWORD_HASH
        with open(HUB_CONF, "w") as f:
            json.dump(conf, f, indent=2)
        os.chmod(HUB_CONF, 0o600)
    except Exception:
        pass
    # Invalidate all existing sessions
    with _sessions_lock:
        _sessions.clear()


def cleanup_sessions():
    """Background thread: remove expired sessions every hour."""
    while True:
        time.sleep(3600)
        now = time.time()
        with _sessions_lock:
            expired = [t for t, exp in _sessions.items() if now >= exp]
            for t in expired:
                del _sessions[t]

# ---- Service registry (modules with web UIs) --------------------------------
# Format: id -> {name, desc, port, category, icon, docker_image, ha}
# Ports sourced from the clovernas catalog + cloverstack-ctl module list

CLOVERSTACK_MODULES = {
    "netmon":         {"name": "NetMon",          "desc": "Network monitoring (Zabbix)",
                       "port": 8081, "category": "CloverStack Core", "icon": "satellite"},
    "sentrylog":      {"name": "SentryLog",       "desc": "Log management (Graylog + Wazuh)",
                       "port": 9000, "category": "CloverStack Core", "icon": "scroll"},
    "myclover-vault": {"name": "MyClover Vault",  "desc": "Password manager (Vaultwarden)",
                       "port": 8843, "category": "CloverStack Core", "icon": "lock"},
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
                       "port": 8843, "category": "Productivity", "icon": "lock",
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


# ---- UFW Firewall helpers ---------------------------------------------------

_ufw_cache = {"ts": 0, "rules": set(), "active": False}
_ufw_cache_lock = threading.Lock()
UFW_CACHE_TTL = 5  # seconds


def get_ufw_status():
    """Get UFW status and set of allowed ports.  Cached for UFW_CACHE_TTL seconds."""
    with _ufw_cache_lock:
        if time.time() - _ufw_cache["ts"] < UFW_CACHE_TTL:
            return _ufw_cache["active"], set(_ufw_cache["rules"])

    rc, out, _ = run_cmd("ufw status numbered", timeout=10)
    active = "Status: active" in out
    allowed_ports = set()
    if active:
        # Parse lines like:  [ 1] 8081/tcp  ALLOW IN  Anywhere
        for line in out.splitlines():
            m = re.search(r"(\d+)(?:/tcp| )\s+ALLOW", line)
            if m:
                allowed_ports.add(int(m.group(1)))
            # Also match ranges or bare port numbers
            m2 = re.search(r"(\d+):(\d+)(?:/tcp)?\s+ALLOW", line)
            if m2:
                for p in range(int(m2.group(1)), int(m2.group(2)) + 1):
                    allowed_ports.add(p)

    with _ufw_cache_lock:
        _ufw_cache["ts"] = time.time()
        _ufw_cache["rules"] = allowed_ports
        _ufw_cache["active"] = active

    return active, allowed_ports


def ufw_allow_port(port):
    """Open a port in UFW.  Returns (success, message)."""
    port = int(port)
    if port < 1 or port > 65535:
        return False, "Invalid port number"
    rc, out, err = run_cmd(f"ufw allow {port}/tcp", timeout=15)
    _invalidate_ufw_cache()
    return rc == 0, (out or err).strip()


def ufw_deny_port(port):
    """Close (delete allow rule for) a port in UFW.  Returns (success, message)."""
    port = int(port)
    if port < 1 or port > 65535:
        return False, "Invalid port number"
    # delete the allow rule; use --force to skip interactive prompt
    rc, out, err = run_cmd(f"ufw delete allow {port}/tcp", timeout=15)
    # Also try without /tcp in case it was added bare
    if rc != 0:
        rc, out, err = run_cmd(f"ufw delete allow {port}", timeout=15)
    _invalidate_ufw_cache()
    return rc == 0, (out or err).strip()


def _invalidate_ufw_cache():
    with _ufw_cache_lock:
        _ufw_cache["ts"] = 0


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
    """API request handler with session-based authentication."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def get_session_token(self):
        """Extract session token from cookie."""
        cookie_header = self.headers.get("Cookie", "")
        cookies = http.cookies.SimpleCookie()
        try:
            cookies.load(cookie_header)
        except Exception:
            return None
        morsel = cookies.get("hub_session")
        return morsel.value if morsel else None

    def is_authenticated(self):
        """Check if the request has a valid session."""
        return validate_session(self.get_session_token())

    def send_login_redirect(self):
        """Redirect unauthenticated requests to login page."""
        self.send_response(302)
        self.send_header("Location", "/login")
        self.end_headers()

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

        # Login page is always accessible
        if path == "/login":
            self.serve_login_page()
            return

        # Everything else requires authentication
        if not self.is_authenticated():
            if path.startswith("/api/"):
                self.send_json({"error": "Authentication required"}, 401)
            else:
                self.send_login_redirect()
            return

        if path == "/api/status":
            self.handle_status()
        elif path == "/api/ip":
            self.send_json({"ip": get_host_ip()})
        elif path == "/api/services":
            self.handle_services()
        elif path == "/api/desktops":
            self.handle_desktops()
        elif path == "/api/firewall/status":
            self.handle_firewall_status()
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

        # Login endpoint is always accessible
        if path == "/api/login":
            self.handle_login(data)
            return

        # Everything else requires authentication
        if not self.is_authenticated():
            self.send_json({"error": "Authentication required"}, 401)
            return

        if path == "/api/logout":
            self.handle_logout()
        elif path == "/api/change-password":
            self.handle_change_password(data)
        elif path == "/api/module/enable":
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
        elif path == "/api/firewall/allow":
            self.handle_firewall_allow(data)
        elif path == "/api/firewall/deny":
            self.handle_firewall_deny(data)
        else:
            self.send_json({"error": "Not found"}, 404)

    # ---- Auth Handlers ------------------------------------------------------

    def handle_login(self, data):
        password = data.get("password", "")
        if verify_password(password):
            token = create_session()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            cookie = http.cookies.SimpleCookie()
            cookie["hub_session"] = token
            cookie["hub_session"]["path"] = "/"
            cookie["hub_session"]["httponly"] = True
            cookie["hub_session"]["max-age"] = str(SESSION_TIMEOUT)
            cookie["hub_session"]["samesite"] = "Strict"
            self.send_header("Set-Cookie", cookie["hub_session"].OutputString())
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        else:
            time.sleep(1)  # Rate-limit brute force
            self.send_json({"success": False, "error": "Invalid password"}, 401)

    def handle_logout(self):
        token = self.get_session_token()
        if token:
            destroy_session(token)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        cookie = http.cookies.SimpleCookie()
        cookie["hub_session"] = ""
        cookie["hub_session"]["path"] = "/"
        cookie["hub_session"]["max-age"] = "0"
        self.send_header("Set-Cookie", cookie["hub_session"].OutputString())
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode())

    def handle_change_password(self, data):
        current = data.get("current_password", "")
        new_pw = data.get("new_password", "")
        if not verify_password(current):
            self.send_json({"success": False, "error": "Current password is incorrect"}, 403)
            return
        if len(new_pw) < 6:
            self.send_json({"success": False, "error": "Password must be at least 6 characters"}, 400)
            return
        change_password(new_pw)
        # Create a new session for the user
        token = create_session()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        cookie = http.cookies.SimpleCookie()
        cookie["hub_session"] = token
        cookie["hub_session"]["path"] = "/"
        cookie["hub_session"]["httponly"] = True
        cookie["hub_session"]["max-age"] = str(SESSION_TIMEOUT)
        cookie["hub_session"]["samesite"] = "Strict"
        self.send_header("Set-Cookie", cookie["hub_session"].OutputString())
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode())

    def serve_login_page(self):
        """Serve the login page."""
        login_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login.html")
        if os.path.exists(login_path):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(login_path, "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode("utf-8"))
        else:
            # Inline fallback login page
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"""<!DOCTYPE html><html><head><title>CloverOS Login</title></head>
            <body style="background:#0a0a0f;color:#e0e0e8;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh">
            <form onsubmit="event.preventDefault();fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({password:document.getElementById('pw').value})}).then(r=>r.json()).then(d=>{if(d.success)location.href='/';
            else document.getElementById('err').textContent=d.error||'Login failed'})">
            <h2>CloverOS Service Hub</h2><br>
            <input id="pw" type="password" placeholder="Admin password" autofocus style="padding:10px;width:250px;border-radius:8px;border:1px solid #333;background:#111;color:#e0e0e8"><br><br>
            <button type="submit" style="padding:10px 24px;border-radius:8px;border:none;background:#22c55e;color:#fff;cursor:pointer">Sign In</button>
            <p id="err" style="color:#ef4444;margin-top:12px"></p></form></body></html>""")

    # ---- Handlers -----------------------------------------------------------

    def handle_status(self):
        """Full system status."""
        ip = get_host_ip()

        # UFW firewall state
        ufw_active, ufw_allowed = get_ufw_status()

        # Modules
        modules = {}
        for mod_id, info in CLOVERSTACK_MODULES.items():
            status = get_module_status(mod_id)
            port_open = check_port(info["port"])
            ufw_open = info["port"] in ufw_allowed
            # Also check extra_ports
            extra_ufw = {}
            for label, p in info.get("extra_ports", {}).items():
                extra_ufw[str(p)] = p in ufw_allowed
            modules[mod_id] = {
                **info,
                **status,
                "port_open": port_open,
                "ufw_open": ufw_open,
                "extra_ufw": extra_ufw,
            }

        # Deploy apps
        apps = {}
        for app_id, info in DEPLOY_CATALOG.items():
            status = get_deploy_app_status(app_id)
            port_open = check_port(info["port"])
            ufw_open = info["port"] in ufw_allowed
            apps[app_id] = {
                **info,
                **status,
                "port_open": port_open,
                "ufw_open": ufw_open,
            }

        # Desktops
        desktops = get_desktop_status()

        self.send_json({
            "ip": ip,
            "ufw_active": ufw_active,
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

    # ---- Firewall Handlers --------------------------------------------------

    def handle_firewall_status(self):
        """Return UFW active state and per-port allow status for all services."""
        active, allowed = get_ufw_status()
        ports = {}
        for mod_id, info in CLOVERSTACK_MODULES.items():
            ports[str(info["port"])] = info["port"] in allowed
            for label, p in info.get("extra_ports", {}).items():
                ports[str(p)] = p in allowed
        for app_id, info in DEPLOY_CATALOG.items():
            ports[str(info["port"])] = info["port"] in allowed
        self.send_json({"ufw_active": active, "ports": ports})

    def handle_firewall_allow(self, data):
        """Open a port through UFW."""
        port = data.get("port")
        if not port:
            self.send_json({"error": "Missing 'port' parameter"}, 400)
            return
        try:
            port = int(port)
        except (ValueError, TypeError):
            self.send_json({"error": "Invalid port number"}, 400)
            return
        ok, msg = ufw_allow_port(port)
        self.send_json({"success": ok, "port": port, "message": msg})

    def handle_firewall_deny(self, data):
        """Close a port through UFW (remove allow rule)."""
        port = data.get("port")
        if not port:
            self.send_json({"error": "Missing 'port' parameter"}, 400)
            return
        try:
            port = int(port)
        except (ValueError, TypeError):
            self.send_json({"error": "Invalid port number"}, 400)
            return
        ok, msg = ufw_deny_port(port)
        self.send_json({"success": ok, "port": port, "message": msg})

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
    # Start session cleanup background thread
    cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
    cleanup_thread.start()

    server = ThreadedHTTPServer(("0.0.0.0", PORT), HubAPIHandler)
    print(f"[clover-hub] Service Hub API running on port {PORT}")
    print(f"[clover-hub] Dashboard: http://{get_host_ip()}:{PORT}/")
    print(f"[clover-hub] Default password: cloverOS (change after first login)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[clover-hub] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
