#!/usr/bin/env python3
"""
CloverVPS Manager — White-label VPS reseller platform for mycloverOS.

Supports: Hetzner, DigitalOcean, Vultr, Linode/Akamai
Features: Full lifecycle, DNS management, billing/invoicing, custom plan pricing
Model:    Reseller — admin configures provider keys, sets markup, end users see CloverCloud branding

Runs on port 8081. Pure Python 3 stdlib + urllib (no pip dependencies).
"""

import http.server
import html as html_mod
import json
import os
import sqlite3
import socket
import time
import urllib.request
import urllib.parse
import urllib.error
import hashlib
import secrets
import threading
import re
import textwrap
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

html = html_mod

# ─── Configuration ───────────────────────────────────────────────────────────

PORT = 8081
DATA_DIR = "/etc/myclover/clover-vps"
DB_PATH = os.path.join(DATA_DIR, "clover-vps.db")
SESSION_SECRET = None

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
        body_text = e.read().decode("utf-8", errors="replace")
        raise ProviderError(f"HTTP {e.code}: {body_text[:500]}")
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
                "id": str(st["id"]), "name": st["name"], "description": st["description"],
                "vcpus": st["cores"], "ram_mb": st["memory"] * 1024, "disk_gb": st["disk"],
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
        payload = {"name": name, "server_type": plan_id, "location": region_id,
                   "image": image_id, "start_after_create": True}
        if ssh_keys:
            payload["ssh_keys"] = ssh_keys
        r = self._post("/servers", payload)
        srv = r.get("server", {})
        return {"provider_id": str(srv.get("id", "")), "name": srv.get("name", name),
                "status": srv.get("status", "unknown"),
                "ip": srv.get("public_net", {}).get("ipv4", {}).get("ip", ""),
                "ipv6": srv.get("public_net", {}).get("ipv6", {}).get("ip", "")}

    def destroy_instance(self, provider_id):
        self._delete(f"/servers/{provider_id}")
        return True

    def get_instance(self, provider_id):
        r = self._get(f"/servers/{provider_id}")
        srv = r.get("server", {})
        return {"provider_id": str(srv["id"]), "name": srv["name"], "status": srv["status"],
                "ip": srv.get("public_net", {}).get("ipv4", {}).get("ip", ""),
                "vcpus": srv.get("server_type", {}).get("cores", 0),
                "ram_mb": int(srv.get("server_type", {}).get("memory", 0) * 1024),
                "disk_gb": srv.get("server_type", {}).get("disk", 0),
                "created": srv.get("created", "")}

    def list_instances(self):
        r = self._get("/servers?per_page=50")
        return [{"provider_id": str(s["id"]), "name": s["name"], "status": s["status"],
                 "ip": s.get("public_net", {}).get("ipv4", {}).get("ip", "")}
                for s in r.get("servers", [])]

    def power_action(self, provider_id, action):
        self._post(f"/servers/{provider_id}/actions/{action}", {})
        return True

    def resize_instance(self, provider_id, new_plan_id):
        self._post(f"/servers/{provider_id}/actions/change_type",
                   {"server_type": new_plan_id, "upgrade_disk": True})
        return True

    def create_snapshot(self, provider_id, description=""):
        r = self._post(f"/servers/{provider_id}/actions/create_image",
                       {"description": description or f"snapshot-{int(time.time())}", "type": "snapshot"})
        return {"id": str(r.get("image", {}).get("id", "")), "status": "creating"}

    def list_snapshots(self):
        r = self._get("/images?type=snapshot&per_page=50")
        return [{"id": str(i["id"]), "name": i.get("description", ""),
                 "size_gb": i.get("image_size", 0), "created": i.get("created", "")}
                for i in r.get("images", [])]

    def delete_snapshot(self, snapshot_id):
        self._delete(f"/images/{snapshot_id}")
        return True

    def list_firewalls(self):
        r = self._get("/firewalls?per_page=50")
        return [{"id": str(f["id"]), "name": f["name"],
                 "rules_count": len(f.get("rules", []))} for f in r.get("firewalls", [])]

    def create_firewall(self, name, rules):
        fw_rules = []
        for rule in rules:
            fw_rules.append({"direction": rule.get("direction", "in"),
                             "protocol": rule.get("protocol", "tcp"),
                             "port": rule.get("port", "22"),
                             "source_ips": rule.get("source_ips", ["0.0.0.0/0", "::/0"])})
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
        m = {"poweron": "power_on", "poweroff": "power_off", "reboot": "reboot", "reset": "power_cycle"}
        self._post(f"/droplets/{provider_id}/actions", {"type": m.get(action, action)})
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
            inbound.append({"protocol": rule.get("protocol", "tcp"), "ports": rule.get("port", "22"),
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

    # DNS
    def list_domains(self):
        r = self._get("/domains?per_page=100")
        return [{"name": d["name"], "ttl": d.get("ttl", 1800)} for d in r.get("domains", [])]

    def add_domain(self, domain, ip=""):
        self._post("/domains", {"name": domain, "ip_address": ip or None})
        return True

    def delete_domain(self, domain):
        self._delete(f"/domains/{domain}")
        return True

    def list_dns_records(self, domain):
        r = self._get(f"/domains/{domain}/records?per_page=200")
        return [{"id": str(rec["id"]), "type": rec["type"], "name": rec["name"],
                 "data": rec["data"], "ttl": rec.get("ttl", 3600)}
                for rec in r.get("domain_records", [])]

    def create_dns_record(self, domain, record_type, name, data, ttl=3600):
        r = self._post(f"/domains/{domain}/records",
                       {"type": record_type, "name": name, "data": data, "ttl": ttl})
        return {"id": str(r.get("domain_record", {}).get("id", ""))}

    def delete_dns_record(self, domain, record_id):
        self._delete(f"/domains/{domain}/records/{record_id}")
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
                "status": inst.get("status", "pending"), "ip": inst.get("main_ip", ""),
                "ipv6": inst.get("v6_main_ip", "")}

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
        m = {"poweron": "start", "poweroff": "halt", "reboot": "reboot", "reset": "reboot"}
        self._post(f"/instances/{provider_id}/{m.get(action, action)}", {})
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
        return [{"id": s["id"], "name": s.get("description", ""),
                 "size_gb": int(s.get("size", 0)) // (1024**3),
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
                "port": rule.get("port", "22"), "subnet": "0.0.0.0", "subnet_size": 0})
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

    # DNS
    def list_domains(self):
        r = self._get("/domains?per_page=100")
        return [{"name": d["domain"], "ttl": 0} for d in r.get("domains", [])]

    def add_domain(self, domain, ip=""):
        self._post("/domains", {"domain": domain, "ip": ip or ""})
        return True

    def delete_domain(self, domain):
        self._delete(f"/domains/{domain}")
        return True

    def list_dns_records(self, domain):
        r = self._get(f"/domains/{domain}/records?per_page=200")
        return [{"id": rec["id"], "type": rec["type"], "name": rec["name"],
                 "data": rec["data"], "ttl": rec.get("ttl", 3600)}
                for rec in r.get("records", [])]

    def create_dns_record(self, domain, record_type, name, data, ttl=3600):
        r = self._post(f"/domains/{domain}/records",
                       {"type": record_type, "name": name, "data": data, "ttl": ttl})
        return {"id": r.get("record", {}).get("id", "")}

    def delete_dns_record(self, domain, record_id):
        self._delete(f"/domains/{domain}/records/{record_id}")
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
        return [{"id": t["id"], "name": t["label"], "description": t["label"],
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
                "status": r.get("status", "provisioning"),
                "ip": ips[0] if ips else "", "ipv6": r.get("ipv6", "")}

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
        m = {"poweron": "boot", "poweroff": "shutdown", "reboot": "reboot", "reset": "reboot"}
        self._post(f"/linode/instances/{provider_id}/{m.get(action, action)}", {})
        return True

    def resize_instance(self, provider_id, new_plan_id):
        self._post(f"/linode/instances/{provider_id}/resize", {"type": new_plan_id})
        return True

    def create_snapshot(self, provider_id, description=""):
        label = description or f"snapshot-{int(time.time())}"
        r = self._post(f"/linode/instances/{provider_id}/backups", {"label": label})
        return {"id": str(r.get("id", "")), "status": "creating"}

    def list_snapshots(self):
        instances = self.list_instances()
        all_snaps = []
        for inst in instances:
            try:
                r = self._get(f"/linode/instances/{inst['provider_id']}/backups")
                snaps = r.get("automatic", [])
                cur = r.get("snapshot", {}).get("current")
                if cur:
                    snaps.append(cur)
                for snap in snaps:
                    if snap:
                        sz = snap.get("disks", [{}])[0].get("size", 0) // 1024 if snap.get("disks") else 0
                        all_snaps.append({"id": str(snap.get("id", "")), "name": snap.get("label", ""),
                                          "size_gb": sz, "created": snap.get("created", "")})
            except ProviderError:
                pass
        return all_snaps

    def delete_snapshot(self, snapshot_id):
        raise ProviderError("Linode manages backup retention automatically")

    def list_firewalls(self):
        r = self._get("/networking/firewalls?page_size=100")
        return [{"id": str(f["id"]), "name": f["label"],
                 "rules_count": len(f.get("rules", {}).get("inbound", []))} for f in r.get("data", [])]

    def create_firewall(self, name, rules):
        inbound = []
        for rule in rules:
            inbound.append({"action": "ACCEPT", "protocol": rule.get("protocol", "TCP").upper(),
                           "ports": rule.get("port", "22"),
                           "addresses": {"ipv4": rule.get("source_ips", ["0.0.0.0/0"]), "ipv6": ["::/0"]}})
        payload = {"label": name, "rules": {
            "inbound": inbound,
            "outbound": [{"action": "ACCEPT", "protocol": "TCP", "ports": "1-65535",
                          "addresses": {"ipv4": ["0.0.0.0/0"], "ipv6": ["::/0"]}}],
            "inbound_policy": "DROP", "outbound_policy": "ACCEPT"}}
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

    # DNS
    def list_domains(self):
        r = self._get("/domains?page_size=100")
        return [{"name": d["domain"], "ttl": d.get("ttl_sec", 0)} for d in r.get("data", [])]

    def add_domain(self, domain, ip=""):
        self._post("/domains", {"domain": domain, "type": "master", "soa_email": f"admin@{domain}"})
        return True

    def delete_domain(self, domain):
        # Need the domain ID
        doms = self._get("/domains?page_size=100")
        for d in doms.get("data", []):
            if d["domain"] == domain:
                self._delete(f"/domains/{d['id']}")
                return True
        raise ProviderError(f"Domain {domain} not found")

    def list_dns_records(self, domain):
        doms = self._get("/domains?page_size=100")
        dom_id = None
        for d in doms.get("data", []):
            if d["domain"] == domain:
                dom_id = d["id"]
                break
        if not dom_id:
            return []
        r = self._get(f"/domains/{dom_id}/records?page_size=200")
        return [{"id": str(rec["id"]), "type": rec["type"], "name": rec["name"],
                 "data": rec.get("target", ""), "ttl": rec.get("ttl_sec", 3600)}
                for rec in r.get("data", [])]

    def create_dns_record(self, domain, record_type, name, data, ttl=3600):
        doms = self._get("/domains?page_size=100")
        dom_id = None
        for d in doms.get("data", []):
            if d["domain"] == domain:
                dom_id = d["id"]
                break
        if not dom_id:
            raise ProviderError(f"Domain {domain} not found")
        r = self._post(f"/domains/{dom_id}/records",
                       {"type": record_type, "name": name, "target": data, "ttl_sec": ttl})
        return {"id": str(r.get("id", ""))}

    def delete_dns_record(self, domain, record_id):
        doms = self._get("/domains?page_size=100")
        dom_id = None
        for d in doms.get("data", []):
            if d["domain"] == domain:
                dom_id = d["id"]
                break
        if not dom_id:
            raise ProviderError(f"Domain {domain} not found")
        self._delete(f"/domains/{dom_id}/records/{record_id}")
        return True


# ── Hetzner DNS (separate API) ──────────────────────────────────────────────

class HetznerDNSMixin:
    """Hetzner uses a separate DNS API at dns.hetzner.com.
    Requires a separate DNS API token (stored as hetzner_dns key)."""
    dns_base = "https://dns.hetzner.com/api/v1"

    def list_domains(self):
        r = _api("GET", f"{self.dns_base}/zones", self.headers)
        return [{"name": z["name"], "ttl": z.get("ttl", 3600)} for z in r.get("zones", [])]

    def add_domain(self, domain, ip=""):
        _api("POST", f"{self.dns_base}/zones", self.headers, {"name": domain, "ttl": 3600})
        return True

    def delete_domain(self, domain):
        zones = _api("GET", f"{self.dns_base}/zones?name={domain}", self.headers)
        for z in zones.get("zones", []):
            if z["name"] == domain:
                _api("DELETE", f"{self.dns_base}/zones/{z['id']}", self.headers)
                return True
        raise ProviderError(f"Domain {domain} not found")

    def list_dns_records(self, domain):
        zones = _api("GET", f"{self.dns_base}/zones?name={domain}", self.headers)
        zone_id = None
        for z in zones.get("zones", []):
            if z["name"] == domain:
                zone_id = z["id"]
                break
        if not zone_id:
            return []
        r = _api("GET", f"{self.dns_base}/records?zone_id={zone_id}", self.headers)
        return [{"id": rec["id"], "type": rec["type"], "name": rec["name"],
                 "data": rec["value"], "ttl": rec.get("ttl", 3600)}
                for rec in r.get("records", [])]

    def create_dns_record(self, domain, record_type, name, data, ttl=3600):
        zones = _api("GET", f"{self.dns_base}/zones?name={domain}", self.headers)
        zone_id = None
        for z in zones.get("zones", []):
            if z["name"] == domain:
                zone_id = z["id"]
                break
        if not zone_id:
            raise ProviderError(f"Domain {domain} not found")
        r = _api("POST", f"{self.dns_base}/records", self.headers,
                 {"zone_id": zone_id, "type": record_type, "name": name, "value": data, "ttl": ttl})
        return {"id": r.get("record", {}).get("id", "")}

    def delete_dns_record(self, domain, record_id):
        _api("DELETE", f"{self.dns_base}/records/{record_id}", self.headers)
        return True

# Apply DNS mixin to Hetzner
for method_name in ['list_domains', 'add_domain', 'delete_domain', 'list_dns_records',
                     'create_dns_record', 'delete_dns_record']:
    setattr(HetznerProvider, method_name, getattr(HetznerDNSMixin, method_name))


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
            notes TEXT DEFAULT '',
            custom_plan_id INTEGER DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS custom_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_plan_id TEXT NOT NULL,
            cost_price REAL DEFAULT 0,
            sell_price REAL DEFAULT 0,
            markup_pct REAL DEFAULT 20,
            currency TEXT DEFAULT 'USD',
            active INTEGER DEFAULT 1,
            vcpus INTEGER DEFAULT 0,
            ram_mb INTEGER DEFAULT 0,
            disk_gb INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
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

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            customer_email TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            subtotal REAL DEFAULT 0,
            tax_rate REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            total REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            due_date TEXT,
            paid_date TEXT,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            unit_price REAL DEFAULT 0,
            total REAL DEFAULT 0,
            instance_id INTEGER,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS billing_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dns_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            domain TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # Seed default billing settings
    defaults = {
        "company_name": "CloverVPS",
        "company_email": "",
        "company_address": "",
        "default_tax_rate": "0",
        "default_currency": "USD",
        "invoice_prefix": "CVPS",
        "invoice_next_number": "1001",
        "payment_terms": "Net 30",
        "payment_instructions": "Please pay via bank transfer or PayPal.",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO billing_settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    return conn


def audit(conn, action, detail=""):
    conn.execute("INSERT INTO audit_log (action, detail) VALUES (?, ?)", (action, detail))
    conn.commit()


def get_setting(conn, key, default=""):
    row = conn.execute("SELECT value FROM billing_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO billing_settings (key, value) VALUES (?, ?)", (key, str(value)))
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
    conn.execute("INSERT INTO sessions (token, expires_at) VALUES (?, datetime('now', '+24 hours'))", (token,))
    conn.commit()
    return token


def verify_session(conn, token):
    if not token:
        return False
    row = conn.execute("SELECT * FROM sessions WHERE token = ? AND expires_at > datetime('now')",
                       (token,)).fetchone()
    return row is not None


# ─── CSS / Layout ────────────────────────────────────────────────────────────

BRAND_CSS = """
:root {
    --bg: #0f1117; --surface: #1a1d27; --surface2: #242836;
    --border: #2d3348; --text: #e4e6f0; --text-dim: #8b8fa3;
    --green: #4ade80; --green-dim: #166534; --red: #f87171;
    --blue: #60a5fa; --yellow: #fbbf24; --purple: #a78bfa;
    --orange: #fb923c;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.6; }
.container { max-width: 1280px; margin: 0 auto; padding: 24px; }
h1, h2, h3 { font-weight: 600; }
a { color: var(--green); text-decoration: none; }
a:hover { text-decoration: underline; }

.navbar { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 24px; display: flex; align-items: center; height: 56px; position: sticky; top: 0; z-index: 100; }
.navbar .brand { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; color: var(--green); white-space: nowrap; }
.navbar .brand span { color: var(--text-dim); font-weight: 400; font-size: 12px; }
.navbar nav { margin-left: 32px; display: flex; gap: 2px; flex-wrap: nowrap; overflow-x: auto; }
.navbar nav a { color: var(--text-dim); padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 500; white-space: nowrap; }
.navbar nav a:hover, .navbar nav a.active { color: var(--text); background: var(--surface2); text-decoration: none; }
.navbar .right { margin-left: auto; white-space: nowrap; }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.card h2 { font-size: 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.card h3 { font-size: 14px; margin-bottom: 12px; color: var(--text-dim); }

table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); padding: 10px 12px; border-bottom: 1px solid var(--border); }
td { padding: 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
tr:hover { background: var(--surface2); }

.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s; text-decoration: none; }
.btn-primary { background: var(--green); color: #000; }
.btn-primary:hover { background: #22c55e; }
.btn-danger { background: var(--red); color: #fff; }
.btn-danger:hover { background: #ef4444; }
.btn-secondary { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--border); }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-purple { background: var(--purple); color: #fff; }
.btn-purple:hover { background: #8b5cf6; }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 12px; font-weight: 500; color: var(--text-dim); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
input, select, textarea { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 14px; font-family: inherit; }
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--green); }
input[type="number"] { -moz-appearance: textfield; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 100px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
.badge-running { background: var(--green-dim); color: var(--green); }
.badge-stopped { background: #3f1d1d; color: var(--red); }
.badge-pending { background: #422006; color: var(--yellow); }
.badge-paid { background: var(--green-dim); color: var(--green); }
.badge-draft { background: #1e293b; color: var(--text-dim); }
.badge-sent { background: #1e3a5f; color: var(--blue); }
.badge-overdue { background: #3f1d1d; color: var(--red); }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat { text-align: center; padding: 20px; }
.stat .value { font-size: 28px; font-weight: 700; color: var(--green); }
.stat .label { font-size: 12px; color: var(--text-dim); margin-top: 4px; }

.alert { padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
.alert-info { background: #1e3a5f; border: 1px solid #2563eb; color: var(--blue); }
.alert-success { background: #14532d; border: 1px solid var(--green); color: var(--green); }
.alert-error { background: #3f1d1d; border: 1px solid var(--red); color: var(--red); }
.alert-warning { background: #422006; border: 1px solid var(--yellow); color: var(--yellow); }

.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 0; }
.tab { padding: 10px 20px; color: var(--text-dim); cursor: pointer; border-bottom: 2px solid transparent; font-size: 13px; font-weight: 500; }
.tab:hover { color: var(--text); }
.tab.active { color: var(--green); border-bottom-color: var(--green); }

.money { font-family: 'SF Mono', 'Fira Code', monospace; }
.money-positive { color: var(--green); }
.money-neutral { color: var(--text-dim); }

@media (max-width: 768px) {
    .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
    .navbar { flex-wrap: wrap; height: auto; padding: 8px 16px; }
    .navbar nav { margin-left: 0; width: 100%; overflow-x: auto; }
}
"""

def page_layout(title, content, active="dashboard"):
    nav_items = [
        ("dashboard", "Dashboard", "/"),
        ("instances", "Instances", "/instances"),
        ("dns", "DNS", "/dns"),
        ("snapshots", "Snapshots", "/snapshots"),
        ("firewalls", "Firewalls", "/firewalls"),
        ("ssh-keys", "SSH Keys", "/ssh-keys"),
        ("plans", "Plans & Pricing", "/plans"),
        ("invoices", "Invoices", "/invoices"),
        ("billing", "Billing Settings", "/billing"),
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
        <div class="brand">🍀 CloverVPS <span>v0.2.0</span></div>
        <nav>{nav_html}</nav>
        <div class="right"><a href="/logout" class="btn btn-secondary btn-sm">Logout</a></div>
    </div>
    <div class="container">{content}</div>
</body>
</html>"""


def login_page(error=""):
    err_html = f'<div class="alert alert-error">{html.escape(error)}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login — CloverVPS</title><style>{BRAND_CSS}
.login-box {{ max-width: 400px; margin: 120px auto; }}
.login-box h1 {{ text-align: center; margin-bottom: 8px; color: var(--green); }}
.login-box p {{ text-align: center; color: var(--text-dim); margin-bottom: 24px; }}
</style></head><body>
<div class="login-box"><h1>🍀 CloverVPS</h1><p>White-label VPS Management</p>
<div class="card">{err_html}
<form method="POST" action="/login"><div class="form-group"><label>Admin Password</label>
<input type="password" name="password" autofocus required placeholder="Enter admin password"></div>
<button type="submit" class="btn btn-primary" style="width:100%">Sign In</button></form>
<p style="margin-top:16px;font-size:12px;color:var(--text-dim);text-align:center">
Default password is set during mycloverOS first-boot setup.</p></div></div>
</body></html>"""


# ─── Invoice PDF Generator (pure Python, no deps) ───────────────────────────

def generate_invoice_html(conn, invoice_id):
    """Generate a printable HTML invoice."""
    inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not inv:
        return "<p>Invoice not found</p>"
    items = conn.execute("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (invoice_id,)).fetchall()

    company = get_setting(conn, "company_name", "CloverVPS")
    company_email = get_setting(conn, "company_email")
    company_addr = get_setting(conn, "company_address")
    payment_terms = get_setting(conn, "payment_terms", "Net 30")
    payment_instr = get_setting(conn, "payment_instructions")

    item_rows = ""
    for item in items:
        item_rows += f"""<tr>
            <td style="padding:10px 12px;border-bottom:1px solid #2d3348">{html.escape(item['description'])}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #2d3348;text-align:right">{item['quantity']:.0f}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #2d3348;text-align:right">{inv['currency']} {item['unit_price']:.2f}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #2d3348;text-align:right">{inv['currency']} {item['total']:.2f}</td>
        </tr>"""

    status_color = {"paid": "#4ade80", "sent": "#60a5fa", "overdue": "#f87171"}.get(inv["status"], "#8b8fa3")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Invoice {inv['invoice_number']}</title>
<style>
@media print {{ body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
body {{ background: #0f1117; color: #e4e6f0; font-family: -apple-system, sans-serif; margin: 0; padding: 40px; }}
.invoice {{ max-width: 800px; margin: 0 auto; background: #1a1d27; border-radius: 16px; padding: 40px; border: 1px solid #2d3348; }}
</style></head><body>
<div class="invoice">
    <div style="display:flex;justify-content:space-between;margin-bottom:40px">
        <div>
            <h1 style="color:#4ade80;font-size:28px;margin-bottom:4px">🍀 {html.escape(company)}</h1>
            <p style="color:#8b8fa3;font-size:13px">{html.escape(company_email)}</p>
            <p style="color:#8b8fa3;font-size:13px;white-space:pre-line">{html.escape(company_addr)}</p>
        </div>
        <div style="text-align:right">
            <h2 style="font-size:24px;margin-bottom:8px">INVOICE</h2>
            <p style="font-size:16px;font-weight:600">{html.escape(inv['invoice_number'])}</p>
            <p style="background:{status_color};color:#000;display:inline-block;padding:2px 10px;border-radius:100px;font-size:11px;font-weight:600;text-transform:uppercase;margin-top:8px">{inv['status']}</p>
        </div>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:32px;padding:20px;background:#242836;border-radius:10px">
        <div><p style="color:#8b8fa3;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">Bill To</p>
            <p style="font-weight:600;font-size:16px">{html.escape(inv['customer_name'])}</p>
            <p style="color:#8b8fa3">{html.escape(inv['customer_email'])}</p></div>
        <div style="text-align:right"><p style="color:#8b8fa3;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">Date Issued</p>
            <p>{inv['created_at']}</p>
            <p style="color:#8b8fa3;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-top:12px;margin-bottom:4px">Due Date</p>
            <p>{inv['due_date'] or 'N/A'}</p></div>
    </div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
        <tr style="border-bottom:2px solid #2d3348">
            <th style="text-align:left;padding:10px 12px;color:#8b8fa3;font-size:11px;text-transform:uppercase">Description</th>
            <th style="text-align:right;padding:10px 12px;color:#8b8fa3;font-size:11px;text-transform:uppercase">Qty</th>
            <th style="text-align:right;padding:10px 12px;color:#8b8fa3;font-size:11px;text-transform:uppercase">Unit Price</th>
            <th style="text-align:right;padding:10px 12px;color:#8b8fa3;font-size:11px;text-transform:uppercase">Total</th>
        </tr>
        {item_rows}
    </table>
    <div style="display:flex;justify-content:flex-end">
        <div style="width:280px">
            <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2d3348">
                <span style="color:#8b8fa3">Subtotal</span><span>{inv['currency']} {inv['subtotal']:.2f}</span></div>
            <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2d3348">
                <span style="color:#8b8fa3">Tax ({inv['tax_rate']:.1f}%)</span><span>{inv['currency']} {inv['tax_amount']:.2f}</span></div>
            <div style="display:flex;justify-content:space-between;padding:12px 0;font-size:18px;font-weight:700">
                <span>Total</span><span style="color:#4ade80">{inv['currency']} {inv['total']:.2f}</span></div>
        </div>
    </div>
    {'<div style="margin-top:32px;padding:16px;background:#242836;border-radius:10px"><p style="color:#8b8fa3;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px">Payment Terms</p><p>' + html.escape(payment_terms) + '</p></div>' if payment_terms else ''}
    {'<div style="margin-top:12px;padding:16px;background:#242836;border-radius:10px"><p style="color:#8b8fa3;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px">Payment Instructions</p><p style="white-space:pre-line">' + html.escape(payment_instr) + '</p></div>' if payment_instr else ''}
    {('<div style="margin-top:12px;padding:16px;background:#242836;border-radius:10px"><p style="color:#8b8fa3;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px">Notes</p><p style="white-space:pre-line">' + html.escape(inv["notes"]) + '</p></div>') if inv["notes"] else ''}
</div></body></html>"""


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

    def _get_providers(self):
        rows = self.conn.execute("SELECT provider, api_key FROM provider_keys WHERE enabled=1").fetchall()
        result = {}
        for row in rows:
            try:
                result[row["provider"]] = get_provider(row["provider"], row["api_key"])
            except Exception:
                pass
        return result

    # ── Routing ──

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        qs = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))

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

        routes = {
            "/": self._page_dashboard,
            "/dashboard": self._page_dashboard,
            "/instances": self._page_instances,
            "/instances/new": self._page_new_instance,
            "/dns": self._page_dns,
            "/dns/records": lambda: self._page_dns_records(qs),
            "/snapshots": self._page_snapshots,
            "/firewalls": self._page_firewalls,
            "/firewalls/new": self._page_new_firewall,
            "/ssh-keys": self._page_ssh_keys,
            "/plans": self._page_plans,
            "/plans/new": self._page_new_plan,
            "/plans/import": self._page_import_plans,
            "/invoices": self._page_invoices,
            "/invoices/new": self._page_new_invoice,
            "/invoices/view": lambda: self._page_view_invoice(qs),
            "/invoices/print": lambda: self._page_print_invoice(qs),
            "/billing": self._page_billing_settings,
            "/providers": self._page_providers,
            "/audit": self._page_audit,
        }

        handler = routes.get(path)
        if handler:
            handler()
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

        post_routes = {
            "/providers/save": self._handle_save_provider,
            "/providers/delete": self._handle_delete_provider,
            "/instances/create": self._handle_create_instance,
            "/instances/action": self._handle_instance_action,
            "/instances/destroy": self._handle_destroy_instance,
            "/snapshots/create": self._handle_create_snapshot,
            "/snapshots/delete": self._handle_delete_snapshot,
            "/firewalls/create": self._handle_create_firewall,
            "/firewalls/delete": self._handle_delete_firewall,
            "/ssh-keys/add": self._handle_add_ssh_key,
            "/ssh-keys/delete": self._handle_delete_ssh_key,
            "/dns/add-domain": self._handle_add_domain,
            "/dns/delete-domain": self._handle_delete_domain,
            "/dns/add-record": self._handle_add_record,
            "/dns/delete-record": self._handle_delete_record,
            "/plans/create": self._handle_create_plan,
            "/plans/delete": self._handle_delete_plan,
            "/plans/toggle": self._handle_toggle_plan,
            "/plans/import-save": self._handle_import_plans,
            "/invoices/create": self._handle_create_invoice,
            "/invoices/update-status": self._handle_update_invoice_status,
            "/invoices/delete": self._handle_delete_invoice,
            "/invoices/generate": self._handle_generate_invoice,
            "/billing/save": self._handle_save_billing,
        }

        handler = post_routes.get(path)
        if handler:
            handler()
        else:
            self._send(404, "Not found")

    # ── Login ──

    def _handle_login(self):
        form = self._parse_form()
        password = form.get("password", "")
        admin_hash_path = os.path.join(DATA_DIR, ".admin_hash")
        if os.path.exists(admin_hash_path):
            with open(admin_hash_path) as f:
                stored = f.read().strip()
            check = hashlib.sha256(password.encode()).hexdigest()
            if check != stored:
                self._send(200, login_page("Invalid password"))
                return
        else:
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
        providers = self._get_providers()
        total_instances = self.conn.execute("SELECT COUNT(*) FROM instances WHERE destroyed_at IS NULL").fetchone()[0]
        by_provider = self.conn.execute(
            "SELECT provider, COUNT(*) as cnt FROM instances WHERE destroyed_at IS NULL GROUP BY provider"
        ).fetchall()

        # Revenue stats
        total_revenue = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status='paid'"
        ).fetchone()[0]
        outstanding = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status IN ('sent', 'overdue')"
        ).fetchone()[0]
        invoice_count = self.conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        currency = get_setting(self.conn, "default_currency", "USD")

        # Monthly revenue (this month)
        month_start = datetime.now().strftime("%Y-%m-01")
        monthly_rev = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status='paid' AND paid_date >= ?",
            (month_start,)
        ).fetchone()[0]

        # Profit calculation from custom plans
        total_cost = 0
        total_sell = 0
        active_plans = self.conn.execute("SELECT * FROM custom_plans WHERE active=1").fetchall()
        plan_instances = self.conn.execute(
            "SELECT custom_plan_id, COUNT(*) as cnt FROM instances WHERE destroyed_at IS NULL AND custom_plan_id IS NOT NULL GROUP BY custom_plan_id"
        ).fetchall()
        plan_inst_map = {r["custom_plan_id"]: r["cnt"] for r in plan_instances}
        for plan in active_plans:
            cnt = plan_inst_map.get(plan["id"], 0)
            total_cost += plan["cost_price"] * cnt
            total_sell += plan["sell_price"] * cnt

        profit = total_sell - total_cost

        provider_stats = ""
        for row in by_provider:
            p_name = PROVIDERS.get(row["provider"], type("", (), {"display": row["provider"]})).display
            provider_stats += f'<div class="stat"><div class="value">{row["cnt"]}</div><div class="label">{p_name}</div></div>'

        recent_audit = self.conn.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10").fetchall()
        audit_rows = ""
        for row in recent_audit:
            audit_rows += f'<tr><td style="color:var(--text-dim)">{row["ts"]}</td><td>{html.escape(row["action"])}</td><td>{html.escape(row["detail"])}</td></tr>'

        content = f"""
        <h1 style="margin-bottom:24px">Dashboard</h1>
        <div class="grid-4">
            <div class="card stat"><div class="value">{total_instances}</div><div class="label">Active Instances</div></div>
            <div class="card stat"><div class="value money money-positive">{currency} {total_revenue:,.2f}</div><div class="label">Total Revenue (Paid)</div></div>
            <div class="card stat"><div class="value money" style="color:var(--yellow)">{currency} {outstanding:,.2f}</div><div class="label">Outstanding</div></div>
            <div class="card stat"><div class="value money {'money-positive' if profit >= 0 else ''}" style="{'color:var(--red)' if profit < 0 else ''}">{currency} {profit:,.2f}</div><div class="label">Est. Monthly Margin</div></div>
        </div>
        <div class="grid-4">
            <div class="card stat"><div class="value">{len(providers)}</div><div class="label">Providers Connected</div></div>
            <div class="card stat"><div class="value">{invoice_count}</div><div class="label">Total Invoices</div></div>
            <div class="card stat"><div class="value money money-positive">{currency} {monthly_rev:,.2f}</div><div class="label">This Month Revenue</div></div>
            {provider_stats or '<div class="card stat"><div class="value">—</div><div class="label">No Instances Yet</div></div>'}
        </div>
        {'<div class="alert alert-warning">⚠️ No providers configured yet. <a href="/providers">Add a provider API key</a> to get started.</div>' if not providers else ''}
        <div class="card">
            <h2>📋 Recent Activity</h2>
            <table><tr><th>Time</th><th>Action</th><th>Detail</th></tr>
                {audit_rows or '<tr><td colspan="3" style="color:var(--text-dim)">No activity yet</td></tr>'}
            </table>
        </div>"""
        self._send(200, page_layout("Dashboard", content, "dashboard"))

    # ── Instances ──

    def _page_instances(self):
        instances = self.conn.execute(
            "SELECT i.*, cp.display_name as plan_name, cp.sell_price as plan_price, cp.currency as plan_currency "
            "FROM instances i LEFT JOIN custom_plans cp ON i.custom_plan_id = cp.id "
            "WHERE i.destroyed_at IS NULL ORDER BY i.created_at DESC"
        ).fetchall()

        rows = ""
        for inst in instances:
            status_cls = "badge-running" if inst["status"] in ("running", "active") else \
                         "badge-stopped" if inst["status"] in ("off", "stopped") else "badge-pending"
            p_display = PROVIDERS.get(inst["provider"], type("", (), {"display": inst["provider"]})).display
            plan_info = f'{inst["plan_name"]} (${inst["plan_price"]:.2f}/mo)' if inst["plan_name"] else inst["plan_id"] or "—"
            rows += f"""<tr>
                <td><strong>{html.escape(inst['name'])}</strong></td>
                <td>{p_display}</td>
                <td><code>{inst['ip'] or '—'}</code></td>
                <td><span class="badge {status_cls}">{inst['status']}</span></td>
                <td>{plan_info}</td>
                <td>{inst['created_at']}</td>
                <td>
                    <form method="POST" action="/instances/action" style="display:inline">
                        <input type="hidden" name="id" value="{inst['id']}"><input type="hidden" name="action" value="reboot">
                        <button class="btn btn-secondary btn-sm" title="Reboot">⟳</button></form>
                    <form method="POST" action="/instances/destroy" style="display:inline"
                          onsubmit="return confirm('Destroy {html.escape(inst['name'])}? This cannot be undone.')">
                        <input type="hidden" name="id" value="{inst['id']}">
                        <button class="btn btn-danger btn-sm">Destroy</button></form>
                </td></tr>"""

        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h1>Instances</h1>
            <a href="/instances/new" class="btn btn-primary">+ New Instance</a>
        </div>
        <div class="card"><table>
            <tr><th>Name</th><th>Provider</th><th>IP Address</th><th>Status</th><th>Plan</th><th>Created</th><th>Actions</th></tr>
            {rows or '<tr><td colspan="7" style="color:var(--text-dim);text-align:center;padding:40px">No instances yet. <a href="/instances/new">Create your first instance</a></td></tr>'}
        </table></div>"""
        self._send(200, page_layout("Instances", content, "instances"))

    def _page_new_instance(self):
        providers = self._get_providers()
        if not providers:
            self._send(200, page_layout("New Instance",
                '<div class="alert alert-warning">No providers configured. <a href="/providers">Add a provider</a> first.</div>', "instances"))
            return

        # Custom plans for selection
        custom_plans = self.conn.execute("SELECT * FROM custom_plans WHERE active=1 ORDER BY provider, sell_price").fetchall()
        plan_opts = '<option value="">— Use provider plan directly —</option>'
        for cp in custom_plans:
            plan_opts += f'<option value="{cp["id"]}" data-provider="{cp["provider"]}" data-plan="{cp["provider_plan_id"]}">{html.escape(cp["display_name"])} — {cp["currency"]} {cp["sell_price"]:.2f}/mo ({PROVIDERS[cp["provider"]].display})</option>'

        provider_options = "".join(f'<option value="{name}">{PROVIDERS[name].display}</option>' for name in providers)

        content = f"""
        <h1 style="margin-bottom:24px">Create Instance</h1>
        <div class="card">
            <form method="POST" action="/instances/create" id="createForm">
                <div class="form-group">
                    <label>Custom Plan (optional — auto-selects provider &amp; plan)</label>
                    <select name="custom_plan_id" id="customPlanSelect" onchange="onCustomPlan()">{plan_opts}</select>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label>Instance Name</label>
                        <input type="text" name="name" required placeholder="my-server-01" pattern="[a-zA-Z0-9][a-zA-Z0-9\\-]*"></div>
                    <div class="form-group"><label>Provider</label>
                        <select name="provider" id="providerSelect" onchange="loadOptions()">{provider_options}</select></div>
                </div>
                <div class="grid-3">
                    <div class="form-group"><label>Region</label><select name="region_id" id="regionSelect"><option>Loading...</option></select></div>
                    <div class="form-group"><label>Plan</label><select name="plan_id" id="planSelect"><option>Loading...</option></select></div>
                    <div class="form-group"><label>Image / OS</label><select name="image_id" id="imageSelect"><option>Loading...</option></select></div>
                </div>
                <div class="form-group"><label>SSH Key (optional)</label><select name="ssh_key_id" id="sshKeySelect"><option value="">None</option></select></div>
                <div style="display:flex;gap:8px;margin-top:8px">
                    <button type="submit" class="btn btn-primary">Create Instance</button>
                    <a href="/instances" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
        <script>
        async function loadOptions() {{
            const prov = document.getElementById('providerSelect').value;
            const [regions, plans, images, keys] = await Promise.all([
                fetch('/api/providers/'+prov+'/regions').then(r=>r.json()),
                fetch('/api/providers/'+prov+'/plans').then(r=>r.json()),
                fetch('/api/providers/'+prov+'/images').then(r=>r.json()),
                fetch('/api/providers/'+prov+'/ssh-keys').then(r=>r.json())
            ]);
            document.getElementById('regionSelect').innerHTML = regions.map(r=>'<option value="'+r.id+'">'+r.name+(r.city?' ('+r.city+')':'')+'</option>').join('');
            document.getElementById('planSelect').innerHTML = plans.map(p=>'<option value="'+p.id+'">'+p.name+' — '+p.vcpus+'vCPU / '+Math.round(p.ram_mb/1024)+'GB / '+p.disk_gb+'GB — $'+p.price_monthly+'/mo</option>').join('');
            document.getElementById('imageSelect').innerHTML = images.map(i=>'<option value="'+i.id+'">'+i.name+'</option>').join('');
            document.getElementById('sshKeySelect').innerHTML = '<option value="">None</option>'+keys.map(k=>'<option value="'+k.id+'">'+k.name+'</option>').join('');
        }}
        function onCustomPlan() {{
            const sel = document.getElementById('customPlanSelect');
            const opt = sel.options[sel.selectedIndex];
            if (opt.dataset.provider) {{
                document.getElementById('providerSelect').value = opt.dataset.provider;
                loadOptions().then(()=>{{ if(opt.dataset.plan) document.getElementById('planSelect').value = opt.dataset.plan; }});
            }}
        }}
        loadOptions();
        </script>"""
        self._send(200, page_layout("New Instance", content, "instances"))

    # ── DNS Management ──

    def _page_dns(self):
        providers = self._get_providers()
        zones = self.conn.execute("SELECT * FROM dns_zones ORDER BY domain").fetchall()

        zone_rows = ""
        for z in zones:
            p_display = PROVIDERS.get(z["provider"], type("", (), {"display": z["provider"]})).display
            zone_rows += f"""<tr>
                <td><a href="/dns/records?provider={z['provider']}&domain={urllib.parse.quote(z['domain'])}"><strong>{html.escape(z['domain'])}</strong></a></td>
                <td>{p_display}</td>
                <td>{z['created_at']}</td>
                <td>
                    <a href="/dns/records?provider={z['provider']}&domain={urllib.parse.quote(z['domain'])}" class="btn btn-secondary btn-sm">Records</a>
                    <form method="POST" action="/dns/delete-domain" style="display:inline"
                          onsubmit="return confirm('Delete zone {html.escape(z['domain'])}? All records will be removed.')">
                        <input type="hidden" name="provider" value="{z['provider']}">
                        <input type="hidden" name="domain" value="{z['domain']}">
                        <button class="btn btn-danger btn-sm">Delete</button></form>
                </td></tr>"""

        provider_options = "".join(f'<option value="{n}">{PROVIDERS[n].display}</option>' for n in providers)

        # Also pull live zones from providers
        live_info = ""
        for name, prov in providers.items():
            try:
                if hasattr(prov, 'list_domains'):
                    live = prov.list_domains()
                    for d in live:
                        exists = self.conn.execute("SELECT 1 FROM dns_zones WHERE domain=? AND provider=?",
                                                    (d["name"], name)).fetchone()
                        if not exists:
                            self.conn.execute("INSERT OR IGNORE INTO dns_zones (provider, domain) VALUES (?, ?)",
                                              (name, d["name"]))
                    self.conn.commit()
            except (ProviderError, AttributeError):
                pass

        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h1>DNS Management</h1>
        </div>
        <div class="card" style="margin-bottom:16px">
            <h2>🌐 Add Domain Zone</h2>
            <form method="POST" action="/dns/add-domain" style="display:flex;gap:8px;align-items:end">
                <div class="form-group" style="flex:1;margin:0"><label>Domain</label><input type="text" name="domain" required placeholder="example.com"></div>
                <div class="form-group" style="flex:1;margin:0"><label>Provider</label><select name="provider">{provider_options}</select></div>
                <div class="form-group" style="flex:0.5;margin:0"><label>Initial IP (optional)</label><input type="text" name="ip" placeholder="1.2.3.4"></div>
                <button class="btn btn-primary" style="margin-bottom:0">Add Domain</button>
            </form>
        </div>
        <div class="card"><table>
            <tr><th>Domain</th><th>Provider</th><th>Added</th><th>Actions</th></tr>
            {zone_rows or '<tr><td colspan="4" style="color:var(--text-dim);text-align:center;padding:40px">No DNS zones. Add a domain above.</td></tr>'}
        </table></div>"""
        self._send(200, page_layout("DNS", content, "dns"))

    def _page_dns_records(self, qs):
        provider = qs.get("provider", "")
        domain = qs.get("domain", "")
        if not provider or not domain:
            self._redirect("/dns")
            return

        records = []
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        error_msg = ""
        if row:
            try:
                prov = get_provider(provider, row["api_key"])
                records = prov.list_dns_records(domain)
            except ProviderError as e:
                error_msg = str(e)[:200]

        record_rows = ""
        for rec in records:
            record_rows += f"""<tr>
                <td><span class="badge" style="background:var(--surface2);color:var(--blue)">{rec['type']}</span></td>
                <td><code>{html.escape(rec.get('name','@'))}</code></td>
                <td><code>{html.escape(str(rec.get('data','')))}</code></td>
                <td>{rec.get('ttl', 3600)}</td>
                <td><form method="POST" action="/dns/delete-record" style="display:inline"
                      onsubmit="return confirm('Delete this record?')">
                    <input type="hidden" name="provider" value="{provider}">
                    <input type="hidden" name="domain" value="{domain}">
                    <input type="hidden" name="record_id" value="{rec['id']}">
                    <button class="btn btn-danger btn-sm">Delete</button></form></td></tr>"""

        enc_domain = html.escape(domain)
        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h1>DNS Records — {enc_domain}</h1>
            <a href="/dns" class="btn btn-secondary">← Back to Zones</a>
        </div>
        {f'<div class="alert alert-error">{html.escape(error_msg)}</div>' if error_msg else ''}
        <div class="card" style="margin-bottom:16px">
            <h2>+ Add Record</h2>
            <form method="POST" action="/dns/add-record" style="display:flex;gap:8px;align-items:end;flex-wrap:wrap">
                <input type="hidden" name="provider" value="{provider}">
                <input type="hidden" name="domain" value="{domain}">
                <div class="form-group" style="width:100px;margin:0"><label>Type</label>
                    <select name="record_type"><option>A</option><option>AAAA</option><option>CNAME</option><option>MX</option><option>TXT</option><option>NS</option><option>SRV</option></select></div>
                <div class="form-group" style="flex:1;margin:0"><label>Name</label><input type="text" name="name" required placeholder="@ or subdomain"></div>
                <div class="form-group" style="flex:1.5;margin:0"><label>Value</label><input type="text" name="data" required placeholder="1.2.3.4"></div>
                <div class="form-group" style="width:100px;margin:0"><label>TTL</label><input type="number" name="ttl" value="3600"></div>
                <button class="btn btn-primary" style="margin-bottom:0">Add</button>
            </form>
        </div>
        <div class="card"><table>
            <tr><th>Type</th><th>Name</th><th>Value</th><th>TTL</th><th>Actions</th></tr>
            {record_rows or '<tr><td colspan="5" style="color:var(--text-dim);text-align:center;padding:40px">No records yet</td></tr>'}
        </table></div>"""
        self._send(200, page_layout(f"DNS — {domain}", content, "dns"))

    # ── Plans & Pricing ──

    def _page_plans(self):
        plans = self.conn.execute("SELECT * FROM custom_plans ORDER BY provider, sell_price").fetchall()
        rows = ""
        for p in plans:
            margin = p["sell_price"] - p["cost_price"]
            margin_pct = (margin / p["cost_price"] * 100) if p["cost_price"] > 0 else 0
            active_cls = "badge-running" if p["active"] else "badge-stopped"
            active_txt = "Active" if p["active"] else "Inactive"
            p_display = PROVIDERS.get(p["provider"], type("", (), {"display": p["provider"]})).display
            inst_count = self.conn.execute(
                "SELECT COUNT(*) FROM instances WHERE custom_plan_id=? AND destroyed_at IS NULL", (p["id"],)
            ).fetchone()[0]

            rows += f"""<tr>
                <td><strong>{html.escape(p['display_name'])}</strong><br><span style="color:var(--text-dim);font-size:11px">{html.escape(p['name'])}</span></td>
                <td>{p_display}</td>
                <td>{p['vcpus']} vCPU / {p['ram_mb']//1024}GB / {p['disk_gb']}GB</td>
                <td class="money">{p['currency']} {p['cost_price']:.2f}</td>
                <td class="money money-positive">{p['currency']} {p['sell_price']:.2f}</td>
                <td class="money {'money-positive' if margin>0 else ''}">{p['currency']} {margin:.2f} <span style="color:var(--text-dim);font-size:11px">({margin_pct:.0f}%)</span></td>
                <td>{inst_count}</td>
                <td><span class="badge {active_cls}">{active_txt}</span></td>
                <td>
                    <form method="POST" action="/plans/toggle" style="display:inline">
                        <input type="hidden" name="id" value="{p['id']}">
                        <button class="btn btn-secondary btn-sm">{'Deactivate' if p['active'] else 'Activate'}</button></form>
                    <form method="POST" action="/plans/delete" style="display:inline"
                          onsubmit="return confirm('Delete plan {html.escape(p['display_name'])}?')">
                        <input type="hidden" name="id" value="{p['id']}">
                        <button class="btn btn-danger btn-sm">Delete</button></form>
                </td></tr>"""

        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h1>Plans & Pricing</h1>
            <div style="display:flex;gap:8px">
                <a href="/plans/import" class="btn btn-secondary">⬇ Import from Provider</a>
                <a href="/plans/new" class="btn btn-primary">+ New Plan</a>
            </div>
        </div>
        <div class="alert alert-info">💰 Set your reseller markup here. <strong>Cost price</strong> = what you pay the provider. <strong>Sell price</strong> = what your customers pay. The margin is your profit.</div>
        <div class="card"><table>
            <tr><th>Plan Name</th><th>Provider</th><th>Specs</th><th>Cost</th><th>Sell Price</th><th>Margin</th><th>Instances</th><th>Status</th><th>Actions</th></tr>
            {rows or '<tr><td colspan="9" style="color:var(--text-dim);text-align:center;padding:40px">No custom plans. <a href="/plans/import">Import from a provider</a> or <a href="/plans/new">create one manually</a>.</td></tr>'}
        </table></div>"""
        self._send(200, page_layout("Plans & Pricing", content, "plans"))

    def _page_new_plan(self):
        providers = self._get_providers()
        provider_options = "".join(f'<option value="{n}">{PROVIDERS[n].display}</option>' for n in providers)

        content = f"""
        <h1 style="margin-bottom:24px">Create Custom Plan</h1>
        <div class="card">
            <form method="POST" action="/plans/create">
                <div class="grid-2">
                    <div class="form-group"><label>Internal Name</label><input type="text" name="name" required placeholder="hetzner-cx22"></div>
                    <div class="form-group"><label>Display Name (customer-facing)</label><input type="text" name="display_name" required placeholder="Starter VPS"></div>
                </div>
                <div class="grid-3">
                    <div class="form-group"><label>Provider</label><select name="provider" id="provSelect" onchange="loadPlans()">{provider_options}</select></div>
                    <div class="form-group"><label>Provider Plan</label><select name="provider_plan_id" id="provPlanSelect"><option>Loading...</option></select></div>
                    <div class="form-group"><label>Description</label><input type="text" name="description" placeholder="Perfect for small projects"></div>
                </div>
                <div class="grid-4">
                    <div class="form-group"><label>vCPUs</label><input type="number" name="vcpus" value="1" min="1"></div>
                    <div class="form-group"><label>RAM (MB)</label><input type="number" name="ram_mb" value="1024" min="256"></div>
                    <div class="form-group"><label>Disk (GB)</label><input type="number" name="disk_gb" value="20" min="10"></div>
                    <div class="form-group"><label>Currency</label><select name="currency"><option>USD</option><option>EUR</option><option>GBP</option></select></div>
                </div>
                <div class="grid-3">
                    <div class="form-group"><label>Cost Price (your cost/mo)</label><input type="number" name="cost_price" step="0.01" required placeholder="4.99"></div>
                    <div class="form-group"><label>Markup %</label><input type="number" name="markup_pct" value="20" step="1" id="markupInput" onchange="calcSell()"></div>
                    <div class="form-group"><label>Sell Price (customer pays/mo)</label><input type="number" name="sell_price" step="0.01" required placeholder="5.99" id="sellInput"></div>
                </div>
                <div style="display:flex;gap:8px"><button type="submit" class="btn btn-primary">Create Plan</button><a href="/plans" class="btn btn-secondary">Cancel</a></div>
            </form>
        </div>
        <script>
        async function loadPlans() {{
            const prov = document.getElementById('provSelect').value;
            const plans = await (await fetch('/api/providers/'+prov+'/plans')).json();
            const sel = document.getElementById('provPlanSelect');
            sel.innerHTML = plans.map(p=>'<option value="'+p.id+'" data-price="'+p.price_monthly+'" data-vcpus="'+p.vcpus+'" data-ram="'+p.ram_mb+'" data-disk="'+p.disk_gb+'">'+p.name+' — $'+p.price_monthly+'/mo ('+p.vcpus+'vCPU/'+Math.round(p.ram_mb/1024)+'GB/'+p.disk_gb+'GB)</option>').join('');
            sel.onchange = function() {{
                const o=sel.options[sel.selectedIndex];
                document.querySelector('[name=cost_price]').value=o.dataset.price;
                document.querySelector('[name=vcpus]').value=o.dataset.vcpus;
                document.querySelector('[name=ram_mb]').value=o.dataset.ram;
                document.querySelector('[name=disk_gb]').value=o.dataset.disk;
                calcSell();
            }};
        }}
        function calcSell() {{
            const cost = parseFloat(document.querySelector('[name=cost_price]').value)||0;
            const markup = parseFloat(document.getElementById('markupInput').value)||0;
            document.getElementById('sellInput').value = (cost*(1+markup/100)).toFixed(2);
        }}
        loadPlans();
        </script>"""
        self._send(200, page_layout("New Plan", content, "plans"))

    def _page_import_plans(self):
        providers = self._get_providers()
        provider_options = "".join(f'<option value="{n}">{PROVIDERS[n].display}</option>' for n in providers)

        content = f"""
        <h1 style="margin-bottom:24px">Import Plans from Provider</h1>
        <div class="card">
            <p style="color:var(--text-dim);margin-bottom:16px">Select a provider and markup percentage. All available plans will be imported as custom plans with the specified markup applied.</p>
            <form method="POST" action="/plans/import-save">
                <div class="grid-3">
                    <div class="form-group"><label>Provider</label><select name="provider">{provider_options}</select></div>
                    <div class="form-group"><label>Markup %</label><input type="number" name="markup_pct" value="20" step="1" min="0"></div>
                    <div class="form-group"><label>Name Prefix</label><input type="text" name="prefix" value="Clover" placeholder="Clover"></div>
                </div>
                <div style="display:flex;gap:8px"><button type="submit" class="btn btn-primary">Import All Plans</button><a href="/plans" class="btn btn-secondary">Cancel</a></div>
            </form>
        </div>"""
        self._send(200, page_layout("Import Plans", content, "plans"))

    # ── Invoices ──

    def _page_invoices(self):
        invoices = self.conn.execute("SELECT * FROM invoices ORDER BY created_at DESC").fetchall()
        rows = ""
        for inv in invoices:
            badge_cls = {"paid": "badge-paid", "sent": "badge-sent", "overdue": "badge-overdue",
                         "draft": "badge-draft"}.get(inv["status"], "badge-draft")
            rows += f"""<tr>
                <td><a href="/invoices/view?id={inv['id']}"><strong>{html.escape(inv['invoice_number'])}</strong></a></td>
                <td>{html.escape(inv['customer_name'])}</td>
                <td><span class="badge {badge_cls}">{inv['status']}</span></td>
                <td class="money">{inv['currency']} {inv['total']:.2f}</td>
                <td>{inv['due_date'] or '—'}</td>
                <td>{inv['created_at']}</td>
                <td>
                    <a href="/invoices/view?id={inv['id']}" class="btn btn-secondary btn-sm">View</a>
                    <a href="/invoices/print?id={inv['id']}" class="btn btn-secondary btn-sm" target="_blank">Print</a>
                    <form method="POST" action="/invoices/delete" style="display:inline"
                          onsubmit="return confirm('Delete invoice {html.escape(inv['invoice_number'])}?')">
                        <input type="hidden" name="id" value="{inv['id']}">
                        <button class="btn btn-danger btn-sm">Delete</button></form>
                </td></tr>"""

        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h1>Invoices</h1>
            <div style="display:flex;gap:8px">
                <a href="/invoices/new" class="btn btn-primary">+ New Invoice</a>
            </div>
        </div>
        <div class="card"><table>
            <tr><th>Invoice #</th><th>Customer</th><th>Status</th><th>Total</th><th>Due Date</th><th>Created</th><th>Actions</th></tr>
            {rows or '<tr><td colspan="7" style="color:var(--text-dim);text-align:center;padding:40px">No invoices yet. <a href="/invoices/new">Create your first invoice</a></td></tr>'}
        </table></div>"""
        self._send(200, page_layout("Invoices", content, "invoices"))

    def _page_new_invoice(self):
        prefix = get_setting(self.conn, "invoice_prefix", "CVPS")
        next_num = get_setting(self.conn, "invoice_next_number", "1001")
        inv_num = f"{prefix}-{next_num}"
        currency = get_setting(self.conn, "default_currency", "USD")
        tax_rate = get_setting(self.conn, "default_tax_rate", "0")

        # Active instances for quick-add
        instances = self.conn.execute(
            "SELECT i.*, cp.display_name as plan_name, cp.sell_price "
            "FROM instances i LEFT JOIN custom_plans cp ON i.custom_plan_id = cp.id "
            "WHERE i.destroyed_at IS NULL ORDER BY i.name"
        ).fetchall()

        instance_buttons = ""
        for inst in instances:
            price = inst["sell_price"] or 0
            desc = f'{inst["plan_name"] or inst["name"]} — {inst["ip"] or "no IP"}'
            instance_buttons += f'<button type="button" class="btn btn-secondary btn-sm" style="margin:2px" onclick="addItem(\'{html.escape(desc)}\', {price})">{html.escape(inst["name"])} (${price:.2f})</button>'

        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        content = f"""
        <h1 style="margin-bottom:24px">Create Invoice</h1>
        <div class="card">
            <form method="POST" action="/invoices/create" id="invoiceForm">
                <div class="grid-3">
                    <div class="form-group"><label>Invoice Number</label><input type="text" name="invoice_number" value="{inv_num}" required></div>
                    <div class="form-group"><label>Customer Name</label><input type="text" name="customer_name" required placeholder="John Smith"></div>
                    <div class="form-group"><label>Customer Email</label><input type="email" name="customer_email" placeholder="john@example.com"></div>
                </div>
                <div class="grid-3">
                    <div class="form-group"><label>Currency</label><select name="currency"><option {'selected' if currency=='USD' else ''}>USD</option><option {'selected' if currency=='EUR' else ''}>EUR</option><option {'selected' if currency=='GBP' else ''}>GBP</option></select></div>
                    <div class="form-group"><label>Tax Rate (%)</label><input type="number" name="tax_rate" value="{tax_rate}" step="0.01" min="0" onchange="recalc()"></div>
                    <div class="form-group"><label>Due Date</label><input type="date" name="due_date" value="{due_date}"></div>
                </div>

                {f'<div style="margin-bottom:16px"><p style="color:var(--text-dim);font-size:12px;margin-bottom:8px">Quick-add active instances:</p>{instance_buttons}</div>' if instance_buttons else ''}

                <h3>Line Items</h3>
                <div id="items"></div>
                <button type="button" class="btn btn-secondary btn-sm" onclick="addItem('', 0)" style="margin-bottom:16px">+ Add Line Item</button>

                <div class="grid-2">
                    <div class="form-group"><label>Notes</label><textarea name="notes" rows="3" placeholder="Additional notes..."></textarea></div>
                    <div>
                        <div style="text-align:right;padding:8px 0"><span style="color:var(--text-dim)">Subtotal:</span> <span id="subtotal" class="money">0.00</span></div>
                        <div style="text-align:right;padding:8px 0"><span style="color:var(--text-dim)">Tax:</span> <span id="taxAmount" class="money">0.00</span></div>
                        <div style="text-align:right;padding:8px 0;font-size:18px;font-weight:700"><span>Total:</span> <span id="totalAmount" class="money money-positive">0.00</span></div>
                    </div>
                </div>

                <input type="hidden" name="items_json" id="itemsJson">
                <div style="display:flex;gap:8px"><button type="submit" class="btn btn-primary" onclick="prepSubmit()">Create Invoice</button><a href="/invoices" class="btn btn-secondary">Cancel</a></div>
            </form>
        </div>
        <script>
        let itemCount = 0;
        function addItem(desc, price) {{
            const div = document.createElement('div');
            div.className = 'grid-3'; div.style.marginBottom = '8px'; div.id = 'item-'+itemCount;
            div.innerHTML = '<div class="form-group" style="margin:0"><input type="text" class="item-desc" placeholder="Description" value="'+desc+'"></div>'
                + '<div class="form-group" style="margin:0"><input type="number" class="item-qty" placeholder="Qty" value="1" min="1" onchange="recalc()"></div>'
                + '<div class="form-group" style="margin:0;display:flex;gap:4px"><input type="number" class="item-price" placeholder="Unit Price" step="0.01" value="'+price.toFixed(2)+'" onchange="recalc()">'
                + '<button type="button" class="btn btn-danger btn-sm" onclick="this.closest(\\'.grid-3\\').remove();recalc()">×</button></div>';
            document.getElementById('items').appendChild(div);
            itemCount++;
            recalc();
        }}
        function recalc() {{
            let sub = 0;
            document.querySelectorAll('#items .grid-3').forEach(row => {{
                const qty = parseFloat(row.querySelector('.item-qty').value)||0;
                const price = parseFloat(row.querySelector('.item-price').value)||0;
                sub += qty * price;
            }});
            const taxRate = parseFloat(document.querySelector('[name=tax_rate]').value)||0;
            const tax = sub * taxRate / 100;
            document.getElementById('subtotal').textContent = sub.toFixed(2);
            document.getElementById('taxAmount').textContent = tax.toFixed(2);
            document.getElementById('totalAmount').textContent = (sub+tax).toFixed(2);
        }}
        function prepSubmit() {{
            const items = [];
            document.querySelectorAll('#items .grid-3').forEach(row => {{
                items.push({{
                    description: row.querySelector('.item-desc').value,
                    quantity: parseFloat(row.querySelector('.item-qty').value)||1,
                    unit_price: parseFloat(row.querySelector('.item-price').value)||0
                }});
            }});
            document.getElementById('itemsJson').value = JSON.stringify(items);
        }}
        addItem('', 0);
        </script>"""
        self._send(200, page_layout("New Invoice", content, "invoices"))

    def _page_view_invoice(self, qs):
        inv_id = qs.get("id", "")
        inv = self.conn.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
        if not inv:
            self._redirect("/invoices")
            return

        items = self.conn.execute("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (inv_id,)).fetchall()
        item_rows = ""
        for item in items:
            item_rows += f"""<tr>
                <td>{html.escape(item['description'])}</td>
                <td style="text-align:right">{item['quantity']:.0f}</td>
                <td style="text-align:right" class="money">{inv['currency']} {item['unit_price']:.2f}</td>
                <td style="text-align:right" class="money">{inv['currency']} {item['total']:.2f}</td></tr>"""

        badge_cls = {"paid": "badge-paid", "sent": "badge-sent", "overdue": "badge-overdue",
                     "draft": "badge-draft"}.get(inv["status"], "badge-draft")

        status_buttons = ""
        for st in ["draft", "sent", "paid", "overdue"]:
            if st != inv["status"]:
                cls = "btn-primary" if st == "paid" else "btn-secondary"
                status_buttons += f'<form method="POST" action="/invoices/update-status" style="display:inline"><input type="hidden" name="id" value="{inv_id}"><input type="hidden" name="status" value="{st}"><button class="btn {cls} btn-sm">{st.title()}</button></form> '

        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h1>Invoice {html.escape(inv['invoice_number'])} <span class="badge {badge_cls}" style="vertical-align:middle">{inv['status']}</span></h1>
            <div style="display:flex;gap:8px">
                <a href="/invoices/print?id={inv_id}" class="btn btn-secondary" target="_blank">🖨 Print</a>
                <a href="/invoices" class="btn btn-secondary">← Back</a>
            </div>
        </div>
        <div class="grid-2">
            <div class="card"><h3>Customer</h3>
                <p style="font-size:16px;font-weight:600">{html.escape(inv['customer_name'])}</p>
                <p style="color:var(--text-dim)">{html.escape(inv['customer_email'])}</p></div>
            <div class="card"><h3>Details</h3>
                <p>Created: {inv['created_at']}</p>
                <p>Due: {inv['due_date'] or '—'}</p>
                {f"<p>Paid: {inv['paid_date']}</p>" if inv['paid_date'] else ''}</div>
        </div>
        <div class="card">
            <h2>Line Items</h2>
            <table><tr><th>Description</th><th style="text-align:right">Qty</th><th style="text-align:right">Unit Price</th><th style="text-align:right">Total</th></tr>
                {item_rows}
            </table>
            <div style="display:flex;justify-content:flex-end;margin-top:16px">
                <div style="width:280px">
                    <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)"><span style="color:var(--text-dim)">Subtotal</span><span class="money">{inv['currency']} {inv['subtotal']:.2f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)"><span style="color:var(--text-dim)">Tax ({inv['tax_rate']:.1f}%)</span><span class="money">{inv['currency']} {inv['tax_amount']:.2f}</span></div>
                    <div style="display:flex;justify-content:space-between;padding:12px 0;font-size:18px;font-weight:700"><span>Total</span><span class="money money-positive">{inv['currency']} {inv['total']:.2f}</span></div>
                </div>
            </div>
        </div>
        <div class="card"><h2>Update Status</h2>{status_buttons}</div>
        {'<div class="card"><h3>Notes</h3><p style="white-space:pre-line">'+html.escape(inv['notes'])+'</p></div>' if inv['notes'] else ''}"""
        self._send(200, page_layout(f"Invoice {inv['invoice_number']}", content, "invoices"))

    def _page_print_invoice(self, qs):
        inv_id = qs.get("id", "")
        self._send(200, generate_invoice_html(self.conn, inv_id))

    # ── Billing Settings ──

    def _page_billing_settings(self):
        fields = [
            ("company_name", "Company Name", "text"),
            ("company_email", "Company Email", "email"),
            ("company_address", "Company Address", "textarea"),
            ("default_currency", "Default Currency", "select:USD,EUR,GBP"),
            ("default_tax_rate", "Default Tax Rate (%)", "number"),
            ("invoice_prefix", "Invoice Prefix", "text"),
            ("invoice_next_number", "Next Invoice Number", "number"),
            ("payment_terms", "Payment Terms", "text"),
            ("payment_instructions", "Payment Instructions", "textarea"),
        ]

        form_fields = ""
        for key, label, ftype in fields:
            val = html.escape(get_setting(self.conn, key, ""))
            if ftype == "textarea":
                form_fields += f'<div class="form-group"><label>{label}</label><textarea name="{key}" rows="3">{val}</textarea></div>'
            elif ftype.startswith("select:"):
                opts = ftype.split(":")[1].split(",")
                opt_html = "".join(f'<option{"selected" if o==val else ""}>{o}</option>' for o in opts)
                form_fields += f'<div class="form-group"><label>{label}</label><select name="{key}">{opt_html}</select></div>'
            elif ftype == "number":
                form_fields += f'<div class="form-group"><label>{label}</label><input type="number" name="{key}" value="{val}" step="0.01"></div>'
            else:
                form_fields += f'<div class="form-group"><label>{label}</label><input type="{ftype}" name="{key}" value="{val}"></div>'

        content = f"""
        <h1 style="margin-bottom:24px">Billing Settings</h1>
        <div class="card">
            <form method="POST" action="/billing/save">
                {form_fields}
                <button type="submit" class="btn btn-primary">Save Settings</button>
            </form>
        </div>"""
        self._send(200, page_layout("Billing Settings", content, "billing"))

    # ── Snapshots ──

    def _page_snapshots(self):
        providers = self._get_providers()
        rows = ""
        for name, prov in providers.items():
            try:
                for s in prov.list_snapshots():
                    rows += f"""<tr><td>{html.escape(s.get('name',''))}</td><td>{PROVIDERS[name].display}</td>
                        <td>{s.get('size_gb',0)} GB</td><td>{s.get('created','')}</td>
                        <td><form method="POST" action="/snapshots/delete" style="display:inline"
                              onsubmit="return confirm('Delete this snapshot?')">
                            <input type="hidden" name="provider" value="{name}"><input type="hidden" name="snapshot_id" value="{s['id']}">
                            <button class="btn btn-danger btn-sm">Delete</button></form></td></tr>"""
            except ProviderError as e:
                rows += f'<tr><td colspan="5" style="color:var(--red)">{PROVIDERS[name].display}: {html.escape(str(e)[:100])}</td></tr>'

        instances = self.conn.execute("SELECT * FROM instances WHERE destroyed_at IS NULL").fetchall()
        inst_options = "".join(f'<option value="{i["id"]}">{html.escape(i["name"])} ({i["provider"]})</option>' for i in instances)

        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px"><h1>Snapshots</h1></div>
        {f'<div class="card" style="margin-bottom:16px"><h2>📸 Create Snapshot</h2><form method="POST" action="/snapshots/create" style="display:flex;gap:8px;align-items:end"><div class="form-group" style="flex:1;margin:0"><label>Instance</label><select name="instance_id">{inst_options}</select></div><div class="form-group" style="flex:1;margin:0"><label>Description</label><input type="text" name="description" placeholder="Pre-upgrade backup"></div><button class="btn btn-primary" style="margin-bottom:0">Create</button></form></div>' if instances else ''}
        <div class="card"><table><tr><th>Name</th><th>Provider</th><th>Size</th><th>Created</th><th>Actions</th></tr>
            {rows or '<tr><td colspan="5" style="color:var(--text-dim);text-align:center;padding:40px">No snapshots</td></tr>'}</table></div>"""
        self._send(200, page_layout("Snapshots", content, "snapshots"))

    # ── Firewalls ──

    def _page_firewalls(self):
        providers = self._get_providers()
        rows = ""
        for name, prov in providers.items():
            try:
                for fw in prov.list_firewalls():
                    rows += f"""<tr><td>{html.escape(fw['name'])}</td><td>{PROVIDERS[name].display}</td><td>{fw['rules_count']}</td>
                        <td><form method="POST" action="/firewalls/delete" style="display:inline"
                              onsubmit="return confirm('Delete firewall {html.escape(fw['name'])}?')">
                            <input type="hidden" name="provider" value="{name}"><input type="hidden" name="firewall_id" value="{fw['id']}">
                            <button class="btn btn-danger btn-sm">Delete</button></form></td></tr>"""
            except ProviderError:
                pass

        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
            <h1>Firewalls</h1><a href="/firewalls/new" class="btn btn-primary">+ New Firewall</a>
        </div>
        <div class="card"><table><tr><th>Name</th><th>Provider</th><th>Rules</th><th>Actions</th></tr>
            {rows or '<tr><td colspan="4" style="color:var(--text-dim);text-align:center;padding:40px">No firewalls</td></tr>'}</table></div>"""
        self._send(200, page_layout("Firewalls", content, "firewalls"))

    def _page_new_firewall(self):
        providers = self._get_providers()
        provider_options = "".join(f'<option value="{n}">{PROVIDERS[n].display}</option>' for n in providers)
        content = f"""
        <h1 style="margin-bottom:24px">Create Firewall</h1>
        <div class="card"><form method="POST" action="/firewalls/create">
            <div class="grid-2">
                <div class="form-group"><label>Firewall Name</label><input type="text" name="name" required placeholder="web-firewall"></div>
                <div class="form-group"><label>Provider</label><select name="provider">{provider_options}</select></div>
            </div>
            <h3>Inbound Rules</h3><p style="color:var(--text-dim);font-size:12px;margin-bottom:12px">One rule per line: protocol,port,source (e.g. tcp,22,0.0.0.0/0)</p>
            <div class="form-group"><textarea name="rules" rows="5">tcp,22,0.0.0.0/0
tcp,80,0.0.0.0/0
tcp,443,0.0.0.0/0</textarea></div>
            <div style="display:flex;gap:8px"><button type="submit" class="btn btn-primary">Create Firewall</button><a href="/firewalls" class="btn btn-secondary">Cancel</a></div>
        </form></div>"""
        self._send(200, page_layout("New Firewall", content, "firewalls"))

    # ── SSH Keys ──

    def _page_ssh_keys(self):
        providers = self._get_providers()
        rows = ""
        for name, prov in providers.items():
            try:
                for k in prov.list_ssh_keys():
                    rows += f"""<tr><td>{html.escape(k['name'])}</td><td>{PROVIDERS[name].display}</td><td><code>{k.get('fingerprint','')[:24]}...</code></td>
                        <td><form method="POST" action="/ssh-keys/delete" style="display:inline"
                              onsubmit="return confirm('Delete SSH key {html.escape(k['name'])}?')">
                            <input type="hidden" name="provider" value="{name}"><input type="hidden" name="key_id" value="{k['id']}">
                            <button class="btn btn-danger btn-sm">Delete</button></form></td></tr>"""
            except ProviderError:
                pass

        provider_options = "".join(f'<option value="{n}">{PROVIDERS[n].display}</option>' for n in providers)
        content = f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px"><h1>SSH Keys</h1></div>
        <div class="card" style="margin-bottom:16px"><h2>🔑 Add SSH Key</h2>
            <form method="POST" action="/ssh-keys/add">
                <div class="grid-2">
                    <div class="form-group"><label>Key Name</label><input type="text" name="name" required placeholder="my-workstation"></div>
                    <div class="form-group"><label>Provider</label><select name="provider">{provider_options}</select></div>
                </div>
                <div class="form-group"><label>Public Key</label><textarea name="public_key" rows="3" required placeholder="ssh-rsa AAAA... user@host"></textarea></div>
                <button type="submit" class="btn btn-primary">Add Key</button>
            </form></div>
        <div class="card"><table><tr><th>Name</th><th>Provider</th><th>Fingerprint</th><th>Actions</th></tr>
            {rows or '<tr><td colspan="4" style="color:var(--text-dim);text-align:center;padding:40px">No SSH keys</td></tr>'}</table></div>"""
        self._send(200, page_layout("SSH Keys", content, "ssh-keys"))

    # ── Providers ──

    def _page_providers(self):
        configured = {r["provider"]: r for r in self.conn.execute("SELECT * FROM provider_keys").fetchall()}
        cards = ""
        for name, cls in PROVIDERS.items():
            is_cfg = name in configured
            status = '<span class="badge badge-running">Connected</span>' if is_cfg else '<span class="badge badge-stopped">Not Connected</span>'
            key_masked = configured[name]["api_key"][:8] + "..." if is_cfg else ""
            cards += f"""<div class="card"><h2>{cls.display} {status}</h2>
                <form method="POST" action="/providers/save"><input type="hidden" name="provider" value="{name}">
                <div class="form-group"><label>API Key</label><input type="password" name="api_key" value="{key_masked}" placeholder="Enter API key"
                    onfocus="if(this.value.includes('...'))this.value=''"></div>
                <div style="display:flex;gap:8px"><button type="submit" class="btn btn-primary btn-sm">{'Update' if is_cfg else 'Connect'}</button>
                {'<form method="POST" action="/providers/delete" style="display:inline"><input type="hidden" name="provider" value="'+name+'"><button class="btn btn-danger btn-sm">Disconnect</button></form>' if is_cfg else ''}</div></form></div>"""

        content = f"""
        <h1 style="margin-bottom:24px">Provider Configuration</h1>
        <div class="alert alert-info">🔒 API keys are stored locally on this mycloverOS instance in <code>/etc/myclover/clover-vps/</code>. They never leave this machine.</div>
        <div class="grid-2">{cards}</div>"""
        self._send(200, page_layout("Providers", content, "providers"))

    # ── Audit Log ──

    def _page_audit(self):
        entries = self.conn.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT 200").fetchall()
        rows = ""
        for e in entries:
            rows += f'<tr><td style="color:var(--text-dim);white-space:nowrap">{e["ts"]}</td><td><strong>{html.escape(e["action"])}</strong></td><td>{html.escape(e["detail"])}</td></tr>'

        content = f"""
        <h1 style="margin-bottom:24px">Audit Log</h1>
        <div class="card"><table><tr><th>Timestamp</th><th>Action</th><th>Details</th></tr>
            {rows or '<tr><td colspan="3" style="color:var(--text-dim);text-align:center;padding:40px">No audit entries</td></tr>'}</table></div>"""
        self._send(200, page_layout("Audit Log", content, "audit"))

    # ── API endpoints ──

    def _handle_api_get(self, path):
        parts = path.strip("/").split("/")
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
                resource_map = {"plans": prov.list_plans, "regions": prov.list_regions,
                               "images": prov.list_images, "ssh-keys": prov.list_ssh_keys}
                fn = resource_map.get(resource)
                if fn:
                    self._json(200, fn())
                else:
                    self._json(404, {"error": "Unknown resource"})
            except ProviderError as e:
                self._json(500, {"error": str(e)})
        else:
            self._json(404, {"error": "Unknown API endpoint"})

    # ── POST handlers ──

    def _handle_save_provider(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        api_key = form.get("api_key", "").strip()
        if not api_key or "..." in api_key or provider not in PROVIDERS:
            self._redirect("/providers")
            return
        try:
            prov = get_provider(provider, api_key)
            prov.list_regions()
        except ProviderError as e:
            content = f'<div class="alert alert-error">Failed to connect to {PROVIDERS[provider].display}: {html.escape(str(e)[:200])}</div><a href="/providers" class="btn btn-secondary">Back</a>'
            self._send(200, page_layout("Error", content, "providers"))
            return
        self.conn.execute("INSERT OR REPLACE INTO provider_keys (provider, api_key, enabled) VALUES (?, ?, 1)",
                          (provider, api_key))
        self.conn.commit()
        audit(self.conn, "provider_connected", PROVIDERS[provider].display)
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
        custom_plan_id = form.get("custom_plan_id", "") or None

        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider_name,)).fetchone()
        if not row:
            self._redirect("/instances")
            return
        try:
            prov = get_provider(provider_name, row["api_key"])
            ssh_keys = [ssh_key_id] if ssh_key_id else None
            result = prov.create_instance(name, plan_id, region_id, image_id, ssh_keys)
            self.conn.execute(
                "INSERT INTO instances (name, provider, provider_id, plan_id, region_id, image_id, status, ip, ipv6, custom_plan_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (name, provider_name, result["provider_id"], plan_id, region_id, image_id,
                 result.get("status", "provisioning"), result.get("ip", ""), result.get("ipv6", ""),
                 int(custom_plan_id) if custom_plan_id else None))
            self.conn.commit()
            audit(self.conn, "instance_created", f"{name} on {PROVIDERS[provider_name].display} ({result.get('provider_id','')})")
        except ProviderError as e:
            content = f'<div class="alert alert-error">Failed to create instance: {html.escape(str(e)[:300])}</div><a href="/instances/new" class="btn btn-secondary">Back</a>'
            self._send(200, page_layout("Error", content, "instances"))
            return
        self._redirect("/instances")

    def _handle_instance_action(self):
        form = self._parse_form()
        inst = self.conn.execute("SELECT * FROM instances WHERE id=?", (form.get("id", ""),)).fetchone()
        if not inst:
            self._redirect("/instances")
            return
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (inst["provider"],)).fetchone()
        if row:
            try:
                prov = get_provider(inst["provider"], row["api_key"])
                prov.power_action(inst["provider_id"], form.get("action", "reboot"))
                audit(self.conn, f"instance_{form.get('action','')}", inst['name'])
            except ProviderError:
                pass
        self._redirect("/instances")

    def _handle_destroy_instance(self):
        form = self._parse_form()
        inst = self.conn.execute("SELECT * FROM instances WHERE id=?", (form.get("id", ""),)).fetchone()
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
        self.conn.execute("UPDATE instances SET destroyed_at=datetime('now'), status='destroyed' WHERE id=?",
                          (form.get("id", ""),))
        self.conn.commit()
        audit(self.conn, "instance_destroyed", f"{inst['name']} on {inst['provider']}")
        self._redirect("/instances")

    def _handle_create_snapshot(self):
        form = self._parse_form()
        inst = self.conn.execute("SELECT * FROM instances WHERE id=?", (form.get("instance_id", ""),)).fetchone()
        if not inst:
            self._redirect("/snapshots")
            return
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (inst["provider"],)).fetchone()
        if row:
            try:
                prov = get_provider(inst["provider"], row["api_key"])
                prov.create_snapshot(inst["provider_id"], form.get("description", ""))
                audit(self.conn, "snapshot_created", f"for {inst['name']}")
            except ProviderError:
                pass
        self._redirect("/snapshots")

    def _handle_delete_snapshot(self):
        form = self._parse_form()
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (form.get("provider", ""),)).fetchone()
        if row:
            try:
                prov = get_provider(form["provider"], row["api_key"])
                prov.delete_snapshot(form.get("snapshot_id", ""))
                audit(self.conn, "snapshot_deleted", f"{form['provider']}:{form.get('snapshot_id','')}")
            except ProviderError:
                pass
        self._redirect("/snapshots")

    def _handle_create_firewall(self):
        form = self._parse_form()
        rules = []
        for line in form.get("rules", "").strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) >= 2:
                rules.append({"protocol": parts[0].strip(), "port": parts[1].strip(),
                              "source_ips": [parts[2].strip()] if len(parts) > 2 else ["0.0.0.0/0", "::/0"]})
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (form.get("provider", ""),)).fetchone()
        if row and rules:
            try:
                prov = get_provider(form["provider"], row["api_key"])
                prov.create_firewall(form.get("name", ""), rules)
                audit(self.conn, "firewall_created", f"{form.get('name','')} on {form['provider']}")
            except ProviderError:
                pass
        self._redirect("/firewalls")

    def _handle_delete_firewall(self):
        form = self._parse_form()
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (form.get("provider", ""),)).fetchone()
        if row:
            try:
                prov = get_provider(form["provider"], row["api_key"])
                prov.delete_firewall(form.get("firewall_id", ""))
                audit(self.conn, "firewall_deleted", f"{form['provider']}:{form.get('firewall_id','')}")
            except ProviderError:
                pass
        self._redirect("/firewalls")

    def _handle_add_ssh_key(self):
        form = self._parse_form()
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (form.get("provider", ""),)).fetchone()
        if row and form.get("name") and form.get("public_key"):
            try:
                prov = get_provider(form["provider"], row["api_key"])
                prov.add_ssh_key(form["name"], form["public_key"])
                audit(self.conn, "ssh_key_added", f"{form['name']} on {form['provider']}")
            except ProviderError:
                pass
        self._redirect("/ssh-keys")

    def _handle_delete_ssh_key(self):
        form = self._parse_form()
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (form.get("provider", ""),)).fetchone()
        if row:
            try:
                prov = get_provider(form["provider"], row["api_key"])
                prov.delete_ssh_key(form.get("key_id", ""))
                audit(self.conn, "ssh_key_deleted", f"{form['provider']}:{form.get('key_id','')}")
            except ProviderError:
                pass
        self._redirect("/ssh-keys")

    # DNS handlers
    def _handle_add_domain(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        domain = form.get("domain", "").strip().lower()
        ip = form.get("ip", "").strip()
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row and domain:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.add_domain(domain, ip)
                self.conn.execute("INSERT OR IGNORE INTO dns_zones (provider, domain) VALUES (?, ?)", (provider, domain))
                self.conn.commit()
                audit(self.conn, "dns_zone_created", f"{domain} on {provider}")
            except ProviderError as e:
                content = f'<div class="alert alert-error">{html.escape(str(e)[:300])}</div><a href="/dns" class="btn btn-secondary">Back</a>'
                self._send(200, page_layout("Error", content, "dns"))
                return
        self._redirect("/dns")

    def _handle_delete_domain(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        domain = form.get("domain", "")
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.delete_domain(domain)
            except ProviderError:
                pass
        self.conn.execute("DELETE FROM dns_zones WHERE provider=? AND domain=?", (provider, domain))
        self.conn.commit()
        audit(self.conn, "dns_zone_deleted", f"{domain} on {provider}")
        self._redirect("/dns")

    def _handle_add_record(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        domain = form.get("domain", "")
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.create_dns_record(domain, form.get("record_type", "A"),
                                       form.get("name", "@"), form.get("data", ""),
                                       int(form.get("ttl", "3600")))
                audit(self.conn, "dns_record_created", f"{form.get('record_type','')} {form.get('name','')} on {domain}")
            except ProviderError as e:
                pass
        self._redirect(f"/dns/records?provider={provider}&domain={urllib.parse.quote(domain)}")

    def _handle_delete_record(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        domain = form.get("domain", "")
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if row:
            try:
                prov = get_provider(provider, row["api_key"])
                prov.delete_dns_record(domain, form.get("record_id", ""))
                audit(self.conn, "dns_record_deleted", f"on {domain}")
            except ProviderError:
                pass
        self._redirect(f"/dns/records?provider={provider}&domain={urllib.parse.quote(domain)}")

    # Plans handlers
    def _handle_create_plan(self):
        form = self._parse_form()
        cost = float(form.get("cost_price", "0"))
        sell = float(form.get("sell_price", "0"))
        markup = (sell / cost - 1) * 100 if cost > 0 else float(form.get("markup_pct", "20"))
        self.conn.execute(
            "INSERT INTO custom_plans (name, display_name, provider, provider_plan_id, cost_price, sell_price, markup_pct, currency, vcpus, ram_mb, disk_gb, description) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (form.get("name",""), form.get("display_name",""), form.get("provider",""),
             form.get("provider_plan_id",""), cost, sell, markup,
             form.get("currency","USD"), int(form.get("vcpus","1")), int(form.get("ram_mb","1024")),
             int(form.get("disk_gb","20")), form.get("description","")))
        self.conn.commit()
        audit(self.conn, "plan_created", f"{form.get('display_name','')} — sell {form.get('currency','USD')} {sell:.2f}")
        self._redirect("/plans")

    def _handle_delete_plan(self):
        form = self._parse_form()
        self.conn.execute("DELETE FROM custom_plans WHERE id=?", (form.get("id",""),))
        self.conn.commit()
        audit(self.conn, "plan_deleted", f"ID {form.get('id','')}")
        self._redirect("/plans")

    def _handle_toggle_plan(self):
        form = self._parse_form()
        plan = self.conn.execute("SELECT * FROM custom_plans WHERE id=?", (form.get("id",""),)).fetchone()
        if plan:
            new_active = 0 if plan["active"] else 1
            self.conn.execute("UPDATE custom_plans SET active=? WHERE id=?", (new_active, plan["id"]))
            self.conn.commit()
            audit(self.conn, "plan_toggled", f"{plan['display_name']} → {'active' if new_active else 'inactive'}")
        self._redirect("/plans")

    def _handle_import_plans(self):
        form = self._parse_form()
        provider = form.get("provider", "")
        markup_pct = float(form.get("markup_pct", "20"))
        prefix = form.get("prefix", "Clover").strip()
        row = self.conn.execute("SELECT api_key FROM provider_keys WHERE provider=?", (provider,)).fetchone()
        if not row:
            self._redirect("/plans")
            return
        try:
            prov = get_provider(provider, row["api_key"])
            plans = prov.list_plans()
            imported = 0
            for p in plans:
                cost = p["price_monthly"]
                sell = round(cost * (1 + markup_pct / 100), 2)
                display = f"{prefix} {p['name']}" if prefix else p["name"]
                # Skip if already exists
                exists = self.conn.execute(
                    "SELECT 1 FROM custom_plans WHERE provider=? AND provider_plan_id=?",
                    (provider, p["id"])).fetchone()
                if exists:
                    continue
                self.conn.execute(
                    "INSERT INTO custom_plans (name, display_name, provider, provider_plan_id, cost_price, sell_price, markup_pct, currency, vcpus, ram_mb, disk_gb) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (p["id"], display, provider, p["id"], cost, sell, markup_pct,
                     p.get("currency", "USD"), p["vcpus"], p["ram_mb"], p["disk_gb"]))
                imported += 1
            self.conn.commit()
            audit(self.conn, "plans_imported", f"{imported} plans from {PROVIDERS[provider].display} at {markup_pct}% markup")
        except ProviderError as e:
            pass
        self._redirect("/plans")

    # Invoice handlers
    def _handle_create_invoice(self):
        form = self._parse_form()
        items_json = form.get("items_json", "[]")
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            items = []

        subtotal = sum(i.get("quantity", 1) * i.get("unit_price", 0) for i in items)
        tax_rate = float(form.get("tax_rate", "0"))
        tax_amount = round(subtotal * tax_rate / 100, 2)
        total = round(subtotal + tax_amount, 2)

        inv_number = form.get("invoice_number", "")
        self.conn.execute(
            "INSERT INTO invoices (invoice_number, customer_name, customer_email, status, subtotal, tax_rate, tax_amount, total, currency, due_date, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (inv_number, form.get("customer_name",""), form.get("customer_email",""),
             "draft", subtotal, tax_rate, tax_amount, total,
             form.get("currency","USD"), form.get("due_date",""), form.get("notes","")))
        inv_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for item in items:
            qty = item.get("quantity", 1)
            price = item.get("unit_price", 0)
            self.conn.execute(
                "INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?,?,?,?,?)",
                (inv_id, item.get("description",""), qty, price, round(qty * price, 2)))

        # Increment next invoice number
        try:
            next_num = int(get_setting(self.conn, "invoice_next_number", "1001"))
            set_setting(self.conn, "invoice_next_number", str(next_num + 1))
        except ValueError:
            pass

        self.conn.commit()
        audit(self.conn, "invoice_created", f"{inv_number} for {form.get('customer_name','')} — {form.get('currency','USD')} {total:.2f}")
        self._redirect(f"/invoices/view?id={inv_id}")

    def _handle_update_invoice_status(self):
        form = self._parse_form()
        new_status = form.get("status", "")
        inv_id = form.get("id", "")
        if new_status in ("draft", "sent", "paid", "overdue"):
            paid_date = "datetime('now')" if new_status == "paid" else "NULL"
            self.conn.execute(
                f"UPDATE invoices SET status=?, paid_date={'datetime(\"now\")' if new_status=='paid' else 'NULL'} WHERE id=?",
                (new_status, inv_id))
            self.conn.commit()
            inv = self.conn.execute("SELECT invoice_number FROM invoices WHERE id=?", (inv_id,)).fetchone()
            audit(self.conn, "invoice_status_changed", f"{inv['invoice_number'] if inv else inv_id} → {new_status}")
        self._redirect(f"/invoices/view?id={inv_id}")

    def _handle_delete_invoice(self):
        form = self._parse_form()
        inv_id = form.get("id", "")
        inv = self.conn.execute("SELECT invoice_number FROM invoices WHERE id=?", (inv_id,)).fetchone()
        self.conn.execute("DELETE FROM invoice_items WHERE invoice_id=?", (inv_id,))
        self.conn.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
        self.conn.commit()
        audit(self.conn, "invoice_deleted", inv["invoice_number"] if inv else inv_id)
        self._redirect("/invoices")

    def _handle_generate_invoice(self):
        """Auto-generate invoices for all active instances with custom plans."""
        form = self._parse_form()
        # This generates a batch invoice for a customer
        self._redirect("/invoices/new")

    def _handle_save_billing(self):
        form = self._parse_form()
        for key, value in form.items():
            set_setting(self.conn, key, value)
        audit(self.conn, "billing_settings_updated", "")
        self._redirect("/billing")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    conn = init_db()
    _get_session_secret()
    VPSHandler.conn = conn

    ip = "0.0.0.0"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        display_ip = s.getsockname()[0]
        s.close()
    except Exception:
        display_ip = "localhost"

    url = f"http://{display_ip}:{PORT}"
    print("", flush=True)
    print("  ╔══════════════════════════════════════════════════╗", flush=True)
    print("  ║     🍀 CloverVPS Manager v0.2.0                 ║", flush=True)
    print("  ║                                                  ║", flush=True)
    print("  ║  VPS • DNS • Billing • Custom Plans              ║", flush=True)
    padding = 48 - len(url)
    print(f"  ║  → {url}{' ' * max(padding, 1)} ║", flush=True)
    print("  ║                                                  ║", flush=True)
    print("  ╚══════════════════════════════════════════════════╝", flush=True)
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
