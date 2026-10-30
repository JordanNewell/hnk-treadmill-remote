"""Scan for the LJJ walking pad and dump its GATT services/characteristics."""
import asyncio
from bleak import BleakScanner, BleakClient

NAME_PREFIX = "ljj"


async def main():
    print("Scanning 8s ...")
    devices = await BleakScanner.discover(timeout=8.0)
    targets = [d for d in devices if d.name and d.name.lower().startswith(NAME_PREFIX)]
    if not targets:
        print("No ljj* device found. Is the treadmill powered on / display awake?")
        print("Nearby devices:")
        for d in devices:
            if d.name:
                print(f"  {d.address}  {d.name}")
        return

    for d in targets:
        print(f"\n=== {d.name} @ {d.address} ===")
        async with BleakClient(d) as client:
            print("Connected:", client.is_connected)
            for svc in client.services:
                print(f"\nService {svc.uuid}  ({svc.description or '?'})")
                for ch in svc.characteristics:
                    props = ",".join(ch.properties)
                    val = ""
                    if "read" in ch.properties:
                        try:
                            raw = await client.read_gatt_char(ch)
                            txt = raw.decode("utf-8", "replace").strip()
                            val = f' = "{txt}"' if txt else f" = {raw.hex()}"
                        except Exception as e:
                            val = f" (read failed: {e})"
                    print(f"  char {ch.uuid}  [{props}]{val}")


asyncio.run(main())
