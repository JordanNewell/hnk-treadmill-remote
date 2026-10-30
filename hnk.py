"""HNK-family (LJJ P6) walking pad controller — protocol from FITIME TreadMill_HNK.

Usage: hnk.py start | stop | speed N | watch [SECS] | status
"""
import asyncio
import sys
from bleak import BleakScanner, BleakClient

ADDR = "C4:F1:02:06:4A:C2"  # LJJ-sports interface
FFB1 = "0000ffb1-0000-1000-8000-00805f9b34fb"  # notify (device -> app)
FFB2 = "0000ffb2-0000-1000-8000-00805f9b34fb"  # write (app -> device)

START = bytes([0xFA, 0xEF, 0x11, 0x00, 0x00, 0x00, 0x00, 0xF3, 0x04])
STOP = bytes([0xFA, 0xEF, 0x11, 0x00, 0x00, 0x00, 0x00, 0xF4, 0x05])
INIT = bytes([0x88])


def controller_bytes(cmd: int, b5: int = 0, b6: int = 0) -> bytes:
    return bytes([cmd & 0xFF, b5 & 0xFF, b6 & 0xFF, 0, 0,
                  ((cmd + b5) ^ b6) + 37 & 0xFF,
                  ((cmd ^ b5) + b6) + 2 & 0xFF])


READY = controller_bytes(7)  # app's ready() on connect
PAUSE = controller_bytes(5)


def speed_frame(speed_dmph: int, incline: int = 0) -> bytes:
    ck = (incline + 17 + speed_dmph + 17) & 0xFF
    return bytes([0xFA, 0xEF, 0x11, 0x00, incline & 0xFF, 0x00, speed_dmph & 0xFF, 0x11, ck])


state = {"last": None}


def on_notify(ch, raw: bytearray):
    b = bytes(raw)
    state["last"] = b
    if len(b) >= 4 and b[0] == 0xFA and b[1] == 0xEF:
        t = b[2]
        if t == 0x91:
            running = len(b) > 6 and b[6] == 0xF3
            print(f"  <- status: {'RUNNING' if running else 'stopped'} raw={b.hex()}")
        elif t == 0x92:
            spd = b[6] if len(b) > 6 else 0
            inc = b[4] if len(b) > 4 else 0
            print(f"  <- speed {spd/10:.1f} km/h incline {inc} raw={b.hex()}")
        elif t == 0x95:
            tsec = (b[3] << 8) | b[4] if len(b) > 4 else 0
            dist = (b[5] << 8) | b[6] if len(b) > 6 else 0
            cal = b[8] if len(b) > 8 else 0
            print(f"  <- stats: time {tsec}s dist {dist*10}m cal {cal} raw={b.hex()}")
        else:
            print(f"  <- {b.hex()}")
    else:
        print(f"  <- {b.hex()}")


async def connect(retries=4):
    dev = None
    for i in range(retries):
        dev = await BleakScanner.find_device_by_address(ADDR, timeout=8.0)
        if dev:
            break
        print(f"  (not advertising, retry {i+1}/{retries} — deck may be settling)")
        await asyncio.sleep(3)
    if not dev:
        raise SystemExit("LJJ-sports not advertising")
    c = BleakClient(dev)
    await c.connect()
    await c.start_notify(FFB1, on_notify)
    await c.write_gatt_char(FFB2, INIT, response=False)  # app init(): 0x88
    await asyncio.sleep(0.5)
    await c.write_gatt_char(FFB2, READY, response=False)
    await asyncio.sleep(0.5)
    return c


async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    c = await connect()
    try:
        if cmd == "start":
            await c.write_gatt_char(FFB2, START, response=False)
            print("-> START")
        elif cmd == "stop":
            await c.write_gatt_char(FFB2, STOP, response=False)
            print("-> STOP")
        elif cmd == "speed":
            kmh = float(sys.argv[2])
            await c.write_gatt_char(FFB2, speed_frame(int(round(kmh * 10))), response=False)
            print(f"-> speed {kmh}")
        elif cmd in ("status", "watch"):
            secs = float(sys.argv[2]) if len(sys.argv) > 2 and cmd == "watch" else 6.0
            print(f"listening {secs}s ...")
            await asyncio.sleep(secs)
        else:
            print(__doc__)
    finally:
        await c.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
