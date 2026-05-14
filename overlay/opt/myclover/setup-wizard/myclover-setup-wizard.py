#!/usr/bin/env python3
"""
mycloverOS First-Boot Setup Wizard
===================================
Lightweight web-based setup wizard that runs on first boot.
Accessible at http://<device-ip>:8080
Auto-disables after setup is complete.
"""

import http.server
import json
import os
import subprocess
import sys
import socket
import html
import urllib.parse
import crypt
import time

PORT = 8080
SETUP_DONE_FLAG = "/etc/myclover/.setup-complete"
CLOVERSTACK_ROOT = "/opt/cloverstack"
CLOVERSTACK_CONFIG = "/etc/myclover"

# ─── HTML Templates ───────────────────────────────────────────────────────────

def get_current_ip():
    """Get the current IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"

def get_current_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "cloverstack"

def get_network_interfaces():
    """Get list of network interfaces and their IPs."""
    interfaces = []
    try:
        result = subprocess.run(["ip", "-j", "addr", "show"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for iface in data:
                name = iface.get("ifname", "")
                if name == "lo":
                    continue
                addrs = []
                for addr_info in iface.get("addr_info", []):
                    if addr_info.get("family") == "inet":
                        addrs.append(addr_info.get("local", ""))
                interfaces.append({"name": name, "ips": addrs, "state": iface.get("operstate", "UNKNOWN")})
    except Exception:
        pass
    return interfaces

def get_service_status(service):
    """Check if a systemd service is active."""
    try:
        result = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except Exception:
        return "unknown"

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>mycloverOS Setup</title>
<style>
  :root {
    --clover: #22c55e;
    --clover-dark: #16a34a;
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #242736;
    --border: #2e3142;
    --text: #e2e4eb;
    --text-muted: #8b8fa3;
    --danger: #ef4444;
    --warning: #f59e0b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 2rem 1rem;
  }
  .container {
    max-width: 640px;
    width: 100%;
  }
  .logo {
    text-align: center;
    margin-bottom: 2rem;
  }
  .logo h1 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--clover), #4ade80);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
  }
  .logo p {
    color: var(--text-muted);
    font-size: 0.9rem;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
  }
  .card h2 {
    font-size: 1.1rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .card h2 .icon {
    font-size: 1.3rem;
  }
  .field {
    margin-bottom: 1rem;
  }
  .field label {
    display: block;
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-bottom: 0.35rem;
    font-weight: 500;
  }
  .field input, .field select {
    width: 100%;
    padding: 0.6rem 0.8rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s;
  }
  .field input:focus, .field select:focus {
    border-color: var(--clover);
  }
  .field .hint {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
  }
  .checkbox-group {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }
  .checkbox-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    transition: border-color 0.2s;
  }
  .checkbox-item:hover {
    border-color: var(--clover);
  }
  .checkbox-item input[type="checkbox"] {
    accent-color: var(--clover);
    width: 16px;
    height: 16px;
  }
  .checkbox-item span {
    font-size: 0.88rem;
  }
  .status-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }
  .status-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    background: var(--surface2);
    border-radius: 8px;
    font-size: 0.85rem;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .status-dot.active { background: var(--clover); }
  .status-dot.inactive { background: var(--danger); }
  .status-dot.unknown { background: var(--warning); }
  .btn {
    width: 100%;
    padding: 0.8rem;
    background: linear-gradient(135deg, var(--clover), var(--clover-dark));
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .btn:hover { opacity: 0.9; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .alert {
    padding: 0.8rem 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.9rem;
  }
  .alert.success {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    color: #4ade80;
  }
  .alert.error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #f87171;
  }
  .ip-display {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 1.5rem;
    color: var(--clover);
    text-align: center;
    padding: 0.5rem;
  }
  .net-iface {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.7rem;
    background: var(--surface2);
    border-radius: 8px;
    margin-bottom: 0.5rem;
    font-size: 0.88rem;
  }
  .net-iface .name { font-weight: 600; }
  .net-iface .state {
    font-size: 0.78rem;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
  }
  .net-iface .state.UP { background: rgba(34,197,94,0.15); color: #4ade80; }
  .net-iface .state.DOWN { background: rgba(239,68,68,0.15); color: #f87171; }
  .net-iface .state.UNKNOWN { background: rgba(245,158,11,0.15); color: #fbbf24; }
  .progress-bar {
    width: 100%;
    height: 4px;
    background: var(--surface2);
    border-radius: 2px;
    overflow: hidden;
    margin-top: 1rem;
    display: none;
  }
  .progress-bar.active { display: block; }
  .progress-bar .fill {
    height: 100%;
    background: var(--clover);
    border-radius: 2px;
    width: 0%;
    transition: width 0.5s;
    animation: progress 2s ease-in-out infinite;
  }
  @keyframes progress {
    0% { width: 0%; }
    50% { width: 70%; }
    100% { width: 100%; }
  }
  .complete-screen {
    text-align: center;
    padding: 3rem 1rem;
  }
  .complete-screen .checkmark {
    font-size: 4rem;
    margin-bottom: 1rem;
  }
  .complete-screen h2 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
  }
  .complete-screen p {
    color: var(--text-muted);
    margin-bottom: 0.5rem;
  }
  .footer {
    text-align: center;
    color: var(--text-muted);
    font-size: 0.78rem;
    margin-top: 1rem;
  }
</style>
</head>
<body>
<div class="container">
  <div class="logo">
    <h1>&#x1f340; mycloverOS</h1>
    <p>First-Boot Setup Wizard</p>
  </div>

  <div id="alert-area"></div>

  <div id="setup-form">
    <!-- Network Status -->
    <div class="card">
      <h2><span class="icon">&#x1f310;</span> Network Status</h2>
      <div id="network-info">Loading...</div>
    </div>

    <!-- System Configuration -->
    <div class="card">
      <h2><span class="icon">&#x2699;&#xFE0F;</span> System Configuration</h2>
      <div class="field">
        <label>Hostname</label>
        <input type="text" id="hostname" value="HOSTNAME_PLACEHOLDER" placeholder="cloverstack">
        <div class="hint">Name for this machine on the network</div>
      </div>
      <div class="field">
        <label>Timezone</label>
        <select id="timezone">
          <option value="America/Los_Angeles">Pacific (America/Los_Angeles)</option>
          <option value="America/Denver">Mountain (America/Denver)</option>
          <option value="America/Chicago">Central (America/Chicago)</option>
          <option value="America/New_York">Eastern (America/New_York)</option>
          <option value="UTC" selected>UTC</option>
          <option value="Europe/London">Europe/London</option>
          <option value="Europe/Berlin">Europe/Berlin</option>
          <option value="Asia/Tokyo">Asia/Tokyo</option>
          <option value="Asia/Shanghai">Asia/Shanghai</option>
          <option value="Australia/Sydney">Australia/Sydney</option>
        </select>
      </div>
    </div>

    <!-- User Setup -->
    <div class="card">
      <h2><span class="icon">&#x1f464;</span> Admin User</h2>
      <div class="field">
        <label>Username</label>
        <input type="text" id="username" value="clover" placeholder="clover">
      </div>
      <div class="field">
        <label>Password</label>
        <input type="password" id="password" placeholder="Enter password">
      </div>
      <div class="field">
        <label>Confirm Password</label>
        <input type="password" id="password2" placeholder="Confirm password">
        <div class="hint">Set a strong password for SSH and console access</div>
      </div>
    </div>

    <!-- CloverStack Modules -->
    <div class="card">
      <h2><span class="icon">&#x1f4E6;</span> CloverStack Modules</h2>
      <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;">Select which modules to enable</p>
      <div class="checkbox-group">
        <label class="checkbox-item">
          <input type="checkbox" name="module" value="netmon" checked>
          <span>NetMon</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" name="module" value="sentrylog" checked>
          <span>SentryLog</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" name="module" value="myclover-vault" checked>
          <span>MyClover Vault</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" name="module" value="chappie" checked>
          <span>Chappie AI</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" name="module" value="wireguard">
          <span>WireGuard VPN</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" name="module" value="traefik">
          <span>Traefik Proxy</span>
        </label>
        <label class="checkbox-item">
          <input type="checkbox" name="module" value="clovermarket" checked>
          <span>🍀 CloverMarket</span>
        </label>
      </div>
    </div>

    <!-- Services Status -->
    <div class="card">
      <h2><span class="icon">&#x1f6e0;&#xFE0F;</span> Service Status</h2>
      <div id="services-info" class="status-grid">Loading...</div>
    </div>

    <button class="btn" id="apply-btn" onclick="applySetup()">
      Apply Configuration &amp; Complete Setup
    </button>
    <div class="progress-bar" id="progress">
      <div class="fill"></div>
    </div>
  </div>

  <div id="complete-screen" class="card complete-screen" style="display:none;">
    <div class="checkmark">&#x2705;</div>
    <h2>Setup Complete!</h2>
    <p>mycloverOS is configured and ready.</p>
    <p id="ssh-info" style="font-family: monospace; color: var(--clover); margin-top: 1rem;"></p>
    <p style="color: var(--text-muted); margin-top: 1rem; font-size: 0.85rem;">
      This wizard will shut down automatically.<br>
      You can access your system via SSH or console.
    </p>
  </div>

  <div class="footer">
    mycloverOS v0.1.0 &middot; CloverStack Platform
  </div>
</div>

<script>
async function loadStatus() {
  try {
    const r = await fetch('/api/status');
    const data = await r.json();

    // Network
    let netHtml = '';
    if (data.ip) {
      netHtml += '<div class="ip-display">' + data.ip + '</div>';
    }
    if (data.interfaces) {
      data.interfaces.forEach(iface => {
        const ips = iface.ips.length > 0 ? iface.ips.join(', ') : 'no IP';
        netHtml += '<div class="net-iface">' +
          '<span class="name">' + iface.name + '</span>' +
          '<span>' + ips + '</span>' +
          '<span class="state ' + iface.state + '">' + iface.state + '</span>' +
          '</div>';
      });
    }
    document.getElementById('network-info').innerHTML = netHtml || 'No network detected';

    // Services
    let svcHtml = '';
    if (data.services) {
      Object.entries(data.services).forEach(([name, status]) => {
        const cls = status === 'active' ? 'active' : (status === 'inactive' ? 'inactive' : 'unknown');
        svcHtml += '<div class="status-item">' +
          '<span class="status-dot ' + cls + '"></span>' +
          '<span>' + name + ': ' + status + '</span></div>';
      });
    }
    document.getElementById('services-info').innerHTML = svcHtml || 'No services detected';
  } catch(e) {
    console.error('Status fetch failed:', e);
  }
}

async function applySetup() {
  const hostname = document.getElementById('hostname').value.trim();
  const timezone = document.getElementById('timezone').value;
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const password2 = document.getElementById('password2').value;

  // Validation
  if (!hostname) return showAlert('Please enter a hostname', 'error');
  if (!username) return showAlert('Please enter a username', 'error');
  if (!password) return showAlert('Please enter a password', 'error');
  if (password !== password2) return showAlert('Passwords do not match', 'error');
  if (password.length < 6) return showAlert('Password must be at least 6 characters', 'error');

  const modules = Array.from(document.querySelectorAll('input[name="module"]:checked')).map(cb => cb.value);

  const btn = document.getElementById('apply-btn');
  const progress = document.getElementById('progress');
  btn.disabled = true;
  btn.textContent = 'Applying configuration...';
  progress.classList.add('active');

  try {
    const r = await fetch('/api/setup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ hostname, timezone, username, password, modules })
    });
    const data = await r.json();
    if (data.success) {
      document.getElementById('setup-form').style.display = 'none';
      document.getElementById('complete-screen').style.display = 'block';
      document.getElementById('ssh-info').textContent = 'ssh ' + username + '@' + (data.ip || hostname);
    } else {
      showAlert('Setup failed: ' + (data.error || 'Unknown error'), 'error');
      btn.disabled = false;
      btn.textContent = 'Apply Configuration & Complete Setup';
      progress.classList.remove('active');
    }
  } catch(e) {
    showAlert('Connection error: ' + e.message, 'error');
    btn.disabled = false;
    btn.textContent = 'Apply Configuration & Complete Setup';
    progress.classList.remove('active');
  }
}

function showAlert(msg, type) {
  document.getElementById('alert-area').innerHTML =
    '<div class="alert ' + type + '">' + msg + '</div>';
  setTimeout(() => { document.getElementById('alert-area').innerHTML = ''; }, 5000);
}

loadStatus();
setInterval(loadStatus, 10000);
</script>
</body>
</html>"""


class SetupHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[mycloverOS Setup] {args[0]}", flush=True)

    def do_GET(self):
        if self.path == "/api/status":
            self._send_status()
        elif self.path == "/" or self.path == "/index.html":
            self._send_page()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/setup":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                result = apply_setup(data)
                self._send_json(result)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})
        else:
            self.send_error(404)

    def _send_page(self):
        hostname = get_current_hostname()
        page = PAGE_HTML.replace("HOSTNAME_PLACEHOLDER", html.escape(hostname))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(page.encode())

    def _send_status(self):
        ip = get_current_ip()
        interfaces = get_network_interfaces()
        services = {}
        for svc in ["docker", "ollama", "ssh", "ufw", "NetworkManager"]:
            services[svc] = get_service_status(svc)
        self._send_json({
            "ip": ip,
            "interfaces": interfaces,
            "services": services,
            "hostname": get_current_hostname()
        })

    def _send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


def apply_setup(data):
    """Apply the setup configuration to the system."""
    errors = []

    hostname = data.get("hostname", "cloverstack")
    timezone = data.get("timezone", "UTC")
    username = data.get("username", "clover")
    password = data.get("password", "")
    modules = data.get("modules", [])

    # 1. Set hostname
    try:
        subprocess.run(["hostnamectl", "set-hostname", hostname], check=True, timeout=10)
        with open("/etc/hosts", "r") as f:
            hosts = f.read()
        if hostname not in hosts:
            with open("/etc/hosts", "a") as f:
                f.write(f"127.0.1.1\t{hostname}\n")
        print(f"[Setup] Hostname set to: {hostname}", flush=True)
    except Exception as e:
        errors.append(f"Hostname: {e}")

    # 2. Set timezone
    try:
        subprocess.run(["timedatectl", "set-timezone", timezone], check=True, timeout=10)
        print(f"[Setup] Timezone set to: {timezone}", flush=True)
    except Exception as e:
        errors.append(f"Timezone: {e}")

    # 3. Create/update user
    try:
        # Check if user exists
        result = subprocess.run(["id", username], capture_output=True, timeout=5)
        if result.returncode != 0:
            # Create user
            subprocess.run([
                "useradd", "-m", "-s", "/bin/bash",
                "-G", "sudo,docker",
                username
            ], check=True, timeout=10)
            print(f"[Setup] User created: {username}", flush=True)

        # Set password
        proc = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, timeout=10)
        proc.communicate(f"{username}:{password}".encode())
        print(f"[Setup] Password set for: {username}", flush=True)
    except Exception as e:
        errors.append(f"User: {e}")

    # 4. Enable CloverStack modules
    try:
        os.makedirs(CLOVERSTACK_CONFIG, exist_ok=True)
        with open(f"{CLOVERSTACK_CONFIG}/modules.conf", "w") as f:
            f.write("# mycloverOS CloverStack Enabled Modules\n")
            f.write(f"ENABLED_MODULES=\"{' '.join(modules)}\"\n")
        print(f"[Setup] Modules enabled: {modules}", flush=True)
    except Exception as e:
        errors.append(f"Modules: {e}")

    # 5. Enable SSH
    try:
        subprocess.run(["systemctl", "enable", "--now", "ssh"], timeout=10, capture_output=True)
        print("[Setup] SSH enabled", flush=True)
    except Exception as e:
        errors.append(f"SSH: {e}")

    # 6. Mark setup as complete
    try:
        os.makedirs(os.path.dirname(SETUP_DONE_FLAG), exist_ok=True)
        with open(SETUP_DONE_FLAG, "w") as f:
            f.write(f"Setup completed at: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
            f.write(f"Hostname: {hostname}\n")
            f.write(f"User: {username}\n")
            f.write(f"Modules: {', '.join(modules)}\n")
        print("[Setup] Setup marked as complete", flush=True)
    except Exception as e:
        errors.append(f"Flag: {e}")

    # 7. Disable the setup wizard service
    try:
        subprocess.run(["systemctl", "disable", "myclover-setup-wizard"], timeout=10, capture_output=True)
        print("[Setup] Wizard service disabled for future boots", flush=True)
    except Exception as e:
        errors.append(f"Service disable: {e}")

    if errors:
        return {"success": False, "error": "; ".join(errors)}

    ip = get_current_ip()
    return {"success": True, "ip": ip, "message": "Setup complete!"}


def main():
    # Check if setup already done
    if os.path.exists(SETUP_DONE_FLAG):
        print("[mycloverOS] Setup already completed. Exiting wizard.", flush=True)
        sys.exit(0)

    ip = get_current_ip()
    print(f"", flush=True)
    print(f"  ╔══════════════════════════════════════════════╗", flush=True)
    print(f"  ║     🍀 mycloverOS Setup Wizard              ║", flush=True)
    print(f"  ║                                              ║", flush=True)
    print(f"  ║  Open a browser and navigate to:             ║", flush=True)
    print(f"  ║  → http://{ip}:{PORT:<25s}    ║", flush=True)
    print(f"  ║                                              ║", flush=True)
    print(f"  ╚══════════════════════════════════════════════╝", flush=True)
    print(f"", flush=True)

    server = http.server.HTTPServer(("0.0.0.0", PORT), SetupHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    print("[mycloverOS] Setup wizard stopped.", flush=True)


if __name__ == "__main__":
    main()
