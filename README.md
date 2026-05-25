# room-temperature-monitor

Distributed BLE poller for ThermoPro TP357 temperature and humidity sensors. Reads sensor advertisements passively over Bluetooth, writes metrics to VictoriaMetrics, and visualises them in Grafana.

Designed to run across multiple hosts — useful when sensors are spread across rooms out of Bluetooth range of a single machine.

## Prerequisites

- Docker and Docker Compose on each host machine
- A running VictoriaMetrics instance accessible from each host
- Bluetooth adapter (`hci0`) on each host

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/jitadityakumar/room-temperature-monitor.git
cd room-temperature-monitor
```

### 2. Configure the poller

```bash
cp poller/.env.example poller/.env
```

Edit `poller/.env`:

```
DEVICES=AA:BB:CC:DD:EE:FF,AA:BB:CC:DD:EE:FF
VM_URL=http://your-victoriametrics-host:8428
POLL_INTERVAL_SECS=60
```

Set `DEVICES` to the MAC addresses of the sensors this host can reach. Set `VM_URL` to your VictoriaMetrics endpoint.

### 3. Configure deployment (optional)

```bash
cp .env.deploy.example .env.deploy
```

Edit `.env.deploy` with your SSH details for the remote host.

### 4. Start the poller

```bash
cd poller && docker compose up -d --build
```

## Deployment

After making changes, deploy to all hosts:

```bash
./deploy.sh           # deploy to both local and remote
./deploy.sh local     # local only
./deploy.sh remote    # remote only
```

## Metrics written to VictoriaMetrics

| Metric | Description |
|---|---|
| `thermo_temperature_celsius` | Temperature in °C |
| `thermo_humidity_percent` | Relative humidity % |
| `thermo_battery_percent` | Battery level % |
| `thermo_rssi_dbm` | BLE signal strength in dBm |

Labels: `mac`, `device`

## Finding your sensor MAC addresses

```bash
sudo hcitool lescan
```

Look for devices named `TP357 (XXXX)`.
