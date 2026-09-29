# Render Studio Robotics Runtime

Local compute companion for Render Studio. It detects the host, exposes a local
dashboard and status API, and provides one execution boundary for LeRobot,
MuJoCo, and Isaac Lab jobs.

The runtime never commands physical hardware. Robot deployment remains behind
Render Studio's guarded Pi workflow.

## Install

```bash
./install.sh
```

Open `http://127.0.0.1:8460`. The installer creates a per-machine pairing token
under `~/.render3d-robotics-runtime/config.json` and installs a macOS LaunchAgent.

## API

- `GET /api/status` reports platform, compute, simulator, and training-tool readiness.
- `GET /api/config` returns the non-secret runtime configuration.
- `PUT /api/config` updates the advertised LAN host and preferred simulator.
- `POST /api/jobs/estimate` returns a transparent estimate from GPU hours and hourly rate.

Localhost is the default bind address. LAN binding is opt-in and requires the
pairing token in `Authorization: Bearer ...` for write requests.

