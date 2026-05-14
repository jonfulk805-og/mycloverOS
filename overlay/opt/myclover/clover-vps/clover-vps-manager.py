#!/usr/bin/env python3
"""
CloverVPS Manager — White-label VPS reseller platform for mycloverOS.

Supports: Hetzner, DigitalOcean, Vultr, Linode/Akamai
Features: Full lifecycle (create, destroy, resize, snapshots, firewall, DNS)
Model:    Reseller — admin configures provider keys, end users see CloverCloud branding

Runs on port 8081. Pure Python 3 stdlib + urllib (no pip dependencies).
"""

import http.server
import json
import os
import sqlite3
import ssl
import subprocess
import socket
import time
import urllib.request
import urllib.parse
import urllib.error
import hashlib
import base64
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

PORT = 8081
DATA_DIR = "/etc/myclover/clover-vps"
DB_PATH = os.path.join(DATA_DIR, "clover-vps.db")
CONFIG_PATH = os.path.join(DATA_DIR, "providers.json")
SESSION_SECRET = None  # generated on first run

# ─── Provider Abstraction ────────────────────────────────────────────────────

class ProviderError(Exception):
    pass


def _api(method, url, headers=None, data=None, timeout=30):
    """Generic HTTP API call using urllib."""
    if headers is None:
        headers = {}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise ProviderError(f"HTTP {e.code}: {body[:500]}")
    except urllib.error.URLError as e:
        raise ProviderError(f"Connection error: {e.reason}")


# ── Hetzner Cloud ────────────────────────────────────────────────────────────

class HetznerProvider:
    name = "hetzner"
    display = "Hetzner Cloud"
    base = "https://api.hetzner.cloud/v1"

    def __init__(self, api_key):
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _get(self, path):
        return _api("GET", f"{self.base}{path}", self.headers)

    def _post(self, path, data):
        return _api("POST", f"{self.base}{path}", self.headers, data)

    def _delete(self, path):
        return _api("DELETE", f"{self.base}{path}", self.headers)

    def _put(self, path, data):
        return _api("PUT", f"{self.base}{path}", self.headers, data)

    def list_plans(self):
        r = self._get("/server_types")
        plans = []
        for st in r.get("server_types", []):
            plans.append({
                "id": str(st["id"]),
                "name": st["name"],
                "description": st["description"],
                "vcpus": st["cores"],
                "ram_mb": st["memory"] * 1024,
                "disk_gb": st["disk"],
                "price_monthly": float(st["prices"][0]["price_monthly"]["gross"]) if st.get("prices") else 0,
                "currency": "EUR",
            })
        return plans

    def list_regions(self):
        r = self._get("/locations")
        return [{"id": str(l["id"]), "name": l["name"], "city": l["city"], "country": l["country"]}
                for l in r.get("locations", [])]

    def list_images(self):
        r = self._get("/images?type=system&status=available&per_page=50")
        return [{"id": str(i["id"]), "name": i["description"], "slug": i["name"]}
                for i in r.get("images", [])]

    def create_instance(self, name, plan_id, region_id, image_id, ssh_keys=None):
        payload = {
            "name": name,
            "server_type": plan_id,
            "location": region_id,
            "image": image_id,
            "start_after_create": True,
        }
        if ssh_keys:
            payload["ssh_keys"] = ssh_keys
        r = self._post("/servers", payload)
        srv = r.get("server", {})
        return {
            "provider_id": str(srv.get("id", "")),
            "name": srv.get("name", name),
            "status": srv.get("status", "unknown"),
            "ip": srv.get("public_net", {}).get("ipv4", {}).get("ip", ""),
            "ipv6": srv.get("public_net", {}).get("ipv6", {}).get("ip", ""),
        }

    def destroy_instance(self, provider_id):
        self._delete(f"/servers/{provider_id}")
        return True

    def get_instance(self, provider_id):
        r = self._get(f"/servers/{provider_id}")
        srv = r.get("server", {})
        return {
            "provider_id": str(srv["id"]),
            "name": srv["name"],
            "status": srv["status"],
            "ip": srv.get("public_net", {}).get("ipv4", {}).get("ip", ""),
            "vcpus": srv.get("server_type", {}).get("cores", 0),
            "ram_mb": int(srv.get("server_type", {}).get("memory", 0) * 1024),
            "disk_gb": srv.get("server_type", {}).get("disk", 0),
            "created": srv.get("created", ""),
        }

    def list_instances(self):
        r = self._get("/servers?per_page=50")
        results = []
        for srv in r.get("servers", []):
            results.append({
                "provider_id": str(srv["id"]),
                "name": srv["name"],
                "status": srv["status"],
                "ip": srv.get("public_net", {}).get("ipv4", {}).get("ip", ""),
            })
        return results

    def power_action(self, provider_id, action):
        # action: poweron, poweroff, reboot, reset
        self._post(f"/servers/{provider_id}/actions/{action}", {})
        return True

    def resize_instance(self, provider_id, new_plan_id):
        self._post(f"/servers/{provider_id}/actions/change_type", {
            "server_type": new_plan_id, "upgrade_disk": True
        })
        return True

    def create_snapshot(self, provider_id, description=""):
        r = self._post(f"/servers/{provider_id}/actions/create_image", {
            "description": description or f"snapshot-{int(time.time())}",
            "type": "snapshot"
        })
        return {"id": str(r.get("image", {}).get("id", "")), "status": "creating"}

    def list_snapshots(self):
        r = self._get("/images?type=snapshot&per_page=50")
        return [{"id": str(i["id"]), "name": i.get("description", ""), "size_gb": i.get("image_size", 0),
                 "created": i.get("created", "")} for i in r.get("images", [])]

    def delete_snapshot(self, snapshot_id):
        self._delete(f"/images/{snapshot_id}")
        return True

    def list_firewalls(self):
        r = self._get("/firewalls?per_page=50")
        return [{"id": str(f["id"]), "name": f["name"],
                 "rules_count": len(f.get("rules", []))} for f in r.get("firewalls", [])]

    def create_firewall(self, name, rules):
        # rules: [{"direction":"in","protocol":"tcp","port":"22","source_ips":["0.0.0.0/0"]}]
        fw_rules = []
        for rule in rules:
            fw_rules.append({
                "direction": rule.get("direction", "in"),
                "protocol": rule.get("protocol", "tcp"),
                "port": rule.get("port", "22"),
                "source_ips": rule.get("source_ips", ["0.0.0.0/0", "::/0"]),
            })
        r = self._post("/firewalls", {"name": name, "rules": fw_rules})
        return {"id": str(r.get("firewall", {}).get("id", "")), "name": name}

    def delete_firewall(self, firewall_id):
        self._delete(f"/firewalls/{firewall_id}")
        return True

    def list_ssh_keys(self):
        r = self._get("/ssh_keys?per_page=50")
        return [{"id": str(k["id"]), "name": k["name"], "fingerprint": k.get("fingerprint", "")}
                for k in r.get("ssh_keys", [])]

    def add_ssh_key(self, name, public_key):
        r = self._post("/ssh_keys", {"name": name, "public_key": public_key})
        return {"id": str(r.get("ssh_key", {}).get("id", "")), "name": name}

    def delete_ssh_key(self, key_id):
        self._delete(f"/ssh_keys/{key_id}")
        return True


# ── DigitalOcean ─────────────────────────────────────────────────────────────

class DigitalOceanProvider:
    name = "digitalocean"
    display = "DigitalOcean"
    base = "https://api.digitalocean.com/v2"

    def __init__(self, api_key):
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _get(self, path):
        return _api("GET", f"{self.base}{path}", self.headers)

    def _post(self, path, data):
        return _api("POST", f"{self.base}{path}", self.headers, data)

    def _delete(self, path):
        return _api("DELETE", f"{self.base}{path}", self.headers)

    def list_plans(self):
        r = self._get("/sizes?per_page=100")
        return [{"id": s["slug"], "name": s["slug"], "description": s.get("description", s["slug"]),
                 "vcpus": s["vcpus"], "ram_mb": s["memory"], "disk_gb": s["disk"],
                 "price_monthly": s["price_monthly"], "currency": "USD"}
                for s in r.get("sizes", []) if s.get("available")]

    def list_regions(self):
        r = self._get("/regions?per_page=100")
        return [{"id": rg["slug"], "name": rg["name"], "city": rg["name"], "country": ""}
                for rg in r.get("regions", []) if rg.get("available")]

    def list_images(self):
        r = self._get("/images?type=distribution&per_page=100")
        return [{"id": str(i["id"]), "name": i["description"], "slug": i["slug"] or str(i["id"])}
                for i in r.get("images", []) if i.get("slug")]

    def create_instance(self, name, plan_id, region_id, image_id, ssh_keys=None):
        payload = {"name": name, "size": plan_id, "region": region_id, "image": image_id}
        if ssh_keys:
            payload["ssh_keys"] = ssh_keys
        r = self._post("/droplets", payload)
        d = r.get("droplet", {})
        nets = d.get("networks", {}).get("v4", [])
        ip = next((n["ip_address"] for n in nets if n["type"] == "public"), "")
        return {"provider_id": str(d.get("id", "")), "name": d.get("name", name),
                "status": d.get("status", "new"), "ip": ip, "ipv6": ""}

    def destroy_instance(self, provider_id):
        self._delete(f"/droplets/{provider_id}")
        return True

    def get_instance(self, provider_id):
        r = self._get(f"/droplets/{provider_id}")
        d = r.get("droplet", {})
        nets = d.get("networks", {}).get("v4", [])
        ip = next((n["ip_address"] for n in nets if n["type"] == "public"), "")
        return {"provider_id": str(d["id"]), "name": d["name"], "status": d["status"], "ip": ip,
                "vcpus": d.get("vcpus", 0), "ram_mb": d.get("memory", 0),
                "disk_gb": d.get("disk", 0), "created": d.get("created_at", "")}

    def list_instances(self):
        r = self._get("/droplets?per_page=100")
        results = []
        for d in r.get("droplets", []):
            nets = d.get("networks", {}).get("v4", [])
            ip = next((n["ip_address"] for n in nets if n["type"] == "public"), "")
            results.append({"provider_id": str(d["id"]), "name": d["name"],
                            "status": d["status"], "ip": ip})
        return results

    def power_action(self, provider_id, action):
        action_map = {"poweron": "power_on", "poweroff": "power_off",
                       "reboot": "reboot", "reset": "power_cycle"}
        self._post(f"/droplets/{provider_id}/actions", {"type": action_map.get(action, action)})
        return True

    def resize_instance(self, provider_id, new_plan_id):
        self._post(f"/droplets/{provider_id}/actions", {"type": "resize", "size": new_plan_id, "disk": True})
        return True

    def create_snapshot(self, provider_id, description=""):
        name = description or f"snapshot-{int(time.time())}"
        r = self._post(f"/droplets/{provider_id}/actions", {"type": "snapshot", "name": name})
        return {"id": str(r.get("action", {}).get("id", "")), "status": "creating"}

    def list_snapshots(self):
        r = self._get("/snapshots?resource_type=droplet&per_page=100")
        return [{"id": str(s["id"]), "name": s["name"], "size_gb": s.get("size_gigabytes", 0),
                 "created": s.get("created_at", "")} for s in r.get("snapshots", [])]

    def delete_snapshot(self, snapshot_id):
        self._delete(f"/snapshots/{snapshot_id}")
        return True

    def list_firewalls(self):
        r = self._get("/firewalls?per_page=100")
        return [{"id": f["id"], "name": f["name"],
                 "rules_count": len(f.get("inbound_rules", []))} for f in r.get("firewalls", [])]

    def create_firewall(self, name, rules):
        inbound = []
        for rule in rules:
            inbound.append({"protocol": rule.get("protocol", "tcp"),
                           "ports": rule.get("port", "22"),
                           "sources": {"addresses": rule.get("source_ips", ["0.0.0.0/0", "::/0"])}})
        r = self._post("/firewalls", {"name": name, "inbound_rules": inbound,
                                       "outbound_rules": [{"protocol": "tcp", "ports": "all",
                                                           "destinations": {"addresses": ["0.0.0.0/0", "::/0"]}}]})
        return {"id": r.get("firewall", {}).get("id", ""), "name": name}

    def delete_firewall(self, firewall_id):
        self._delete(f"/firewalls/{firewall_id}")
        return True

    def list_ssh_keys(self):
        r = self._get("/account/keys?per_page=100")
        return [{"id": str(k["id"]), "name": k["name"], "fingerprint": k.get("fingerprint", "")}
                for k in r.get("ssh_keys", [])]

    def add_ssh_key(self, name, public_key):
        r = self._post("/account/keys", {"name": name, "public_key": public_key})
        return {"id": str(r.get("ssh_key", {}).get("id", "")), "name": name}

    def delete_ssh_key(self, key_id):
        self._delete(f"/account/keys/{key_id}")
        return True


# ── Vultr ────────────────────────────────────────────────────────────────────

class VultrProvider:
    name = "vultr"
    display = "Vultr"
    base = "https://api.vultr.com/v2"

    def __init__(self, api_key):
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _get(self, path):
        return _api("GET", f"{self.base}{path}", self.headers)

    def _post(self, path, data):
        return _api("POST", f"{self.base}{path}", self.headers, data)

    def _delete(self, path):
        return _api("DELETE", f"{self.base}{path}", self.headers)

    def _patch(self, path, data):
        return _api("PATCH", f"{self.base}{path}", self.headers, data)

    def list_plans(self):
        r = self._get("/plans?type=vc2&per_page=100")
        return [{"id": p["id"], "name": p["id"],
                 "description": f"{p['vcpu_count']}vCPU / {p['ram']}MB / {p['disk']}GB",
                 "vcpus": p["vcpu_count"], "ram_mb": p["ram"], "disk_gb": p["disk"],
                 "price_monthly": p["monthly_cost"], "currency": "USD"}
                for p in r.get("plans", [])]

    def list_regions(self):
        r = self._get("/regions?per_page=100")
        return [{"id": rg["id"], "name": rg["city"], "city": rg["city"], "country": rg["country"]}
                for rg in r.get("regions", [])]

    def list_images(self):
        r = self._get("/os?per_page=100")
        return [{"id": str(o["id"]), "name": o["name"], "slug": str(o["id"])}
                for o in r.get("os", []) if o.get("arch") == "x64"]

    def create_instance(self, name, plan_id, region_id, image_id, ssh_keys=None):
        payload = {"label": name, "plan": plan_id, "region": region_id, "os_id": int(image_id)}
        if ssh_keys:
            payload["sshkey_id"] = ssh_keys
        r = self._post("/instances", payload)
        inst = r.get("instance", {})
        return {"provider_id": inst.get("id", ""), "name": inst.get("label", name),
                "status": inst.get("status", "pending"), "ip": inst.get("main_ip", ""), "ipv6": inst.get("v6_main_ip", "")}

    def destroy_instance(self, provider_id):
        self._delete(f"/instances/{provider_id}")
        return True

    def get_instance(self, provider_id):
        r = self._get(f"/instances/{provider_id}")
        inst = r.get("instance", {})
        return {"provider_id": inst["id"], "name": inst.get("label", ""), "status": inst["status"],
                "ip": inst.get("main_ip", ""), "vcpus": inst.get("vcpu_count", 0),
                "ram_mb": inst.get("ram", 0), "disk_gb": inst.get("disk", 0),
                "created": inst.get("date_created", "")}

    def list_instances(self):
        r = self._get("/instances?per_page=100")
        return [{"provider_id": i["id"], "name": i.get("label", ""), "status": i["status"],
                 "ip": i.get("main_ip", "")} for i in r.get("instances", [])]

    def power_action(self, provider_id, action):
        action_map = {"poweron": "start", "poweroff": "halt", "reboot": "reboot", "reset": "reboot"}
        self._post(f"/instances/{provider_id}/{action_map.get(action, action)}", {})
        return True

    def resize_instance(self, provider_id, new_plan_id):
        self._patch(f"/instances/{provider_id}", {"plan": new_plan_id})
        return True

    def create_snapshot(self, provider_id, description=""):
        r = self._post("/snapshots", {"instance_id": provider_id,
                                       "description": description or f"snapshot-{int(time.time())}"})
        return {"id": r.get("snapshot", {}).get("id", ""), "status": "creating"}

    def list_snapshots(self):
        r = self._get("/snapshots?per_page=100")
        return [{"id": s["id"], "name": s.get("description", ""), "size_gb": int(s.get("size", 0)) // (1024**3),
                 "created": s.get("date_created", "")} for s in r.get("snapshots", [])]

    def delete_snapshot(self, snapshot_id):
        self._delete(f"/snapshots/{snapshot_id}")
        return True

    def list_firewalls(self):
        r = self._get("/firewalls?per_page=100")
        return [{"id": g["id"], "name": g["description"],
                 "rules_count": g.get("rule_count", 0)} for g in r.get("firewall_groups", [])]

    def create_firewall(self, name, rules):
        r = self._post("/firewalls", {"description": name})
        fw_id = r.get("firewall_group", {}).get("id", "")
        for rule in rules:
            self._post(f"/firewalls/{fw_id}/rules", {
                "ip_type": "v4", "protocol": rule.get("protocol", "tcp"),
                "port": rule.get("port", "22"), "subnet": "0.0.0.0", "subnet_size": 0
            })
        return {"id": fw_id, "name": name}

    def delete_firewall(self, firewall_id):
        self._delete(f"/firewalls/{firewall_id}")
        return True

    def list_ssh_keys(self):
        r = self._get("/ssh-keys?per_page=100")
        return [{"id": k["id"], "name": k["name"], "fingerprint": k.get("fingerprint", "")}
                for k in r.get("ssh_keys", [])]

    def add_ssh_key(self, name, public_key):
        r = self._post("/ssh-keys", {"name": name, "ssh_key": public_key})
        return {"id": r.get("ssh_key", {}).get("id", ""), "name": name}

    def delete_ssh_key(self, key_id):
        self._delete(f"/ssh-keys/{key_id}")
        return True


# ── Linode / Akamai ──────────────────────────────────────────────────────────

class LinodeProvider:
    name = "linode"
    display = "Linode / Akamai"
    base = "https://api.linode.com/v4"

    def __init__(self, api_key):
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _get(self, path):
        return _api("GET", f"{self.base}{path}", self.headers)

    def _post(self, path, data):
        return _api("POST", f"{self.base}{path}", self.headers, data)

    def _delete(self, path):
        return _api("DELETE", f"{self.base}{path}", self.headers)

    def _put(self, path, data):
        return _api("PUT", f"{self.base}{path}", self.headers, data)

    def list_plans(self):
        r = self._get("/linode/types?page_size=100")
        return [{"id": t["id"], "name": t["label"],
                 "description": t["label"],
                 "vcpus": t["vcpus"], "ram_mb": t["memory"], "disk_gb": t["disk"] // 1024,
                 "price_monthly": t["price"]["monthly"], "currency": "USD"}
                for t in r.get("data", [])]

    def list_regions(self):
        r = self._get("/regions?page_size=100")
        return [{"id": rg["id"], "name": rg["label"], "city": rg["label"], "country": rg.get("country", "")}
                for rg in r.get("data", []) if rg.get("status") == "ok"]

    def list_images(self):
        r = self._get("/images?page_size=100")
        return [{"id": i["id"], "name": i["label"], "slug": i["id"]}
                for i in r.get("data", []) if i.get("is_public") and "linode/" in i.get("id", "")]

    def create_instance(self, name, plan_id, region_id, image_id, ssh_keys=None):
        payload = {"label": name, "type": plan_id, "region": region_id, "image": image_id, "booted": True}
        if ssh_keys:
            payload["authorized_keys"] = ssh_keys
        else:
            payload["root_pass"] = secrets.token_urlsafe(24)
        r = self._post("/linode/instances", payload)
        ips = r.get("ipv4", [])
        return {"provider_id": str(r.get("id", "")), "name": r.get("label", name),
                "status": r.get("status", "provisioning"), "ip": ips[0] if ips else "", "ipv6": r.get("ipv6", "")}

    def destroy_instance(self, provider_id):
        self._delete(f"/linode/instances/{provider_id}")
        return True

    def get_instance(self, provider_id):
        r = self._get(f"/linode/instances/{provider_id}")
        ips = r.get("ipv4", [])
        specs = r.get("specs", {})
        return {"provider_id": str(r["id"]), "name": r["label"], "status": r["status"],
                "ip": ips[0] if ips else "", "vcpus": specs.get("vcpus", 0),
                "ram_mb": specs.get("memory", 0), "disk_gb": specs.get("disk", 0) // 1024,
                "created": r.get("created", "")}

    def list_instances(self):
        r = self._get("/linode/instances?page_size=100")
        results = []
        for inst in r.get("data", []):
            ips = inst.get("ipv4", [])
            results.append({"provider_id": str(inst["id"]), "name": inst["label"],
                            "status": inst["status"], "ip": ips[0] if ips else ""})
        return results

    def power_action(self, provider_id, action):
        action_map = {"poweron": "boot", "poweroff": "shutdown", "reboot": "reboot", "reset": "reboot"}
        self._post(f"/linode/instances/{provider_id}/{action_map.get(action, action)}", {})
        return True

    def resize_instance(self, provider_id, new_plan_id):
        self._post(f"/linode/instances/{provider_id}/resize", {"type": new_plan_id})
        return True

    def create_snapshot(self, provider_id, description=""):
        label = description or f"snapshot-{int(time.time())}"
        r = self._post(f"/linode/instances/{provider_id}/backups", {"label": label})
        return {"id": str(r.get("id", "")), "status": "creating"}

    def list_snapshots(self):
        # Linode backups are per-instance; list all instances' backups
        instances = self.list_instances()
        all_snaps = []
        for inst in instances:
            try:
                r = self._get(f"/linode/instances/{inst['provider_id']}/backups")
                for snap in r.get("automatic", []) + ([r.get("snapshot", {}).get("current")] if r.get("snapshot", {}).get("current") else []):
                    if snap:
                        all_snaps.append({"id": str(snap.get("id", "")), "name": snap.get("label", ""),
                                          "size_gb": snap.get("disks", [{}])[0].get("size", 0) // 1024 if snap.get("disks") else 0,
                                          "created": snap.get("created", "")})
            except ProviderError:
                pass
        return all_snaps

    def delete_snapshot(self, snapshot_id):
        # Linode doesn't support deleting individual backups easily
        raise ProviderError("Linode manages backup retention automatically")

    def list_firewalls(self):
        r = self._get("/networking/firewalls?page_size=100")
        return [{"id": str(f["id"]), "name": f["label"],
                 "rules_count": len(f.get("rules", {}).get("inbound", []))} for f in r.get("data", [])]

    def create_firewall(self, name, rules):
        inbound = []
        for rule in rules:
            inbound.append({
                "action": "ACCEPT", "protocol": rule.get("protocol", "TCP").upper(),
                "ports": rule.get("port", "22"),
                "addresses": {"ipv4": rule.get("source_ips", ["0.0.0.0/0"]),
                              "ipv6": ["::/0"]}
            })
        payload = {"label": name, "rules": {
            "inbound": inbound,
            "outbound": [{"action": "ACCEPT", "protocol": "TCP", "ports": "1-65535",
                          "addresses": {"ipv4": ["0.0.0.0/0"], "ipv6": ["::/0"]}}],
            "inbound_policy": "DROP", "outbound_policy": "ACCEPT"
        }}
        r = self._post("/networking/firewalls", payload)
        return {"id": str(r.get("id", "")), "name": name}

    def delete_firewall(self, firewall_id):
        self._delete(f"/networking/firewalls/{firewall_id}")
        return True

    def list_ssh_keys(self):
        r = self._get("/profile/sshkeys?page_size=100")
        return [{"id": str(k["id"]), "name": k["label"], "fingerprint": ""}
                for k in r.get("data", [])]

    def add_ssh_key(self, name, public_key):
        r = self._post("/profile/sshkeys", {"label": name, "ssh_key": public_key})
        return {"id": str(r.get("id", "")), "name": name}

    def delete_ssh_key(self, key_id):
        self._delete(f"/profile/sshkeys/{key_id}")
        return True


# ─── Provider Registry ───────────────────────────────────────────────────────

PROVIDERS = {
    "hetzner": HetznerProvider,
    "digitalocean": DigitalOceanProvider,
    "vultr": VultrProvider,
    "linode": LinodeProvider,
}


def get_provider(name, api_key):
    cls = PROVIDERS.get(name)
    if not cls:
        raise ProviderError(f"Unknown provider: {name}")
    return cls(api_key)


# ─── Database ────────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS provider_keys (
            provider TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            added_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            plan_id TEXT,
            region_id TEXT,
            image_id TEXT,
            status TEXT DEFAULT 'provisioning',
            ip TEXT DEFAULT '',
            ipv6 TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            destroyed_at TEXT,
            label TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_plan_id TEXT NOT NULL,
            price_monthly REAL DEFAULT 0,
            markup_pct REAL DEFAULT 20,
            active INTEGER DEFAULT 1,
            vcpus INTEGER DEFAULT 0,
            ram_mb INTEGER DEFAULT 0,
            disk_gb INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            detail TEXT DEFAULT '',
            ts TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS dns_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            domain TEXT NOT NULL,
            record_type TEXT DEFAULT 'A',
            name TEXT DEFAULT '@',
            value TEXT NOT NULL,
            ttl INTEGER DEFAULT 3600,
            provider_record_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn


def audit(conn, action, detail=""):
    conn.execute("INSERT INTO audit_log (action, detail) VALUES (?, ?)", (action, detail))
    conn.commit()


# ─── Session Management ─────────────────────────────────────────────────────

def _get_session_secret():
    global SESSION_SECRET
    if SESSION_SECRET is None:
        secret_path = os.path.join(DATA_DIR, ".session_secret")
        if os.path.exists(secret_path):
            with open(secret_path) as f:
                SESSION_SECRET = f.read().strip()
        else:
            SESSION_SECRET = secrets.token_hex(32)
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(secret_path, "w") as f:
                f.write(SESSION_SECRET)
            os.chmod(secret_path, 0o600)
    return SESSION_SECRET


def create_session(conn):
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT INTO sessions (token, expires_at) VALUES (?, datetime('now', '+24 hours'))", (token,))
    conn.commit()
    return token


def verify_session(conn, token):
    if not token:
        return False
    row = conn.execute("SELECT * FROM sessions WHERE token = ? AND expires_at > datetime('now')", (token,)).fetchone()
    return row is not None


# ─── HTML Templates ──────────────────────────────────────────────────────────

BRAND_CSS = """
:root {
    --bg: #0f1117; --surface: #1a1d27; --surface2: #242836;
    --border: #2d3348; --text: #e4e6f0; --text-dim: #8b8fa3;
    --green: #4ade80; --green-dim: #166534; --red: #f87171;
    --blue: #60a5fa; --yellow: #fbbf24; --purple: #a78bfa;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
h1, h2, h3 { font-weight: 600; }
a { color: var(--green); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Navigation */
.navbar { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 24px; display: flex; align-items: center; height: 56px; position: sticky; top: 0; z-index: 100; }
.navbar .brand { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; color: var(--green); }
.navbar .brand span { color: var(--text-dim); font-weight: 400; font-size: 12px; }
.navbar nav { margin-left: 40px; display: flex; gap: 4px; }
.navbar nav a { color: var(--text-dim); padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 500; }
.navbar nav a:hover, .navbar nav a.active { color: var(--text); background: var(--surface2); text-decoration: none; }
.navbar .right { margin-left: auto; }

/* Cards */
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.card h2 { font-size: 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.card h3 { font-size: 14px; margin-bottom: 12px; color: var(--text-dim); }

/* Tables */
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); padding: 10px 12px; border-bottom: 1px solid var(--border); }
td { padding: 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
tr:hover { background: var(--surface2); }

/* Buttons */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s; }
.btn-primary { background: var(--green); color: #000; }
.btn-primary:hover { background: #22c55e; }
.btn-danger { background: var(--red); color: #fff; }
.btn-danger:hover { background: #ef4444; }
.btn-secondary { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--border); }
.btn-sm { padding: 4px 10px; font-size: 12px; }

/* Forms */
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 500; color: var(--text-dim); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
input, select, textarea { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 14px; font-family: inherit; }
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--green); }

/* Status badges */
.badge { display: inline-block; padding: 2px 8px; border-radius: 100px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
.badge-running { background: var(--green-dim); color: var(--green); }
.badge-stopped { background: #3f1d1d; color: var(--red); }
.badge-pending { background: #422006; color: var(--yellow); }

/* Grid */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

/* Stats */
.stat { text-align: center; padding: 20px; }
.stat .value { font-size: 28px; font-weight: 700; color: var(--green); }
.stat .label { font-size: 12px; color: var(--text-dim); margin-top: 4px; }

/* Alerts */
.alert { padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
.alert-info { background: #1e3a5f; border: 1px solid #2563eb; color: var(--blue); }
.alert-success { background: #14532d; border: 1px solid var(--green); color: var(--green); }
.alert-error { background: #3f1d1d; border: 1px solid var(--red); color: var(--red); }
.alert-warning { background: #422006; border: 1px solid var(--yellow); color: var(--yellow); }

/* Modal */
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 200; justify-content: center; align-items: center; }
.modal-overlay.active { display: flex; }
.modal { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 32px; width: 90%; max-width: 540px; max-height: 80vh; overflow-y: auto; }
.modal h2 { margin-bottom: 24px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 24px; }

@media (max-width: 768px) {
    .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
    .navbar nav { display: none; }
}
"""

def page_layout(title, content, active="dashboard"):
    nav_items = [
        ("dashboard", "Dashboard", "/"),
        ("instances", "Instances", "/instances"),
        ("snapshots", "Snapshots", "/snapshots"),
        ("firewalls", "Firewalls", "/firewalls"),
        ("ssh-keys", "SSH Keys", "/ssh-keys"),
        ("providers", "Providers", "/providers"),
        ("audit", "Audit Log", "/audit"),
    ]
    nav_html = ""
    for key, label, href in nav_items:
        cls = ' class="active"' if key == active else ""
        nav_html += f'<a href="{href}"{cls}>{label}</a>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — CloverVPS</title>
    <style>{BRAND_CSS}</style>
</head>
<body>
    <div class="navbar">
        <div class="brand">🍀 CloverVPS <span>v0.1.0</span></div>
        <nav>{nav_html}</nav>
        <div class="right"><a href="/logout" class="btn btn-secondary btn-sm">Logout</a></div>
    </div>
    <div class="container">{content}</div>
</body>
</html>"""


def login_page(error=""):
    err_html = f'<div class="alert alert-error">{html.escape(error)}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login — CloverVPS</title>
    <style>{BRAND_CSS}
    .login-box {{ max-width: 400px; margin: 120px auto; }}
    .login-box h1 {{ text-align: center; margin-bottom: 8px; color: var(--green); }}
    .login-box p {{ text-align: center; color: var(--text-dim); margin-bottom: 24px; }}
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🍀 CloverVPS</h1>
        <p>White-label VPS Management</p>
        <div class="card">
            {err_html}
            <form method="POST" action="/login">
                <div class="form-group">
                    <label>Admin Password</label>
                    <input type="password" name="password" autofocus required placeholder="Enter admin password">
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%">Sign In</button>
            </form>
            <p style="margin-top:16px; font-size:12px; color:var(--text-dim); text-align:center;">
                Default password is set during mycloverOS first-boot setup.
            </p>
        </div>
    </div>
</body>
</html>"""


# ─── Web Handler ─────────────────────────────────────────────────────────────

class VPSHandler(http.server.BaseHTTPRequestHandler):
    conn = None

    def log_message(self, fmt, *args):
        print(f"[CloverVPS] {self.address_string()} {fmt % args}", flush=True)

    def _send(self, code, body, content_type="text/html"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, indent=2), "application/json")

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def _get_cookie(self, name):
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            part = part.strip()
            if part.startswith(f"{name}="):
                return part[len(name)+1:]
        return None

    def _set_cookie(self, name, value, max_age=86400):
        self.send_header("Set-Cookie", f"{name}={value}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Strict")

    def _auth_ok(self):
        token = self._get_cookie("cvps_session")
        return verify_session(self.conn, token)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length > 0 else b""

    def _parse_form(self):
        body = self._read_body().decode("utf-8")
        return dict(urllib.parse.parse_qsl(body))

    def _get_configured_providers(self):
        rows = self.conn.execute("SELECT provider, api_key FROM provider_keys WHERE enabled=1").fetchall()
        result = {}
        for row in rows:
            try:
                result[row["provider"]] = get_provider(row["provider"], row["api_key"])
            except Exception:
                pass
        return result

    # ── GET routes ──

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/login":
            self._send(200, login_page())
            return

        if path == "/logout":
            token = self._get_cookie("cvps_session")
            if token:
                self.conn.execute("DELETE FROM sessions WHERE token=?", (token,))
                self.conn.commit()
            self._redirect("/login")
            return

        if not self._auth_ok():
            self._redirect("/login")
            return

        if path == "/" or path == "/dashboard":
            self._page_dashboard()
        elif path == "/instances":
            self._page_instances()
        elif path == "/instances/new":
            self._page_new_instance()
        elif path == "/snapshots":
            self._page_snapshots()
        elif path == "/firewalls":
            self._page_firewalls()
        elif path == "/firewalls/new":
            self._page_new_firewall()
        elif path == "/ssh-keys":
            self._page_ssh_keys()
        elif path == "/providers":
            self._page_providers()
        elif path == "/audit":
            self._page_audit()
        elif path.startswith("/api/"):
            self._handle_api_get(path)
        else:
            self._send(404, page_layout("Not Found", '<div class="alert alert-error">Page not found</div>'))

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/login":
            self._handle_login()
            return

        if not self._auth_ok():
            self._redirect("/login")
            return

        if path == "/providers/save":
            self._handle_save_provider()
        elif path == "/providers/delete":
            self._handle_delete_provider()
        elif path == "/instances/create":
            self._handle_create_instance()
        elif path == "/instances/action":
            self._handle_instance_action()
        elif path == "/instances/destroy":
            self._handle_destroy_instance()
        elif path == "/snapshots/create":
            self._handle_create_snapshot()
        elif path == "/snapshots/delete":
            self._handle_delete_snapshot()
        elif path == "/firewalls/create":
            self._handle_create_firewall()
        elif path == "/firewalls/delete":
            self._handle_delete_firewall()
        elif path == "/ssh-keys/add":
            self._handle_add_ssh_key()
        elif path == "/ssh-keys/delete":
            self._handle_delete_ssh_key()
        elif path.startswith("/api/"):
            self._handle_api_post(path)
        else:
            self._send(404, "Not found")

    # ── Login ──

    def _handle_login(self):
        form = self._parse_form()
        password = form.get("password", "")
        # Check against system admin password (the user created during first-boot setup)
        # Verify by checking if the password matches any sudo user's password via PAM
        # For simplicity, we use a stored admin hash
        admin_hash_path = os.path.join(DATA_DIR, ".admin_hash")
        if os.path.exists(admin_hash_path):
            with open(admin_hash_path) as f:
                stored = f.read().strip()
            check = hashlib.sha256(password.encode()).hexdigest()
            if check != stored:
                self._send(200, login_page("Invalid password"))
                return
        else:
            # First login — set the admin password
            os.makedirs(DATA_DIR, exist_ok=True)
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            with open(admin_hash_path, "w") as f:
                f.write(pw_hash)
            os.chmod(admin_hash_path, 0o600)
            audit(self.conn, "admin_setup", "Initial admin password set")

        token = create_session(self.conn)
        self.send_response(302)
        self.send_header("Location", "/")
        self._set_cookie("cvps_session", token)
        self.end_headers()
        audit(self.conn, "login", f"from {self.client_address[0]}")

    # ── Dashboard ──

    def _page_dashboard(self):
        providers = self._get_configured_providers()
        total_instances = self.conn.execute("SELECT COUNT(*) FROM instances WHERE destroyed_at IS NULL").fetchone()[0]

        # Count by provider
        by_provider = self.conn.execute(
            "SELECT provider, COUNT(*) as cnt FROM instances WHERE destroyed_at IS NULL GROUP BY provider"
        ).fetchall()

        provider_stats = ""
        for row in by_provider:
            p_name = PROVIDERS.get(row["provider"], type("", (), {"display": row["provider"]})).display
            provider_stats += f'<div class="stat"><div class="value">{row["cnt"]}</div><div class="label">{p_name}</div></div>'

        configured = len(providers)
        recent_audit = self.conn.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10").fetchall()
        audit_rows = ""
        for row in recent_audit:
            audit_rows += f'<tr><td style="color:var(--text-dim)">{row["ts"]}</td><td>{html.escape(row["action"])}</td><td>{html.escape(row["detail"])}</td></tr>'

        content = f"""
        <h1 style="margin-bottom:24px">Dashboard</h1>
        <div class="grid-4">
            <div class="card stat"><div class="value">{total_instances}</div><div class="label">Active Instances</div></div>
            <div class="card stat"><div class="value">{configured}</div><div class="label">Providers Connected</div></div>
            <div class="card stat"><div class="value">{len(PROVIDERS)}</div><div class="label">Providers Available</div></div>
            {provider_stats or '<div class="card stat"><div class="value">—</div><div class="label">No Instances Yet</div></div>'}
        </div>
        {'<div class="alert alert-warning">⚠️ No providers configured yet. <a href="/providers">Add a provider API key</a> to get started.</div>' if not providers else ''}
        <div class="card">
            <h2>📋 Recent Activity</h2>
            <table>
                <tr><th>Time</th><th>Action</th><th>Detail</th></tr>
                {audit_rows or '<tr><td colspan="3" style="color:var(--text-dim)">No activity yet</td></tr>'}
            </table>
        </div>
        """
        self._send(200, page_layout("Dashboard", content, "dashboard"))

    # ── Instances ──

    def _page_instances(self):
        instances = self.conn.execute(
            "SELECT * FROM instances WHERE destroyed_at IS NULL ORDER BY created_at DESC"
        ).fetchall()

        rows = ""
        for inst in instances:
            status_cls = "badge-running" if inst["status"] in ("running", "active") else \
                         "badge-stopped" if inst["status"] in ("off", "stopped") else "badge-pending"
            p_display = PROVIDERS.get(inst["provider"], type("", (), {"display": inst["provider"]})).display
            rows += f"""<tr>
                <td><strong>{html.escape(inst['name'])}</strong></td>
                <td>{p_display}</td>
                <td><code>{inst['ip'] or '—'}</code></td>
                <td><span class="badge {status_cls}">{inst['status']}</span></td>
                <td>{inst['created_at']}</td>
                <td>
                    <form method="POST" action="/instances/action" style="display:inline">
                        <input type="hidden" name="id" value="{inst['id']}">
                        <input type="hidden" name="action" value="reboot">
                        <button class="btn btn-secondary btn-sm" title="Reboot">⟳</button>
                    </form>
                    <form method="POST" action="/instances/destroy" style="display:inline"
                          onsubmit="return confirm('Destroy {html.escape(inst['name'])}? This cannot be undone.')">
                        <input type="hidden" name="id" value="{inst['id']}">
                        <button class="btn btn-danger btn-sm">Destroy</button>
                    </form>
                </td>
            </tr>"""

        content = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px">
            <h1>Instances</h1>
            <a href="/instances/new" class="btn btn-primary">+ New Instance</a>
        </div>
        <div class="card">
            <table>
                <tr><th>Name</th><th>Provider</th><th>IP Address</th><th>Status</th><th>Created</th><th>Actions</th></tr>
                {rows or '<tr><td colspan="6" style="color:var(--text-dim); text-align:center; padding:40px">No instances yet. <a href="/instances/new">Create your first instance</a></td></tr>'}
            </table>
        </div>
        """
        self._send(200, page_layout("Instances", content, "instances"))

    def _page_new_instance(self):
        providers = self._get_configured_providers()
        if not providers:
            content = '<div class="alert alert-warning">No providers configured. <a href="/providers">Add a provider</a> first.</div>'
            self._send(200, page_layout("New Instance", content, "instances"))
            return

        provider_options = "".join(f'<option value="{name}">{PROVIDERS[name].display}</option>' for name in providers)

        content = f"""
        <h1 style="margin-bottom:24px">Create Instance</h1>
        <div class="card">
            <form method="POST" action="/instances/create" id="createForm">
                <div class="grid-2">
                    <div class="form-group">
                        <label>Instance Name</label>
                        <input type="text" name="name" required placeholder="my-server-01" pattern="[a-zA-Z0-9][a-zA-Z0-9\\-]*">
                    </div>
                    <div class="form-group">
                        <label>Provider</label>
                        <select name="provider" id="providerSelect" onchange="loadOptions()">{provider_options}</select>
                    </div>
                </div>
                <div class="grid-3">
                    <div class="form-group">
                        <label>Region</label>
                        <select name="region_id" id="regionSelect"><option>Loading...</option></select>
                    </div>
                    <div class="form-group">
                        <label>Plan</label>
                        <select name="plan_id" id="planSelect"><option>Loading...</option></select>
                    </div>
                    <div class="form-group">
                        <label>Image / OS</label>
                        <select name="image_id" id="imageSelect"><option>Loading...</option></select>
                    </div>
                </div>
                <div class="form-group">
                    <label>SSH Key (optional)</label>
                    <select name="ssh_key_id" id="sshKeySelect"><option value="">None</option></select>
                </div>
                <div style="display:flex; gap:8px; margin-top:8px">
                    <button type="submit" class="btn btn-primary">Create Instance</button>
                    <a href="/instances" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
        <script>
        async function loadOptions() {{
            const provider = document.getElementById('providerSelect').value;
            // Load regions
            const regions = await (await fetch('/api/providers/' + provider + '/regions')).json();
            const regionSel = document.getElementById('regionSelect');
            regionSel.innerHTML = regions.map(r => '<option value="' + r.id + '">' + r.name + (r.city ? ' (' + r.city + ')' : '') + '</option>').join('');
            // Load plans
            const plans = await (await fetch('/api/providers/' + provider + '/plans')).json();
            const planSel = document.getElementById('planSelect');
            planSel.innerHTML = plans.map(p => '<option value="' + p.id + '">' + p.name + ' — ' + p.vcpus + 'vCPU / ' + Math.round(p.ram_mb/1024) + 'GB / ' + p.disk_gb + 'GB — $' + p.price_monthly + '/mo</option>').join('');
            // Load images
            const images = await (await fetch('/api/providers/' + provider + '/images')).json();
            const imgSel = document.getElementById('imageSelect');
            imgSel.innerHTML = images.map(i => '<option value="' + i.id + '">' + i.name + '</option>').join('');
            // Load SSH keys
            const keys = await (await fetch('/api/providers/' + provider + '/ssh-keys')).json();
            const keySel = document.getElementById('sshKeySelect');
            keySel.innerHTML = '<option value="">None</option>' + keys.map(k => '<option value="' + k.id + '">' + k.name + '</option>').join('');
        }}
        loadOptions();
        </script>
        """
        self._send(200, page_layout("New Instance", content, "instances"))

    # ── Snapshots ──

    def _page_snapshots(self):
        providers = self._get_configured_providers()
        rows = ""
        for name, prov in providers.items():
            try:
                snaps = prov.list_snapshots()
                for s in snaps:
                    rows += f"""<tr>
                        <td>{html.escape(s.get('name',''))}</td>
                        <td>{PROVIDERS[name].display}</td>
                        <td>{s.get('size_gb',0)} GB</td>
                        <td>{s.get('created','')}</td>
                        <td>
                            <form method="POST" action="/snapshots/delete" style="display:inline"
                                  onsubmit="return confirm('Delete this snapshot?')">
                                <input type="hidden" name="provider" value="{name}">
                                <input type="hidden" name="snapshot_id" value="{s['id']}">
                                <button class="btn btn-danger btn-sm">Delete</button>
                            </form>
                        </td>
                    </tr>"""
            except ProviderError as e:
                rows += f'<tr><td colspan="5" style="color:var(--red)">{PROVIDERS[name].display}: {html.escape(str(e)[:100])}</td></tr>'

        # Instance list for creating snapshot
        instances = self.conn.execute("SELECT * FROM instances WHERE destroyed_at IS NULL").fetchall()
        inst_options = "".join(f'<option value="{i["id"]}">{html.escape(i["name"])} ({i["provider"]})</option>' for i in instances)

        content = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px">
            <h1>Snapshots</h1>
        </div>
        {f'''<div class="card" style="margin-bottom:16px">
            <h2>📸 Create Snapshot</h2>
            <form method="POST" action="/snapshots/create" style="display:flex;gap:8px;align-items:end">
                <div class="form-group" style="flex:1;margin:0">
                    <label>Instance</label>
                    <select name="instance_id">{inst_options}</select>
                </div>
                <div class="form-group" style="flex:1;margin:0">
                    <label>Description</label>
                    <input type="text" name="description" placeholder="Pre-upgrade backup">
                </div>
                <button class="btn btn-primary" style="margin-bottom:0">Create</button>
            </form>
        </div>''' if instances else ''}
        <div class="card">
            <table>
                <tr><th>Name</th><th>Provider</th><th>Size</th><th>Created</th><th>Actions</th></tr>
                {rows or '<tr><td colspan="5" style="color:var(--text-dim); text-align:center; padding:40px">No snapshots</td></tr>'}
            </table>
        </div>
        """
        self._send(200, page_layout("Snapshots", content, "snapshots"))

    # ── Firewalls ──

    def _page_firewalls(self):
        providers = self._get_configured_providers()
        rows = ""
        for name, prov in providers.items():
            try:
                fws = prov.list_firewalls()
                for fw in fws:
                    rows += f"""<tr>
                        <td>{html.escape(fw['name'])}</td>
                        <td>{PROVIDERS[name].display}</td>
                        <td>{fw['rules_count']}</td>
                        <td>
                            <form method="POST" action="/firewalls/delete" style="display:inline"
                                  onsubmit="return confirm('Delete firewall {html.escape(fw['name'])}?')">
                                <input type="hidden" name="provider" value="{name}">
                                <input type="hidden" name="firewall_id" value="{fw['id']}">
                                <button class="btn btn-danger btn-sm">Delete</button>
                            </form>
                        </td>
                    </tr>"""
            except ProviderError:
                pass

        content = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px">
            <h1>Firewalls</h1>
            <a href="/firewalls/new" class="btn btn-primary">+ New Firewall</a>
        </div>
        <div class="card">
            <table>
                <tr><th>Name</th><th>Provider</th><th>Rules</th><th>Actions</th></tr>
                {rows or '<tr><td colspan="4" style="color:var(--text-dim); text-align:center; padding:40px">No firewalls</td></tr>'}
            </table>
        </div>
        """
        self._send(200, page_layout("Firewalls", content, "firewalls"))

    def _page_new_firewall(self):
        providers = self._get_configured_providers()
        provider_options = "".join(f'<option value="{name}">{PROVIDERS[name].display}</option>' for name in providers)
        content = f"""
        <h1 style="margin-bottom:24px">Create Firewall</h1>
        <div class="card">
            <form method="POST" action="/firewalls/create">
                <div class="grid-2">
                    <div class="form-group"><label>Firewall Name</label><input type="text" name="name" required placeholder="web-firewall"></div>
                    <div class="form-group"><label>Provider</label><select name="provider">{provider_options}</select></div>
                </div>
                <h3>Inbound Rules</h3>
                <p style="color:var(--text-dim);font-size:12px;margin-bottom:12px">One rule per line: protocol,port,source (e.g. tcp,22,0.0.0.0/0)</p>
                <div class="form-group">
                    <textarea name="rules" rows="5" placeholder="tcp,22,0.0.0.0/0&#10;tcp,80,0.0.0.0/0&#10;tcp,443,0.0.0.0/0">tcp,22,0.0.0.0/0
tcp,80,0.0.0.0/0
tcp,443,0.0.0.0/0</textarea>
                </div>
                <div style="display:flex;gap:8px"><button type="submit" class="btn btn-primary">Create Firewall</button><a href="/firewalls" class="btn btn-secondary">Cancel</a></div>
            </form>
        </div>
        """
        self._send(200, page_layout("New Firewall", content, "firewalls"))

    # ── SSH Keys ──

    def _page_ssh_keys(self):
        providers = self._get_configured_providers()
        rows = ""
        for name, prov in providers.items():
            try:
                keys = prov.list_ssh_keys()
                for k in keys:
                    rows += f"""<tr>
                        <td>{html.escape(k['name'])}</td>
                        <td>{PROVIDERS[name].display}</td>
                        <td><code>{k.get('fingerprint','')[:24]}...</code></td>
                        <td>
                            <form method="POST" action="/ssh-keys/delete" style="display:inline"
                                  onsubmit="return confirm('Delete SSH key {html.escape(k['name'])}?')">
                                <input type="hidden" name="provider" value="{name}">
                                <input type="hidden" name="key_id" value="{k['id']}">
                                <button class="btn btn-danger btn-sm">Delete</button>
                            </form>
                        </td>
                    </tr>"""
            except ProviderError:
                pass

        provider_options = "".join(f'<option value="{name}">{PROVIDERS[name].display}</option>' for name in providers)
        content = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px">
            <h1>SSH Keys</h1>
        </div>
        <div class="card" style="margin-bottom:16px">
            <h2>🔑 Add SSH Key</h2>
            <form method="POST" action="/ssh-keys/add">
                <div class="grid-2">
                    <div class="form-group"><label>Key Name</label><input type="text" name="name" required placeholder="my-workstation"></div>
                    <div class="form-group"><label>Provider</label><select name="provider">{provider_options}</select></div>
                </div>
                <div class="form-group"><label>Public Key</label><textarea name="public_key" rows="3" required placeholder="ssh-rsa AAAA... user@host"></textarea></div>
                <button type="submit" class="btn btn-primary">Add Key</button>
            </form>
        </div>
        <div class="card">
            <table>
                <tr><th>Name</th><th>Provider</th><th>Fingerprint</th><th>Actions</th></tr>
                {rows or '<tr><td colspan="4" style="color:var(--text-dim); text-align:center; padding:40px">No SSH keys</td></tr>'}
            </table>
        </div>
        """
        self._send(200, page_layout("SSH Keys", content, "ssh-keys"))

    # ── Providers ──

    def _page_providers(self):
        configured = {r["provider"]: r for r in self.conn.execute("SELECT * FROM provider_keys").fetchall()}
        cards = ""
        for name, cls in PROVIDERS.items():
            is_configured = name in configured
            status = '<span class="badge badge-running">Connected</span>' if is_configured else '<span class="badge badge-stopped">Not Connected</span>'
            key_masked = configured[name]["api_key"][:8] + "..." if is_configured else ""

            cards += f"""
            <div class="card">
                <h2>{cls.display} {status}</h2>
                <form method="POST" action="/providers/save">
                    <input type="hidden" name="provider" value="{name}">
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="password" name="api_key" value="{key_masked}" placeholder="Enter API key"
                               onfocus="if(this.value.includes('...'))this.value=''">
                    </div>
                    <div style="display:flex;gap:8px">
                        <button type="submit" class="btn btn-primary btn-sm">{'Update' if is_configured else 'Connect'}</button>
                        {'<form method="POST" action="/providers/delete" style="display:inline"><input type="hidden" name="provider" value="' + name + '"><button class="btn btn-danger btn-sm">Disconnect</button></form>' if is_configured else ''}
                    </div>
                </form>
            </div>"""

        content = f"""
        <h1 style="margin-bottom:24px">Provider Configuration</h1>
        <div class="alert alert-info">🔒 API keys are stored locally on this mycloverOS instance in <code>/etc/myclover/clover-vps/</code>. They never leave this machine.</div>
        <div class="grid-2">{cards}</div>
        """
        self._send(200, page_layout("Providers", content, "providers"))

    # ── Audit Log ──

    def _page_audit(self):
        entries = self.conn.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT 100").fetchall()
        rows = ""
        for e in entries:
            rows += f'<tr><td style="color:var(--text-dim);white-space:nowrap">{e["ts"]}</td><td><strong>{html.escape(e["action"])}</strong></td><td>{html.escape(e["detail"])}</td></tr>'

        content = f"""
        <h1 style="margin-bottom:24px">Audit Log</h1>
        <div class="card">
            <table>
                <tr><th>Timestamp</th><th>Action</th><th>Details</th></tr>
                {rows or '<tr><td colspan="3" style="color:var(--text-dim); text-align:center; padding:40px">No audit entries</td></tr>'}
            </table>
        </div>
        """
        self._send(200, page_layout("Audit Log", content, "audit"))

    # ── API endpoints (for dynamic form loading) ──

    def _handle_api_get(self, path):
        parts = path.strip("/").split("/")
        # /api/providers/{name}/plans|regions|images|ssh-keys
        if len(parts) == 4 and parts[1] == "providers":
            provider_name = parts[2]
            resource = parts[3]
            row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=? AND enabled=1",
                                     (provider_name,)).fetchone()
            if not row:
                self._json(404, {"error": "Provider not configured"})
                return
            try:
                prov = get_provider(provider_name, row["api_key"])
                if resource == "plans":
                    self._json(200, prov.list_plans())
                elif resource == "regions":
                    self._json(200, prov.list_regions())
                elif resource == "images":
                    self._json(200, prov.list_images())
                elif resource == "ssh-keys":
                    self._json(200, prov.list_ssh_keys())
                else:
                    self._json(404, {"error": "Unknown resource"})
            except ProviderError as e:
                self._json(500, {"error": str(e)})
        else:
            self._json(404, {"error": "Unknown API endpoint"})

    def _handle_api_post(self, path):
        self._json(404, {"error": "Unknown API endpoint"})

    # ── POST handlers ──

    def _handle_save_provider(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        api_key = form.get("api_key", "").strip()
        if not api_key or "..." in api_key:
            self._redirect("/providers")
            return
        if provider not in PROVIDERS:
            self._redirect("/providers")
            return
        # Test the key
        try:
            prov = get_provider(provider, api_key)
            prov.list_regions()  # quick connectivity test
        except ProviderError as e:
            content = f'<div class="alert alert-error">Failed to connect to {PROVIDERS[provider].display}: {html.escape(str(e)[:200])}</div><a href="/providers" class="btn btn-secondary">Back</a>'
            self._send(200, page_layout("Error", content, "providers"))
            return

        self.conn.execute(
            "INSERT OR REPLACE INTO provider_keys (provider, api_key, enabled) VALUES (?, ?, 1)",
            (provider, api_key)
        )
        self.conn.commit()
        audit(self.conn, "provider_connected", f"{PROVIDERS[provider].display}")
        self._redirect("/providers")

    def _handle_delete_provider(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        self.conn.execute("DELETE FROM provider_keys WHERE provider=?", (provider,))
        self.conn.commit()
        audit(self.conn, "provider_disconnected", provider)
        self._redirect("/providers")

    def _handle_create_instance(self):
        form = self._parse_form()
        name = form.get("name", "").strip()
        provider_name = form.get("provider", "")
        region_id = form.get("region_id", "")
        plan_id = form.get("plan_id", "")
        image_id = form.get("image_id", "")
        ssh_key_id = form.get("ssh_key_id", "")

        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider_name,)).fetchone()
        if not row:
            self._redirect("/instances")
            return

        try:
            prov = get_provider(provider_name, row["api_key"])
            ssh_keys = [ssh_key_id] if ssh_key_id else None
            result = prov.create_instance(name, plan_id, region_id, image_id, ssh_keys)

            self.conn.execute(
                "INSERT INTO instances (name, provider, provider_id, plan_id, region_id, image_id, status, ip, ipv6) VALUES (?,?,?,?,?,?,?,?,?)",
                (name, provider_name, result["provider_id"], plan_id, region_id, image_id,
                 result.get("status", "provisioning"), result.get("ip", ""), result.get("ipv6", ""))
            )
            self.conn.commit()
            audit(self.conn, "instance_created", f"{name} on {PROVIDERS[provider_name].display} ({result.get('provider_id','')})")
        except ProviderError as e:
            content = f'<div class="alert alert-error">Failed to create instance: {html.escape(str(e)[:300])}</div><a href="/instances/new" class="btn btn-secondary">Back</a>'
            self._send(200, page_layout("Error", content, "instances"))
            return

        self._redirect("/instances")

    def _handle_instance_action(self):
        form = self._parse_form()
        inst_id = form.get("id", "")
        action = form.get("action", "")
        inst = self.conn.execute("SELECT * FROM instances WHERE id=?", (inst_id,)).fetchone()
        if not inst:
            self._redirect("/instances")
            return

        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (inst["provider"],)).fetchone()
        if row:
            try:
                prov = get_provider(inst["provider"], row["api_key"])
                prov.power_action(inst["provider_id"], action)
                audit(self.conn, f"instance_{action}", f"{inst['name']}")
            except ProviderError:
                pass
        self._redirect("/instances")

    def _handle_destroy_instance(self):
        form = self._parse_form()
        inst_id = form.get("id", "")
        inst = self.conn.execute("SELECT * FROM instances WHERE id=?", (inst_id,)).fetchone()
        if not inst:
            self._redirect("/instances")
            return

        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (inst["provider"],)).fetchone()
        if row:
            try:
                prov = get_provider(inst["provider"], row["api_key"])
                prov.destroy_instance(inst["provider_id"])
            except ProviderError:
                pass

        self.conn.execute("UPDATE instances SET destroyed_at=datetime('now'), status='destroyed' WHERE id=?", (inst_id,))
        self.conn.commit()
        audit(self.conn, "instance_destroyed", f"{inst['name']} on {inst['provider']}")
        self._redirect("/instances")

    def _handle_create_snapshot(self):
        form = self._parse_form()
        inst_id = form.get("instance_id", "")
        description = form.get("description", "")
        inst = self.conn.execute("SELECT * FROM instances WHERE id=?", (inst_id,)).fetchone()
        if not inst:
            self._redirect("/snapshots")
            return

        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (inst["provider"],)).fetchone()
        if row:
            try:
                prov = get_provider(inst["provider"], row["api_key"])
                prov.create_snapshot(inst["provider_id"], description)
                audit(self.conn, "snapshot_created", f"for {inst['name']}: {description}")
            except ProviderError:
                pass
        self._redirect("/snapshots")

    def _handle_delete_snapshot(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        snapshot_id = form.get("snapshot_id", "")
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.delete_snapshot(snapshot_id)
                audit(self.conn, "snapshot_deleted", f"{provider}:{snapshot_id}")
            except ProviderError:
                pass
        self._redirect("/snapshots")

    def _handle_create_firewall(self):
        form = self._parse_form()
        name = form.get("name", "").strip()
        provider = form.get("provider", "")
        rules_text = form.get("rules", "")
        rules = []
        for line in rules_text.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) >= 2:
                rules.append({
                    "protocol": parts[0].strip(),
                    "port": parts[1].strip(),
                    "source_ips": [parts[2].strip()] if len(parts) > 2 else ["0.0.0.0/0", "::/0"]
                })

        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row and rules:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.create_firewall(name, rules)
                audit(self.conn, "firewall_created", f"{name} on {provider}")
            except ProviderError:
                pass
        self._redirect("/firewalls")

    def _handle_delete_firewall(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        firewall_id = form.get("firewall_id", "")
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.delete_firewall(firewall_id)
                audit(self.conn, "firewall_deleted", f"{provider}:{firewall_id}")
            except ProviderError:
                pass
        self._redirect("/firewalls")

    def _handle_add_ssh_key(self):
        form = self._parse_form()
        name = form.get("name", "").strip()
        provider = form.get("provider", "")
        public_key = form.get("public_key", "").strip()
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row and name and public_key:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.add_ssh_key(name, public_key)
                audit(self.conn, "ssh_key_added", f"{name} on {provider}")
            except ProviderError:
                pass
        self._redirect("/ssh-keys")

    def _handle_delete_ssh_key(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        key_id = form.get("key_id", "")
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.delete_ssh_key(key_id)
                audit(self.conn, "ssh_key_deleted", f"{provider}:{key_id}")
            except ProviderError:
                pass
        self._redirect("/ssh-keys")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import html as html_mod
    global html
    html = html_mod

    conn = init_db()
    _get_session_secret()

    VPSHandler.conn = conn

    ip = "0.0.0.0"
    # Try to get actual IP for display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        display_ip = s.getsockname()[0]
        s.close()
    except Exception:
        display_ip = "localhost"

    print("", flush=True)
    print("  ╔══════════════════════════════════════════════╗", flush=True)
    print("  ║     🍀 CloverVPS Manager                    ║", flush=True)
    print("  ║                                              ║", flush=True)
    print("  ║  White-label VPS management for mycloverOS  ║", flush=True)
    url = f"http://{display_ip}:{PORT}"
    print(f"  ║  → {url:<35s}  ║", flush=True)
    print("  ║                                              ║", flush=True)
    print("  ╚══════════════════════════════════════════════╝", flush=True)
    print("", flush=True)

    server = http.server.HTTPServer((ip, PORT), VPSHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    conn.close()
    print("[CloverVPS] Server stopped.", flush=True)


if __name__ == "__main__":
    main()
