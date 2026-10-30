"""Passive sniff of the LJJ-sports control interface (FFB0 + Tencent FEE7)."""
import asyncio
from bleak import BleakClient

ADDR = "C4:F1:02:06:4A:C2"
FFB1 = "0000ffb1-0000-1000-8000-00805f9b34fb"  # notify
FFB2 = "0000ffb2-0000-1000-8000-00805f9b34fb"  # write-without-response
FEC8 = "0000fec8-0000-1000-8000-00805f9b34fb"  # indicate
FEC9 = "0000fec9-0000-1000-8000-00805f9b34fb"  # read


def mk(tag):
    def cb(ch, raw):
        print(f"  <- {tag} {bytes(raw).hex()}")
    return cb


async def main():
    dev_addr = ADDR
    from bleak import BleakScanner
    dev = await BleakScanner.find_device_by_address(dev_addr, timeout=10.0)
    if not dev:
        print("LJJ-sports not advertising"); return
    async with BleakClient(dev) as c:
        print("connected to LJJ-sports:", c.is_connected)
        try:
            r = await c.read_gatt_char(FEC9)
            print("FEC9 read:", r.hex())
        except Exception as e:
            print("FEC9 read failed:", e)
        await c.start_notify(FFB1, mk("FFB1"))
        await c.start_notify(FEC8, mk("FEC8"))
        print("listening 12s (no writes yet) ...")
        await asyncio.sleep(12)
        # gentle probe: single null-ish byte to see if it reacts
        try:
            await c.write_gatt_char(FFB2, b"\x55", response=False)
            print("-> FFB2 wrote 55")
        except Exception as e:
            print("FFB2 write failed:", e)
        await asyncio.sleep(6)
        print("done")


asyncio.run(main())
