"""Handshake probe: echo device token frames back on FEC7/FFB2, watch responses."""
import asyncio
from bleak import BleakScanner, BleakClient

ADDR = "C4:F1:02:06:4A:C2"
FFB1 = "0000ffb1-0000-1000-8000-00805f9b34fb"
FFB2 = "0000ffb2-0000-1000-8000-00805f9b34fb"
FEC7 = "0000fec7-0000-1000-8000-00805f9b34fb"
FEC8 = "0000fec8-0000-1000-8000-00805f9b34fb"

frames = []
token = {"data": None}


def mk(tag):
    def cb(ch, raw):
        b = bytes(raw)
        frames.append((tag, b))
        print(f"  <- {tag} {b.hex()}")
        # device token frame: fa f1 30 <payload> <cksum>
        if len(b) >= 4 and b[0] == 0xFA and b[2] == 0x30:
            token["data"] = b
    return cb


def cksum(b: bytes) -> bytes:
    """prefix fa + cmd assumed; cksum = sum(bytes[2:-1]) & 0xff"""
    return bytes([sum(b[2:-1]) & 0xFF])


async def main():
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=10.0)
    if not dev:
        print("not advertising"); return
    async with BleakClient(dev) as c:
        await c.start_notify(FFB1, mk("FFB1"))
        await c.start_notify(FEC8, mk("FEC8"))
        print("collecting token for 8s ...")
        await asyncio.sleep(8)
        if not token["data"]:
            print("no token frame seen; aborting echo")
            return
        tok = token["data"]
        print(f"token frame: {tok.hex()}")
        candidates = []
        # echo token back with cmd f0 and f1, on both chars
        for cmd in (0xF0, 0xF1):
            body = bytes([0xFA, cmd]) + tok[2:]
            candidates.append(("FEC7", body))
            candidates.append(("FFB2", body))
        # simple query frames
        for t in (0x10, 0x20):
            for cmd in (0xF0, 0xF1):
                body = bytes([0xFA, cmd, t, 0x00, 0x00, 0x00, 0x00, 0x00])
                body += cksum(body)
                candidates.append(("FEC7", body))
        for charname, frame in candidates:
            ch = FEC7 if charname == "FEC7" else FFB2
            try:
                await c.write_gatt_char(ch, frame, response=(charname == "FEC7"))
                print(f"-> {charname} {frame.hex()}")
            except Exception as e:
                print(f"-> {charname} {frame.hex()} FAILED: {e}")
            await asyncio.sleep(2)
        print("listening 10s for reactions ...")
        await asyncio.sleep(10)


asyncio.run(main())
