#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

APP_DIR = Path.home() / ".render3d-robotics-runtime"
CONFIG_PATH = APP_DIR / "config.json"


def default_config() -> dict:
    return {
        "schema": "render3d.local-robotics-runtime/v1",
        "bind_host": "127.0.0.1",
        "advertise_host": "127.0.0.1",
        "port": 8460,
        "simulator": "mujoco",
        "pairing_token": secrets.token_urlsafe(24),
    }


def load_config() -> dict:
    APP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = default_config()
    if CONFIG_PATH.exists():
        try:
            config.update(json.loads(CONFIG_PATH.read_text()))
        except (OSError, ValueError, TypeError):
            pass
    config["port"] = max(1024, min(65535, int(config.get("port") or 8460)))
    config["simulator"] = config.get("simulator") if config.get("simulator") in {"mujoco", "isaac"} else "mujoco"
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    CONFIG_PATH.chmod(0o600)
    return config


def command_version(command: str, *args: str) -> dict:
    path = shutil.which(command)
    if not path:
        return {"available": False, "path": "", "version": ""}
    try:
        result = subprocess.run([path, *args], capture_output=True, text=True, timeout=3, check=False)
        version = (result.stdout or result.stderr).strip().splitlines()[0][:160]
        if result.returncode != 0:
            return {"available": False, "path": path, "version": version}
    except (OSError, subprocess.TimeoutExpired):
        version = "detected"
    return {"available": True, "path": path, "version": version}


def status_payload(config: dict) -> dict:
    system = platform.system().lower()
    return {
        "schema": config["schema"],
        "ok": True,
        "runtime_url": f"http://{config['advertise_host']}:{config['port']}",
        "platform": {"system": system, "machine": platform.machine(), "python": platform.python_version()},
        "tools": {
            "lerobot": command_version("lerobot-train", "--help"),
            "mujoco": command_version("python3", "-c", "import mujoco; print(mujoco.__version__)"),
            "nvidia_smi": command_version("nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"),
        },
        "simulators": {
            "mujoco": {"supported": True, "selected": config["simulator"] == "mujoco"},
            "isaac": {
                "supported": system in {"linux", "windows"},
                "selected": config["simulator"] == "isaac",
                "reason": "Full Isaac Lab requires a supported NVIDIA Windows or Ubuntu host" if system == "darwin" else "",
            },
        },
    }


INDEX = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Render Studio Robotics Runtime</title><style>
body{font:15px system-ui;background:#0b1118;color:#e7eef7;margin:0}.wrap{max-width:900px;margin:40px auto;padding:24px}.card{background:#111a24;border:1px solid #29415a;border-radius:14px;padding:20px;margin:14px 0}h1{margin:0 0 6px;color:#61dafb}label{display:block;margin:12px 0 4px;color:#9fb2c7}input,select,button{font:inherit;padding:10px;border-radius:8px;border:1px solid #38516a;background:#0a131d;color:#fff}input{width:min(420px,90%)}button{background:#126d47;cursor:pointer;margin-top:14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.pill{padding:12px;background:#0a131d;border-radius:9px}.muted{color:#91a3b5}code{color:#9ee7c2}</style></head><body><main class="wrap"><h1>Robotics Runtime</h1><p class="muted">Local compute for Render Studio</p><section class="card"><h2>Runtime status</h2><div id="status" class="grid">Loading…</div></section><section class="card"><h2>Connection</h2><label>Advertised host or LAN IP</label><input id="host"><label>Simulator</label><select id="sim"><option value="mujoco">MuJoCo</option><option value="isaac">Isaac Lab</option></select><br><button id="save">Save</button><p id="message" class="muted"></p></section><section class="card"><h2>Pair with Render Studio</h2><p>Runtime URL: <code id="url"></code></p><p>Pairing token: <code id="token"></code></p><p class="muted">Keep this token private. Render Studio should store it in the local browser only.</p></section></main><script>
const byId=id=>document.getElementById(id);let cfg={};async function load(){const [s,c]=await Promise.all([fetch('/api/status').then(r=>r.json()),fetch('/api/config').then(r=>r.json())]);cfg=c;byId('host').value=c.advertise_host;byId('sim').value=c.simulator;byId('url').textContent=s.runtime_url;byId('token').textContent=c.pairing_token;byId('status').innerHTML=`<div class=pill>Platform<br><b>${s.platform.system} ${s.platform.machine}</b></div><div class=pill>LeRobot<br><b>${s.tools.lerobot.available?'Ready':'Not installed'}</b></div><div class=pill>MuJoCo<br><b>${s.tools.mujoco.available?'Ready':'Not installed'}</b></div><div class=pill>Isaac Lab<br><b>${s.simulators.isaac.supported?'Supported':'Unavailable here'}</b></div>`}byId('save').onclick=async()=>{const r=await fetch('/api/config',{method:'PUT',headers:{'content-type':'application/json','authorization':`Bearer ${cfg.pairing_token}`},body:JSON.stringify({advertise_host:byId('host').value,simulator:byId('sim').value})});byId('message').textContent=r.ok?'Saved. Restart the runtime if you changed its network binding.':`Save failed: ${r.status}`;await load()};load();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "RenderStudioRoboticsRuntime/0.1"

    def _json(self, value: dict, status: int = 200) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "https://render3d.app")
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "https://render3d.app")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type")
        self.end_headers()

    def do_GET(self) -> None:
        config = load_config()
        path = urlparse(self.path).path
        if path == "/api/status":
            return self._json(status_payload(config))
        if path == "/api/config":
            return self._json(config)
        if path == "/":
            body = INDEX.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        self._json({"ok": False, "error": "not_found"}, 404)

    def do_PUT(self) -> None:
        if urlparse(self.path).path != "/api/config":
            return self._json({"ok": False, "error": "not_found"}, 404)
        config = load_config()
        if self.headers.get("Authorization") != f"Bearer {config['pairing_token']}":
            return self._json({"ok": False, "error": "unauthorized"}, 401)
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 4096)))
        except (ValueError, TypeError):
            return self._json({"ok": False, "error": "invalid_json"}, 400)
        host = str(body.get("advertise_host") or "").strip()
        if host and len(host) <= 253 and all(ch.isalnum() or ch in ".:-" for ch in host):
            config["advertise_host"] = host
        if body.get("simulator") in {"mujoco", "isaac"}:
            config["simulator"] = body["simulator"]
        CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
        CONFIG_PATH.chmod(0o600)
        self._json({"ok": True, "config": config})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"runtime {self.address_string()} {fmt % args}")


def main() -> None:
    config = load_config()
    if "--initialize" in sys.argv:
        print(CONFIG_PATH)
        return
    server = ThreadingHTTPServer((config["bind_host"], config["port"]), Handler)
    print(f"Render Studio Robotics Runtime listening on http://{config['bind_host']}:{config['port']}")
    server.serve_forever()


if __name__ == "__main__":
    main()
