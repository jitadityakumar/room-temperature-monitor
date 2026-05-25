import asyncio
import logging
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
    f"&current=temperature_2m,relative_humidity_2m"
    f"&timezone=Europe%2FLondon"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def fetch_weather(client: httpx.AsyncClient) -> dict[str, float]:
    resp = await client.get(OPEN_METEO_URL, timeout=10)
    resp.raise_for_status()
    current = resp.json()["current"]
    return {
        "temperature": float(current["temperature_2m"]),
        "humidity": float(current["relative_humidity_2m"]),
    }


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
