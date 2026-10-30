# hnk-treadmill-remote

Self-hosted Bluetooth LE remote for "HNK-family" walking pads — the generic
under-desk treadmills sold as Abonow / LIJIUJIA (LJJ) / and a dozen other
Amazon names. Built after losing the IR remote for an **LJJ P6**; the device
speaks an unpublished vendor protocol, which is documented here for the first
time, along with a working controller.

Replaces the remote with a web page served from your own machine — no vendor
account, no cloud, no app.

## What's here

| File | Purpose |
|---|---|
| `hnk.py` | CLI controller: `start`, `stop`, `speed N`, `watch` |
| `hnk_serve.py` | Persistent server: holds the BLE link, serves a button page + JSON API |
| `experiments/` | The reverse-engineering trail — GATT discovery, dead ends, probes |
| `experiments/apk-analysis/` | Androguard scripts that pulled the protocol out of the official FITIME APK |

Requires Python 3.10+ and `bleak` (`pip install bleak`). Works on any machine
with Bluetooth LE (Windows/macOS/Linux).

## Hardware notes (LJJ P6, may generalize)

The deck exposes **two** BLE interfaces:

- `…:05` `LJJ-XXXXXX` — standard **Fitness Machine Service (0x1826)**.
  Telemetry works over standard FTMS, but the control point is
  **hard-locked**: every command returns result `0x05` regardless of unlock
  frames (including qdomyos-zwift's YPOO-M5 unlock `01 00 02 02 00 05 01 01`
  on `d18d2c10-c44c-11e8-a355-529269fb1459` — this deck ignores it).
- `…:06` `LJJ-sports` — service **0xFFB0**: `FFB1` notify, `FFB2`
  write-without-response. **All control happens here.**

Gotchas learned the hard way:

- The deck only advertises for ~1 minute after its **rocker switch** is
  flipped. Tapping the display wakes the console, not the BLE radio.
- One BLE client at a time. The link drops after long idle; re-send the
  READY frame periodically to hold it (the server does this every 45 s).

## Protocol (HNK family, reverse-engineered from the FITIME APK)

Session init after connect:

```
1. subscribe to FFB1 notifications
2. write single byte 0x88 to FFB2
3. wait 500 ms
4. write READY frame (below)
```

Controller frames (7 bytes), used for READY/PAUSE-style ops:

```
[cmd, b5, b6, 0x00, 0x00,
 ((cmd + b5) ^ b6) + 37 & 0xFF,      # checksum 1
 ((cmd ^ b5) + b6) + 2 & 0xFF]       # checksum 2
READY = getControllerBytes(7) -> 07 00 00 00 00 2C 09
PAUSE = getControllerBytes(5) -> 05 00 00 00 00 2A 07
```

Belt commands (9-byte frames, written to FFB2):

```
START = FA EF 11 00 00 00 00 F3 04    (belt starts at its default 0.8 km/h)
STOP  = FA EF 11 00 00 00 00 F4 05
SPEED = FA EF 11 00 [incline] 00 [speed] 11 [ck]
         ck = (incline + 17 + speed + 17) & 0xFF
         speed in 0.1 km/h units (e.g. 30 = 3.0 km/h)
```

Telemetry frames on FFB1 (`FA EF <type> …`):

| Type | Meaning |
|---|---|
| `0x90` | device capability block (max incline, min/max speed) |
| `0x91` | run status — byte 6 == `0xF3` while the belt is running |
| `0x92` | current speed (byte 6, 0.1 km/h) and incline (byte 4) |
| `0x95` | workout stats — time (bytes 3–4, s), distance (bytes 5–6, dm), calories (byte 8) |

The deck's other interface also speaks a `FA F1`-framed protocol over the
Tencent **FEE7** service (`FEC7`/`FEC8`) — duplicates of the above, unused
by this project.

## Usage

```bash
pip install bleak
python hnk_serve.py 8099        # then open http://localhost:8099
```

Point a reverse proxy at it (the author exposes it over Tailscale Serve) and
any phone on the network becomes the remote. Edit `ADDR` at the top of
`hnk.py` to your deck's `LJJ-sports` address (find it with any BLE scanner).

## Safety

You are controlling a physical belt with unvetted vendor firmware. Stand
clear of the deck when testing commands, keep the physical stop / rocker
switch reachable, and don't set speeds you wouldn't step onto. This is a
hobby project with zero warranties.

## Related

- [jerome-salanhac/ljj-treadmill-walkpad-0811fe-web-interface](https://github.com/jerome-salanhac/ljj-treadmill-walkpad-0811fe-web-interface) — web controller for the FitShow-protocol LJJ models (different firmware family)
- [cagnulein/qdomyos-zwift](https://github.com/cagnulein/qdomyos-zwift) — YPOO-M5 FTMS driver (adjacent hardware, different unlock)
