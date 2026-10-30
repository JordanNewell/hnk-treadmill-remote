"""Probe FMS: read feature/speed-range, request control, listen to responses."""
import asyncio
from bleak import BleakScanner, BleakClient

ADDR = "C4:F1:02:05:4A:C2"
CTRL = "00002ad9-0000-1000-8000-00805f9b34fb"  # Fitness Machine Control Point
DATA = "00002acd-0000-1000-8000-00805f9b34fb"  # Treadmill Data
STATUS = "00002ada-0000-1000-8000-00805f9b34fb"  # Fitness Machine Status
FEATURE = "00002ad3-0000-1000-8000-00805f9b34fb"
SPEEDRANGE = "00002acc-0000-1000-8000-00805f9b34fb"


def on_notify(ch, raw: bytearray):
    print(f"  <- {ch.uuid[4:8]}: {raw.hex()}")


def on_indicate(ch):
    print(f"  <- CTRL response: {bytes(ch).hex()}")


async def main():
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=10.0)
    if not dev:
        print("treadmill not advertising"); return
    async with BleakClient(dev) as c:
        print("connected:", c.is_connected)
        feat = await c.read_gatt_char(FEATURE)
        sr = await c.read_gatt_char(SPEEDRANGE)
        print(f"feature:   {feat.hex()}")
        print(f"speedrange raw: {sr.hex()}")
        if len(sr) >= 4:
            import struct
            mn, mx = struct.unpack("<HH", sr[:4])
            print(f"  supported speed: {mn/100} – {mx/100} km/h")
        await c.start_notify(DATA, on_notify)
        await c.start_notify(STATUS, on_notify)
        await c.start_notify(CTRL, on_indicate)
        print("-> Request Control (0x00)")
        await c.write_gatt_char(CTRL, b"\x00", response=True)
        await asyncio.sleep(2)
        print("-> Reset (0x01)")
        await c.write_gatt_char(CTRL, b"\x01", response=True)
        await asyncio.sleep(2)
        print("listening 5s for treadmill data ...")
        await asyncio.sleep(5)
        await c.stop_notify(DATA)


asyncio.run(main())
