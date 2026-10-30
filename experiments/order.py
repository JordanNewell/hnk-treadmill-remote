"""Try alternate orderings / vendor char to find what unlocks control."""
import asyncio
import struct
from bleak import BleakScanner, BleakClient
import tread

VENDOR = "d18d2c10-c44c-11e8-a355-529269fb1459"
STATUS = "00002ada-0000-1000-8000-00805f9b34fb"


async def main():
    client = await tread.connect()
    try:
        await client.start_notify(STATUS, lambda ch, d: print(f"  <- status: {bytes(d).hex()}"))
        # A: speed first, then start, no request-control
        await tread.send(client, b"\x02" + struct.pack("<H", 200), wait=2.0, label="A: speed 2.0 (no ctrl)")
        # B: bare start again
        await tread.send(client, b"\x07", wait=2.0, label="B: START (no ctrl)")
        # C: pause/stop opcodes (should be safe; belt is stopped)
        await tread.send(client, b"\x08\x02", wait=1.5, label="C: pause")
        await tread.send(client, b"\x08\x01", wait=1.5, label="C: stop")
        # D: vendor char — probe with a few plausible frames (auto-stop framing)
        for payload in [b"\x00", b"\x01", b"\xff\x01\x00", b"\xaa\x05\x01\x00\x00\x55"]:
            try:
                await client.write_gatt_char(VENDOR, payload, response=True)
                print(f"[vendor {payload.hex()}] write ok")
                await asyncio.sleep(1.0)
            except Exception as e:
                print(f"[vendor {payload.hex()}] {e}")
                break
        await asyncio.sleep(2)
        await tread.snap(client)
    finally:
        await client.disconnect()


asyncio.run(main())
