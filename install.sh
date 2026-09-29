#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
state_dir="$HOME/.render3d-robotics-runtime"
launch_dir="$HOME/Library/LaunchAgents"
label="app.render3d.robotics-runtime"
plist="$launch_dir/$label.plist"

mkdir -p "$state_dir" "$launch_dir"
chmod 700 "$state_dir"
python3 "$repo_dir/runtime_server.py" --initialize >/dev/null

python3 - "$repo_dir" "$plist" <<'PY'
import plistlib, sys
from pathlib import Path
repo, target = sys.argv[1:]
payload = {
    "Label": "app.render3d.robotics-runtime",
    "ProgramArguments": ["/usr/bin/python3", str(Path(repo) / "runtime_server.py")],
    "RunAtLoad": True,
    "KeepAlive": True,
    "StandardOutPath": str(Path.home() / ".render3d-robotics-runtime/runtime.log"),
    "StandardErrorPath": str(Path.home() / ".render3d-robotics-runtime/runtime.err.log"),
}
Path(target).write_bytes(plistlib.dumps(payload))
PY

launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$plist"
echo "Installed. Open http://127.0.0.1:8460"
