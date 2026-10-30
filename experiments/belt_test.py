"""Watch for LJJ-sports to appear, then immediately: init, ready, START, 5s, STOP."""
import asyncio
from bleak import BleakScanner, BleakClient
import hnk


async def main():
    print("watching for deck (power-cycle it now) ...", flush=True)
    dev = None
    sc = BleakScanner()
    await sc.start()
    for _ in range(90):
        devs = await BleakScanner.discover(timeout=1.0)
        hit = [d for d in devs if d.address == hnk.ADDR]
        if hit:
            dev = hit[0]
            break
    await sc.stop()
    if not dev:
        raise SystemExit("never appeared in 90s")
    print(f"appeared: {dev.address} {dev.name} — connecting", flush=True)
    c = BleakClient(dev, timeout=15.0)
    await c.connect()
    print("connected", flush=True)
    try:
        await asyncio.sleep(2.0)  # deck GATT stack needs a beat after boot-connect
        for attempt in range(4):
            try:
                await c.start_notify(hnk.FFB1, hnk.on_notify)
                break
            except OSError as e:
                print(f"  notify attempt {attempt+1} failed: {e}", flush=True)
                await asyncio.sleep(2)
        await c.write_gatt_char(hnk.FFB2, hnk.INIT, response=False)
        await asyncio.sleep(0.5)
        await c.write_gatt_char(hnk.FFB2, hnk.READY, response=False)
        await asyncio.sleep(0.5)
        await c.write_gatt_char(hnk.FFB2, hnk.START, response=False)
        print("-> START sent", flush=True)
        await asyncio.sleep(5)
        await c.write_gatt_char(hnk.FFB2, hnk.STOP, response=False)
        print("-> STOP sent", flush=True)
        await asyncio.sleep(4)
    finally:
        await c.disconnect()


asyncio.run(main())
