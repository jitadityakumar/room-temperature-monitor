import asyncio
import logging
import math
import os
import time

import httpx
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bluetooth_sensor_state_data import BluetoothServiceInfoBleak
from thermopro_ble import ThermoProBluetoothDeviceData

DEVICES: set[str] = {mac.strip().upper() for mac in os.environ["DEVICES"].split(",")}
VM_URL: str = os.environ["VM_URL"].rstrip("/")
POLL_INTERVAL: int = int(os.environ.get("POLL_INTERVAL_SECS", "60"))
SCAN_DURATION: int = 10

FEELS_LIKE_MIN_C = 16.0
FEELS_LIKE_MAX_C = 40.0


def feels_like(temp_c: float, rh: float) -> float | None:
    if not (FEELS_LIKE_MIN_C <= temp_c <= FEELS_LIKE_MAX_C):
        return None
    rho = (rh / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))
    return temp_c + 0.33 * rho - 4.00


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def parse_advertisement(device: BLEDevice, adv: AdvertisementData) -> dict[str, float]:
    service_info = BluetoothServiceInfoBleak.from_device_and_advertisement_data(
        device=device,
        advertisement_data=adv,
        source="hci0",
        time=time.monotonic(),
        connectable=False,
    )
    update = ThermoProBluetoothDeviceData().update(service_info)
    return {
        key.key: float(value.native_value)
        for key, value in update.entity_values.items()
        if value.native_value is not None
    }


async def scan_once() -> dict[str, dict[str, float]]:
    results: dict[str, dict[str, float]] = {}
    seen: set[str] = set()

    def on_advertisement(device: BLEDevice, adv: AdvertisementData) -> None:
        mac = device.address.upper()
        if mac not in DEVICES or mac in seen:
            return
        try:
            readings = parse_advertisement(device, adv)
        except Exception:
            log.exception("Failed to parse advertisement from %s", mac)
            return
        if readings:
            results[mac] = readings
            seen.add(mac)
            log.info("  %s: %s", mac, readings)

    async with BleakScanner(detection_callback=on_advertisement):
        await asyncio.sleep(SCAN_DURATION)

    return results


async def write_to_vm(results: dict[str, dict[str, float]]) -> None:
    ts_ms = int(time.time() * 1000)
    lines = [
        f'thermopro_{metric}{{mac="{mac}"}} {value} {ts_ms}'
        for mac, readings in results.items()
        for metric, value in readings.items()
    ]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{VM_URL}/api/v1/import/prometheus",
            content="\n".join(lines) + "\n",
            headers={"Content-Type": "text/plain"},
            timeout=10,
        )
    resp.raise_for_status()
    log.info("Wrote %d metrics to VictoriaMetrics", len(lines))


async def main() -> None:
    log.info(
        "Starting poller | devices=%s | vm=%s | interval=%ds",
        DEVICES,
        VM_URL,
        POLL_INTERVAL,
    )
    while True:
        start = time.monotonic()
        try:
            results = await scan_once()
            if results:
                for readings in results.values():
                    temp = readings.get("temperature")
                    rh = readings.get("humidity")
                    if temp is not None and rh is not None:
                        fl = feels_like(temp, rh)
                        if fl is not None:
                            readings["feels_like"] = round(fl, 1)
                await write_to_vm(results)
            else:
                log.warning("No readings from any target device")
        except Exception:
            log.exception("Poll cycle failed")
        await asyncio.sleep(max(0, POLL_INTERVAL - (time.monotonic() - start)))


asyncio.run(main())
