"""Persistent walking-pad remote server.

Grabs the LJJ-sports BLE interface whenever it advertises, holds the link,
serves a button page + JSON API.

  python hnk_serve.py [PORT]        (default 8099)

  GET /                      button page
  GET /api/cmd?a=start       start belt
  GET /api/cmd?a=stop        stop belt
  GET /api/cmd?a=speed&v=3.0 set speed km/h
  GET /api/status            JSON snapshot
"""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import hnk
from bleak import BleakScanner, BleakClient

CMD_QUEUE = []  # (action, value)
STATE = {"connected": False, "speed": 0.0, "running": False,
         "time_s": 0, "dist_dm": 0, "cal": 0, "last_frame": ""}


class Deck:
    def __init__(self):
        self.client = None

    async def run(self):
        while True:
            try:
                if not self.client or not self.client.is_connected:
                    await self.connect()
                await self.pump()
            except Exception as e:
                print(f"[deck] {type(e).__name__}: {e}", flush=True)
                STATE["connected"] = False
                self.client = None
                await asyncio.sleep(5)
            await asyncio.sleep(0.5)

    async def connect(self):
        dev = None
        for i in range(6):
            dev = await BleakScanner.find_device_by_address(hnk.ADDR, timeout=6.0)
            if dev:
                break
            print(f"[deck] waiting for advertisement ({i+1}/6) ...", flush=True)
            await asyncio.sleep(4)
        if not dev:
            return
        c = BleakClient(dev, timeout=15.0)
        await c.connect()
        await asyncio.sleep(1.5)
        for attempt in range(4):
            try:
                await c.start_notify(hnk.FFB1, on_ble_frame)
                break
            except OSError as e:
                print(f"[deck] notify retry {attempt+1}: {e}", flush=True)
                await asyncio.sleep(2)
        await c.write_gatt_char(hnk.FFB2, hnk.INIT, response=False)
        await asyncio.sleep(0.5)
        await c.write_gatt_char(hnk.FFB2, hnk.READY, response=False)
        await asyncio.sleep(0.3)
        self.client = c
        STATE["connected"] = True
        print("[deck] connected + initialized", flush=True)

    async def pump(self):
        if not self.client or not self.client.is_connected:
            return
        last_keepalive = asyncio.get_event_loop().time()
        while True:
            while CMD_QUEUE:
                action, value = CMD_QUEUE.pop(0)
                try:
                    if action == "start":
                        await self.client.write_gatt_char(hnk.FFB2, hnk.START, response=False)
                        print("[deck] START", flush=True)
                    elif action == "stop":
                        await self.client.write_gatt_char(hnk.FFB2, hnk.STOP, response=False)
                        print("[deck] STOP", flush=True)
                    elif action == "speed":
                        frame = hnk.speed_frame(int(round(value * 10)))
                        await self.client.write_gatt_char(hnk.FFB2, frame, response=False)
                        print(f"[deck] speed {value}", flush=True)
                    last_keepalive = asyncio.get_event_loop().time()
                    await asyncio.sleep(0.4)
                except Exception as e:
                    print(f"[deck] cmd {action} failed: {e}", flush=True)
                    raise
            # keepalive: re-send READY every 45s idle so the deck doesn't drop the link
            now = asyncio.get_event_loop().time()
            if now - last_keepalive > 45:
                try:
                    await self.client.write_gatt_char(hnk.FFB2, hnk.READY, response=False)
                    print("[deck] keepalive", flush=True)
                except Exception as e:
                    print(f"[deck] keepalive failed: {e}", flush=True)
                    raise
                last_keepalive = now
            await asyncio.sleep(0.5)


def on_ble_frame(ch, raw: bytearray):
    b = bytes(raw)
    STATE["last_frame"] = b.hex()
    if len(b) >= 7 and b[0] == 0xFA and b[1] == 0xEF:
        t = b[2]
        if t == 0x91:
            STATE["running"] = len(b) > 6 and b[6] == 0xF3
        elif t == 0x92:
            STATE["speed"] = b[6] / 10.0 if len(b) > 6 else 0.0
        elif t == 0x95 and len(b) >= 9:
            STATE["time_s"] = (b[3] << 8) | b[4]
            STATE["dist_dm"] = (b[5] << 8) | b[6]
            STATE["cal"] = b[8]


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Treadmill</title><style>
body{background:#0A0A0A;color:#fff;font-family:monospace;display:flex;
flex-direction:column;align-items:center;gap:16px;padding:24px;margin:0}
button{background:#0F0F0F;color:#fff;border:1px solid #1F1F1F;border-radius:12px;
font-size:22px;padding:20px 0;width:90vw;max-width:360px;font-family:inherit}
button:active{border-color:#00FF41;color:#00FF41}
#speed{font-size:56px;color:#00FF41;margin:8px 0}
#st{color:#A0A0A0;font-size:13px}
.row{display:flex;gap:12px;width:90vw;max-width:360px}
.row button{width:50%;font-size:30px;padding:14px 0}
</style></head><body>
<div id=st>connecting...</div>
<div id=speed>0.0</div>
<button onclick="c('start')">START</button>
<div class=row><button onclick="bump(-0.5)">&minus;</button>
<button onclick="bump(0.5)">+</button></div>
<button onclick="c('stop')" style="border-color:#5a1f1f">STOP</button>
<script>
let v=0;
async function c(a){await fetch('api/cmd?a='+a)}
async function bump(d){v=Math.max(0,Math.min(12,v+d));
await fetch('api/cmd?a=speed&v='+v);show()}
function show(){document.getElementById('speed').textContent=v.toFixed(1)}
setInterval(async()=>{const r=await(await fetch('api/status')).json();
document.getElementById('speed').textContent=r.speed.toFixed(1);v=r.speed;
document.getElementById('st').textContent=(r.connected?'connected':'NOT CONNECTED')
+' | '+(r.running?'RUNNING':'stopped')+' | '+r.time_s+'s | '+(r.dist_dm/100).toFixed(2)+' km-ish m | '+r.cal+' cal'},1500)
show()</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/")
        if p.endswith("api/status") or p == "/status":
            self._json(STATE)
            return
        if p.endswith("api/cmd") or p == "/cmd":
            params = dict(q.split("=", 1) for q in self.path.split("?")[1].split("&")
                          if "=" in q)
            a = params.get("a", "")
            if a == "speed":
                CMD_QUEUE.append(("speed", float(params.get("v", 0))))
            elif a in ("start", "stop"):
                CMD_QUEUE.append((a, None))
            else:
                return self._json({"error": "bad action"})
            self._json({"ok": True})
            return
        # any other path: serve the page (root, /treadmill, stale absolute fetches)
        body = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    ThreadingHTTPServer.allow_reuse_address = False  # refuse double-bind: two servers = split-brain
    threading.Thread(target=lambda: ThreadingHTTPServer(
        ("127.0.0.1", port), Handler).serve_forever(), daemon=True).start()
    print(f"[http] http://127.0.0.1:{port}", flush=True)
    await Deck().run()


if __name__ == "__main__":
    import sys
    import logging
    logging.basicConfig(
        filename="E:/dev/projects/ljj-ble-bridge/hnk_serve.log",
        level=logging.INFO, format="%(asctime)s %(message)s")
    asyncio.run(main())
