"""One-connection diagnostic sequence: control -> start -> speed -> watch."""
import asyncio
import sys
import tread


async def main():
    client = await tread.connect()
    try:
        await tread.send(client, b"\x00", wait=3.0, label="request-control")
        await tread.send(client, b"\x07", wait=3.0, label="START")
        await tread.send(client, b"\x02" + __import__("struct").pack("<H", 200),
                         wait=3.0, label="speed 2.0")
        await asyncio.sleep(2)
        await tread.snap(client)
        await asyncio.sleep(4)
        await tread.snap(client)
    finally:
        await client.disconnect()


asyncio.run(main())
