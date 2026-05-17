#!/usr/bin/env python3
"""
CloverMarket Server
====================
On-device marketplace API + web UI.
Runs as a Docker container or standalone service.
Serves the marketplace UI, app registry, wizard renderer, and theme engine.
"""

import http.server
import json
import os
import subprocess
import sys
import socket
import html
import urllib.parse
import time
import hashlib
import threading

PORT = int(os.environ.get("CLOVERMARKET_PORT", 8090))
APPS_DIR = os.environ.get("CLOVERMARKET_APPS", "/opt/clovermarket/apps")
THEMES_DIR = os.environ.get("CLOVERMARKET_THEMES", "/opt/cloverstack/themes")
WALLET_FILE = os.environ.get("CLOVERMARKET_WALLET", "/var/lib/clovermarket/wallet.json")
REGISTRY_CACHE = os.environ.get("CLOVERMARKET_REGISTRY_CACHE", "/opt/clovermarket/cache/registry.json")
REMOTE_REGISTRY = os.environ.get("CLOVERMARKET_REGISTRY_URL", "https://market.myclover.tech/api/v1")
THEME_CSS_PATH = "/etc/myclover/themes/active.css"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default or {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_installed_apps():
    """Scan the apps directory for installed CloverApps."""
    apps = []
    if not os.path.isdir(APPS_DIR):
        return apps
    for entry in sorted(os.listdir(APPS_DIR)):
        manifest_path = os.path.join(APPS_DIR, entry, "cloverapp.yml")
        if os.path.isfile(manifest_path):
            try:
                import yaml
                with open(manifest_path) as f:
                    data = yaml.safe_load(f)
                app_info = data.get("app", {})
                marketplace = data.get("marketplace", {})
                pricing = data.get("pricing", {})
                app_info["_installed"] = True
                app_info["_dir"] = entry
                app_info["category"] = marketplace.get("category", "Uncategorized")
                app_info["pricing"] = pricing
                app_info["has_wizard"] = os.path.isfile(
                    os.path.join(APPS_DIR, entry, "wizard.yml")
                )
                # Check running status
                compose_path = os.path.join(APPS_DIR, entry, "docker-compose.yml")
                app_info["_running"] = False
                if os.path.isfile(compose_path):
                    try:
                        result = subprocess.run(
                            ["docker", "compose", "-f", compose_path, "ps", "--status", "running"],
                            capture_output=True, text=True, timeout=5
                        )
                        app_info["_running"] = "running" in result.stdout
                    except Exception:
                        pass
                apps.append(app_info)
            except Exception as e:
                print(f"[CloverMarket] Error parsing {manifest_path}: {e}", flush=True)
    return apps

def get_themes():
    """Scan the themes directory."""
    themes = []
    for subdir in ["builtin", "custom"]:
        theme_dir = os.path.join(THEMES_DIR, subdir)
        if not os.path.isdir(theme_dir):
            continue
        for fname in sorted(os.listdir(theme_dir)):
            if fname.endswith(".clover-theme"):
                theme_path = os.path.join(theme_dir, fname)
                try:
                    with open(theme_path) as f:
                        theme = json.load(f)
                    theme["_id"] = fname.replace(".clover-theme", "")
                    theme["_type"] = subdir
                    themes.append(theme)
                except Exception:
                    pass
    return themes

def get_active_theme():
    try:
        with open("/etc/myclover/themes/active") as f:
            return f.read().strip()
    except Exception:
        return "clover-classic"

def get_wallet():
    return load_json(WALLET_FILE, {"balance": 0, "transactions": []})


# ─── Wizard Renderer ─────────────────────────────────────────────────────────

def render_wizard_html(app_id):
    """Generate HTML for a CloverApp startup wizard."""
    wizard_path = os.path.join(APPS_DIR, app_id, "wizard.yml")
    if not os.path.isfile(wizard_path):
        return None

    try:
        import yaml
        with open(wizard_path) as f:
            wizard = yaml.safe_load(f)
    except Exception:
        return None

    steps = wizard.get("steps", [])
    app_name = wizard.get("app_name", app_id)

    # Build step HTML
    steps_html = []
    for i, step in enumerate(steps):
        fields_html = []
        for field in step.get("fields", []):
            fid = field.get("id", "")
            label = field.get("label", fid)
            ftype = field.get("type", "text")
            default = field.get("default", "")
            options = field.get("options", [])
            required = "required" if field.get("required") else ""

            if ftype == "select":
                opts_html = "".join(
                    f'<option value="{o.get("value", o) if isinstance(o, dict) else o}"'
                    f'{" selected" if (o.get("value", o) if isinstance(o, dict) else o) == default else ""}>'
                    f'{o.get("label", o) if isinstance(o, dict) else o}</option>'
                    for o in options
                )
                fields_html.append(f'''
                    <div class="field">
                        <label>{html.escape(label)}</label>
                        <select name="{html.escape(fid)}" {required}>{opts_html}</select>
                    </div>
                ''')
            elif ftype in ("checkbox", "checklist"):
                items = field.get("items", options)
                checks = "".join(
                    f'<label class="checkbox-item"><input type="checkbox" name="{html.escape(fid)}" '
                    f'value="{item.get("value", item) if isinstance(item, dict) else item}"> '
                    f'{item.get("label", item) if isinstance(item, dict) else item}</label>'
                    for item in items
                )
                fields_html.append(f'''
                    <div class="field">
                        <label>{html.escape(label)}</label>
                        <div class="checkbox-group">{checks}</div>
                    </div>
                ''')
            elif ftype == "color":
                fields_html.append(f'''
                    <div class="field">
                        <label>{html.escape(label)}</label>
                        <input type="color" name="{html.escape(fid)}" value="{html.escape(str(default))}" {required}>
                    </div>
                ''')
            elif ftype == "number":
                fields_html.append(f'''
                    <div class="field">
                        <label>{html.escape(label)}</label>
                        <input type="number" name="{html.escape(fid)}" value="{html.escape(str(default))}"
                               min="{field.get("min", "")}" max="{field.get("max", "")}" {required}>
                    </div>
                ''')
            elif ftype == "layout_picker":
                # Special widget: layout preset picker with preview cards
                layouts = field.get("layouts", options)
                cards = "".join(
                    f'<div class="layout-card" data-value="{l.get("value", l) if isinstance(l, dict) else l}" '
                    f'onclick="selectLayout(this, \'{html.escape(fid)}\')">'
                    f'<div class="layout-preview">{l.get("preview", "📐") if isinstance(l, dict) else "📐"}</div>'
                    f'<div class="layout-name">{l.get("label", l) if isinstance(l, dict) else l}</div>'
                    f'</div>'
                    for l in layouts
                )
                fields_html.append(f'''
                    <div class="field">
                        <label>{html.escape(label)}</label>
                        <input type="hidden" name="{html.escape(fid)}" value="{html.escape(str(default))}">
                        <div class="layout-grid">{cards}</div>
                    </div>
                ''')
            elif ftype == "theme_picker":
                fields_html.append(f'''
                    <div class="field">
                        <label>{html.escape(label)}</label>
                        <select name="{html.escape(fid)}">
                            <option value="clover-classic">🍀 Clover Classic</option>
                            <option value="midnight">🌙 Midnight</option>
                            <option value="nordic">❄️ Nordic</option>
                            <option value="neon">⚡ Neon</option>
                            <option value="corporate">🏢 Corporate</option>
                        </select>
                    </div>
                ''')
            else:
                fields_html.append(f'''
                    <div class="field">
                        <label>{html.escape(label)}</label>
                        <input type="text" name="{html.escape(fid)}" value="{html.escape(str(default))}"
                               placeholder="{html.escape(field.get('placeholder', ''))}" {required}>
                    </div>
                ''')

        steps_html.append({
            "title": step.get("title", f"Step {i+1}"),
            "description": step.get("description", ""),
            "icon": step.get("icon", "📋"),
            "fields": "\n".join(fields_html),
        })

    # Generate full HTML
    return _wizard_page(app_id, app_name, steps_html)


def _wizard_page(app_id, app_name, steps):
    """Build the full wizard HTML page."""
    step_indicators = "".join(
        f'<div class="step-indicator" id="ind-{i}">'
        f'<span class="step-num">{i+1}</span>'
        f'<span class="step-label">{s["title"]}</span></div>'
        for i, s in enumerate(steps)
    )

    step_panels = "".join(
        f'''<div class="step-panel" id="step-{i}" style="display:{"block" if i == 0 else "none"}">
            <h2>{s["icon"]} {html.escape(s["title"])}</h2>
            <p class="step-desc">{html.escape(s["description"])}</p>
            {s["fields"]}
        </div>'''
        for i, s in enumerate(steps)
    )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Setup — {html.escape(app_name)}</title>
<link rel="stylesheet" href="/theme.css">
<style>
  :root {{
    --clover: #22c55e;
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #242736;
    --border: #2e3142;
    --text: #e2e4eb;
    --text-muted: #8b8fa3;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg); color: var(--text);
    display: flex; justify-content: center; padding: 2rem 1rem;
  }}
  .wizard {{ max-width: 640px; width: 100%; }}
  .wizard-header {{ text-align: center; margin-bottom: 2rem; }}
  .wizard-header h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  .wizard-header p {{ color: var(--text-muted); font-size: 0.9rem; }}
  .steps-bar {{ display: flex; gap: 0.5rem; margin-bottom: 2rem; }}
  .step-indicator {{
    flex: 1; display: flex; align-items: center; gap: 0.5rem;
    padding: 0.5rem 0.75rem; background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; font-size: 0.8rem; color: var(--text-muted);
  }}
  .step-indicator.active {{ border-color: var(--clover); color: var(--clover); }}
  .step-indicator.done {{ border-color: var(--clover); background: rgba(34,197,94,0.1); }}
  .step-num {{
    width: 24px; height: 24px; border-radius: 50%; background: var(--surface2);
    display: flex; align-items: center; justify-content: center; font-weight: 600;
  }}
  .step-indicator.active .step-num {{ background: var(--clover); color: #000; }}
  .step-panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }}
  .step-panel h2 {{ font-size: 1.15rem; margin-bottom: 0.5rem; }}
  .step-desc {{ color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1.25rem; }}
  .field {{ margin-bottom: 1rem; }}
  .field label {{ display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.35rem; }}
  .field input, .field select {{
    width: 100%; padding: 0.6rem 0.8rem; background: var(--surface2);
    border: 1px solid var(--border); border-radius: 8px; color: var(--text);
    font-size: 0.95rem; outline: none;
  }}
  .field input:focus, .field select:focus {{ border-color: var(--clover); }}
  .checkbox-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }}
  .checkbox-item {{
    display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem;
    background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; cursor: pointer;
  }}
  .checkbox-item:hover {{ border-color: var(--clover); }}
  .layout-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }}
  .layout-card {{
    padding: 1rem; background: var(--surface2); border: 2px solid var(--border);
    border-radius: 10px; text-align: center; cursor: pointer; transition: all 0.2s;
  }}
  .layout-card:hover, .layout-card.selected {{ border-color: var(--clover); }}
  .layout-preview {{ font-size: 2rem; margin-bottom: 0.5rem; }}
  .layout-name {{ font-size: 0.8rem; color: var(--text-muted); }}
  .nav-buttons {{ display: flex; gap: 1rem; margin-top: 1.5rem; }}
  .btn {{
    flex: 1; padding: 0.75rem; border: none; border-radius: 10px;
    font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.2s;
  }}
  .btn-back {{ background: var(--surface2); color: var(--text); border: 1px solid var(--border); }}
  .btn-next {{ background: var(--clover); color: #000; }}
  .btn:hover {{ opacity: 0.9; }}
</style>
</head>
<body>
<div class="wizard">
  <div class="wizard-header">
    <h1>🧙 Setup {html.escape(app_name)}</h1>
    <p>Configure your app in a few quick steps</p>
  </div>
  <div class="steps-bar">{step_indicators}</div>
  <form id="wizard-form" action="/api/wizard/{html.escape(app_id)}/submit" method="POST">
    {step_panels}
    <div class="nav-buttons">
      <button type="button" class="btn btn-back" id="btn-back" onclick="prevStep()" style="display:none">← Back</button>
      <button type="button" class="btn btn-next" id="btn-next" onclick="nextStep()">Next →</button>
    </div>
  </form>
</div>
<script>
let currentStep = 0;
const totalSteps = {len(steps)};

function updateNav() {{
  document.getElementById("btn-back").style.display = currentStep > 0 ? "" : "none";
  document.getElementById("btn-next").textContent = currentStep === totalSteps - 1 ? "Complete ✓" : "Next →";
  for (let i = 0; i < totalSteps; i++) {{
    const ind = document.getElementById("ind-" + i);
    const panel = document.getElementById("step-" + i);
    ind.className = "step-indicator" + (i === currentStep ? " active" : (i < currentStep ? " done" : ""));
    panel.style.display = i === currentStep ? "block" : "none";
  }}
}}

function nextStep() {{
  if (currentStep < totalSteps - 1) {{ currentStep++; updateNav(); }}
  else {{ document.getElementById("wizard-form").submit(); }}
}}

function prevStep() {{
  if (currentStep > 0) {{ currentStep--; updateNav(); }}
}}

function selectLayout(el, fieldId) {{
  el.parentElement.querySelectorAll(".layout-card").forEach(c => c.classList.remove("selected"));
  el.classList.add("selected");
  el.parentElement.parentElement.querySelector('input[name="' + fieldId + '"]').value = el.dataset.value;
}}

updateNav();
</script>
</body>
</html>'''


# ─── Web UI Page ──────────────────────────────────────────────────────────────

def marketplace_page():
    """Main marketplace web UI."""
    apps = get_installed_apps()
    themes = get_themes()
    wallet = get_wallet()
    active_theme = get_active_theme()

    apps_html = ""
    for app in apps:
        name = app.get("name", app.get("_dir", "?"))
        version = app.get("version", "?")
        desc = app.get("description", "")[:80]
        status_dot = "🟢" if app.get("_running") else "🔴"
        pricing = app.get("pricing", {}).get("model", "free")
        wizard_btn = (
            f'<a href="/wizard/{app["_dir"]}" class="wiz-btn">🧙 Setup</a>'
            if app.get("has_wizard") else ""
        )
        apps_html += f'''
        <div class="app-row">
            <div class="app-info">
                <span class="status-dot">{status_dot}</span>
                <div>
                    <div class="app-name">{html.escape(name)} <span class="app-ver">v{html.escape(version)}</span></div>
                    <div class="app-desc">{html.escape(desc)}</div>
                </div>
            </div>
            <div class="app-actions">
                <span class="pricing-badge">{html.escape(pricing)}</span>
                {wizard_btn}
            </div>
        </div>
        '''

    themes_html = ""
    for theme in themes:
        tid = theme.get("_id", "")
        tname = theme.get("name", tid)
        is_active = "active" if tid == active_theme else ""
        themes_html += f'''
        <div class="theme-item {is_active}">
            <span>{html.escape(tname)}</span>
            <span class="theme-type">{theme.get("_type", "")}</span>
        </div>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍀 CloverMarket</title>
<style>
  :root {{
    --clover: #22c55e; --bg: #0f1117; --surface: #1a1d27;
    --surface2: #242736; --border: #2e3142; --text: #e2e4eb;
    --text-muted: #8b8fa3; --gold: #f59e0b;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg); color: var(--text); padding: 1.5rem;
  }}
  .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem; }}
  .header h1 {{ font-size: 1.5rem; }}
  .header h1 span {{ color: var(--clover); }}
  .wallet {{ background: var(--surface); padding: 0.5rem 1rem; border-radius: 8px;
             border: 1px solid var(--border); font-size: 0.9rem; }}
  .wallet .bal {{ color: var(--gold); font-weight: 700; }}
  .section {{ margin-bottom: 2rem; }}
  .section h2 {{ font-size: 1.1rem; margin-bottom: 1rem; }}
  .app-row {{
    display: flex; justify-content: space-between; align-items: center;
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 1rem; margin-bottom: 0.75rem; transition: border-color 0.2s;
  }}
  .app-row:hover {{ border-color: var(--clover); }}
  .app-info {{ display: flex; align-items: center; gap: 0.75rem; }}
  .app-name {{ font-weight: 600; }}
  .app-ver {{ color: var(--text-muted); font-size: 0.8rem; }}
  .app-desc {{ color: var(--text-muted); font-size: 0.85rem; }}
  .app-actions {{ display: flex; align-items: center; gap: 0.75rem; }}
  .pricing-badge {{
    font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 100px;
    background: rgba(34,197,94,0.1); color: var(--clover); text-transform: uppercase;
  }}
  .wiz-btn {{
    padding: 0.4rem 0.8rem; background: var(--clover); color: #000;
    border-radius: 8px; text-decoration: none; font-size: 0.85rem; font-weight: 600;
  }}
  .theme-item {{
    display: flex; justify-content: space-between; padding: 0.75rem 1rem;
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    margin-bottom: 0.5rem;
  }}
  .theme-item.active {{ border-color: var(--clover); background: rgba(34,197,94,0.05); }}
  .theme-type {{ color: var(--text-muted); font-size: 0.8rem; }}
  .empty {{ color: var(--text-muted); text-align: center; padding: 2rem; font-size: 0.9rem; }}
</style>
</head>
<body>
  <div class="header">
    <h1>🍀 Clover<span>Market</span></h1>
    <div class="wallet">💰 <span class="bal">{wallet.get("balance", 0):,} CC</span></div>
  </div>

  <div class="section">
    <h2>📦 Installed Apps</h2>
    {apps_html if apps_html else '<div class="empty">No apps installed. Use clovermarket-ctl install &lt;app-id&gt;</div>'}
  </div>

  <div class="section">
    <h2>🎨 Themes</h2>
    {themes_html if themes_html else '<div class="empty">No themes installed</div>'}
  </div>

  <div style="text-align:center; color:var(--text-muted); font-size:0.78rem; margin-top:2rem;">
    CloverMarket v0.1.0 · <a href="/api/registry" style="color:var(--clover);">API</a>
  </div>
</body>
</html>'''


# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class MarketHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[CloverMarket] {args[0]}", flush=True)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/" or path == "/index.html":
            self._send_html(marketplace_page())

        elif path == "/health":
            self._send_json({"status": "ok", "version": "0.1.0"})

        elif path == "/theme.css":
            self._send_css()

        elif path.startswith("/wizard/"):
            app_id = path.split("/wizard/")[1].strip("/")
            wizard_html = render_wizard_html(app_id)
            if wizard_html:
                self._send_html(wizard_html)
            else:
                self.send_error(404, f"No wizard for {app_id}")

        elif path == "/api/apps":
            apps = get_installed_apps()
            self._send_json({"apps": apps})

        elif path == "/api/themes":
            themes = get_themes()
            self._send_json({"themes": themes, "active": get_active_theme()})

        elif path == "/api/wallet":
            self._send_json(get_wallet())

        elif path == "/api/registry":
            registry = load_json(REGISTRY_CACHE, {"apps": []})
            self._send_json(registry)

        else:
            self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b""

        if path.startswith("/api/wizard/") and path.endswith("/submit"):
            app_id = path.split("/api/wizard/")[1].replace("/submit", "")
            try:
                # Parse form data or JSON
                content_type = self.headers.get("Content-Type", "")
                if "json" in content_type:
                    config = json.loads(body)
                else:
                    config = dict(urllib.parse.parse_qsl(body.decode()))
                # Save wizard config
                config_path = os.path.join(APPS_DIR, app_id, "wizard-config.json")
                save_json(config_path, config)
                # Redirect back to marketplace
                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})

        elif path == "/api/theme/apply":
            try:
                data = json.loads(body)
                theme_id = data.get("theme_id", "")
                # Apply theme via clovermarket-ctl
                result = subprocess.run(
                    ["clovermarket-ctl", "theme", "apply", theme_id],
                    capture_output=True, text=True, timeout=10
                )
                self._send_json({
                    "success": result.returncode == 0,
                    "output": result.stdout
                })
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})

        else:
            self.send_error(404)

    def _send_html(self, content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode())

    def _send_json(self, data):
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _send_css(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/css")
        self.end_headers()
        try:
            with open(THEME_CSS_PATH) as f:
                self.wfile.write(f.read().encode())
        except FileNotFoundError:
            # Default theme CSS
            self.wfile.write(b":root { --clover-brand: #22c55e; }")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ip = get_ip()
    print(f"", flush=True)
    print(f"  ╔═══════════════════════════════════════════╗", flush=True)
    print(f"  ║     🍀 CloverMarket Server v0.1.0         ║", flush=True)
    print(f"  ║                                           ║", flush=True)
    print(f"  ║  → http://{ip}:{PORT:<23s}   ║", flush=True)
    print(f"  ║                                           ║", flush=True)
    print(f"  ╚═══════════════════════════════════════════╝", flush=True)

    server = http.server.HTTPServer(("0.0.0.0", PORT), MarketHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    print("[CloverMarket] Server stopped.", flush=True)


if __name__ == "__main__":
    main()
