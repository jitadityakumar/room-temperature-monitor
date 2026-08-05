import asyncio
import logging
import math
import os
import time

import httpx

LAT: str = os.environ["LAT"]
LON: str = os.environ["LON"]
VM_URL: str = os.environ["VM_URL"].rstrip("/")
POLL_INTERVAL: int = int(os.environ.get("POLL_INTERVAL_SECS", "900"))

OPEN_METEO_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
    f"precipitation,rain,showers,snowfall"
    f"&wind_speed_unit=ms"
    f"&timezone=Europe%2FLondon"
)

FEELS_LIKE_MIN_C = -5.0
FEELS_LIKE_MAX_C = 45.0


def feels_like(temp_c: float, rh: float, wind_ms: float) -> float | None:
    if not (FEELS_LIKE_MIN_C <= temp_c <= FEELS_LIKE_MAX_C):
        return None
    rho = (rh / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))
    return temp_c + 0.33 * rho - 0.70 * wind_ms - 4.00


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def fetch_weather(client: httpx.AsyncClient) -> dict[str, float]:
    resp = await client.get(OPEN_METEO_URL, timeout=10)
    resp.raise_for_status()
    current = resp.json()["current"]
    temp = float(current["temperature_2m"])
    rh = float(current["relative_humidity_2m"])
    readings: dict[str, float] = {
        "temperature": temp,
        "humidity": rh,
    }
    for metric in ("precipitation", "rain", "showers", "snowfall"):
        raw_value = current.get(metric)
        if raw_value is not None:
            readings[metric] = float(raw_value)
        else:
            log.warning("%s missing from Open-Meteo response; skipping", metric)
    raw_wind = current.get("wind_speed_10m")
    wind_ms = float(raw_wind) if raw_wind is not None else None
    if wind_ms is not None:
        fl = feels_like(temp, rh, wind_ms)
        if fl is not None:
            readings["feels_like"] = round(fl, 1)
    else:
        log.warning("wind_speed_10m missing from Open-Meteo response; skipping feels_like")
    return readings


async def write_to_vm(client: httpx.AsyncClient, readings: dict[str, float]) -> None:
    ts_ms = int(time.time() * 1000)
    lines = [
        f'outdoor_{metric}{{}} {value} {ts_ms}'
        for metric, value in readings.items()
    ]
    resp = await client.post(
        f"{VM_URL}/api/v1/import/prometheus",
        content="\n".join(lines) + "\n",
        headers={"Content-Type": "text/plain"},
        timeout=10,
    )
    resp.raise_for_status()
    log.info("Wrote %d metrics to VictoriaMetrics: %s", len(lines), readings)


async def main() -> None:
    log.info("Starting weather poller | interval=%ds", POLL_INTERVAL)
    async with httpx.AsyncClient() as client:
        while True:
            start = time.monotonic()
            try:
                readings = await fetch_weather(client)
                await write_to_vm(client, readings)
            except Exception:
                log.exception("Poll cycle failed")
            await asyncio.sleep(max(0, POLL_INTERVAL - (time.monotonic() - start)))


asyncio.run(main())
