# CLAUDE.md — room-temperature-monitor

## What this app does
Distributed BLE poller that reads temperature, humidity, and battery from ThermoPro TP357 sensors and writes metrics to VictoriaMetrics for Grafana visualisation. Runs as a Docker container; multiple instances can be deployed across machines to cover sensors out of Bluetooth range of a single host.

## Stack
- Python 3.12
- bleak — BLE scanning
- thermopro-ble — TP357 advertisement decoding
- httpx — HTTP client (used by both poller and weather)
- Open-Meteo API — outdoor weather (free, no key required)
- Docker / Docker Compose
- VictoriaMetrics (external, shared)
- Grafana (external, shared)

## File map
```
poller/
  poller.py           ← main BLE scan + VictoriaMetrics write loop
  Dockerfile
  requirements.txt
  docker-compose.yml
  .env.example        ← template; copy to .env and fill in per host
weather/
  weather.py          ← polls Open-Meteo, writes outdoor_temperature + outdoor_humidity
  Dockerfile
  requirements.txt
  docker-compose.yml
  .env.example        ← template; copy to .env and fill in (LAT, LON, VM_URL)
scripts/
  check-secrets.sh    ← pre-commit hook: blocks .env commits
deploy.sh             ← deploys to local and/or remote host
.env.deploy.example   ← template for deploy.sh config
```

## Development workflow

Follow this sequence for **every** code change:

1. **Branch** — create a feature branch from main:
   ```bash
   git fetch origin && git checkout -b feature/<name> origin/main
   ```
2. **Implement** — make the code changes
3. **Self-review** — run the `review` skill on the diff; fix any real issues
4. **Test** — run the poller locally in scan-only mode to verify it starts cleanly
5. **PR** — push and open a pull request
6. **Deploy** — once merged, run `./deploy.sh` to push to all hosts

## Deployment

Configuration lives in two gitignored files (never committed):

- `poller/.env` — which devices to scan and where to write metrics (per host)
- `.env.deploy` — SSH details for remote deployment

Copy the examples and fill them in on each host:
```bash
cp poller/.env.example poller/.env
cp .env.deploy.example .env.deploy
```

Deploy:
```bash
./deploy.sh           # deploy to both hosts
./deploy.sh local     # deploy to this machine only
./deploy.sh remote    # deploy to remote host only
```

## Environment variables

### poller/.env

| Variable | Description | Default |
|---|---|---|
| `DEVICES` | Comma-separated BLE MAC addresses to scan | required |
| `VM_URL` | VictoriaMetrics HTTP endpoint | required |
| `POLL_INTERVAL_SECS` | Seconds between polls | `60` |

### weather/.env

| Variable | Description | Default |
|---|---|---|
| `LAT` | Latitude of location | required |
| `LON` | Longitude of location | required |
| `VM_URL` | VictoriaMetrics HTTP endpoint | required |
| `POLL_INTERVAL_SECS` | Seconds between polls | `900` |

> **Note:** `LAT` and `LON` are personal — keep `weather/.env` local and never commit it.

## Key design decisions
- Distributed scanning: one container per host, each scanning only the devices in range
- Poller writes directly to VictoriaMetrics — Prometheus is not involved
- Docker used for isolation; BLE access via host network + D-Bus mount
- Weather container polls Open-Meteo every 15 min; Grafana gauge queries use `last_over_time(...[20m])` to avoid staleness gaps between polls
