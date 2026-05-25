# room-temperature-monitor

Distributed BLE poller for ThermoPro TP357 temperature and humidity sensors. Reads sensor advertisements passively over Bluetooth, writes metrics to VictoriaMetrics, and visualises them in Grafana.

Designed to run across multiple hosts — useful when sensors are spread across rooms out of Bluetooth range of a single machine.

## Prerequisites

- Docker and Docker Compose on each host machine
- A running VictoriaMetrics instance accessible from each host
- Bluetooth adapter (`hci0`) on each host
- BlueZ installed and running on each host (`sudo apt install bluez`)

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

### 3. Configure the outdoor weather poller (optional)

```bash
cp weather/.env.example weather/.env
```

Edit `weather/.env`:

```
LAT=your-latitude
LON=your-longitude
VM_URL=http://your-victoriametrics-host:8428
POLL_INTERVAL_SECS=900
```

Start it:

```bash
cd weather && docker compose up -d --build
```

Fetches current temperature and humidity from [Open-Meteo](https://open-meteo.com) every 15 minutes. No API key required.

### 4. Configure deployment (optional)

```bash
cp .env.deploy.example .env.deploy
```

Edit `.env.deploy` with your SSH details for the remote host.

### 5. Start the poller

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

### Sensor metrics (label: `mac`)

| Metric | Description |
|---|---|
| `thermopro_temperature` | Temperature in °C |
| `thermopro_humidity` | Relative humidity % |
| `thermopro_battery` | Battery level % (1, 50, or 100 for TP357) |
| `thermopro_signal_strength` | BLE signal strength in dBm |

### Outdoor weather metrics

| Metric | Description |
|---|---|
| `outdoor_temperature` | Outdoor temperature in °C |
| `outdoor_humidity` | Outdoor relative humidity % |

## Finding your sensor MAC addresses

```bash
sudo hcitool lescan
```

Look for devices named `TP357 (XXXX)`.
