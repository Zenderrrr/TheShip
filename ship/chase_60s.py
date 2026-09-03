#!/usr/bin/env python3
"""
================================================================================
     THE SHIP — DIRECT RABBITMQ SCANNER AUTOPILOT PURSUIT (60s)
================================================================================
1. Bridges Port 2014 -> 5672 to receive live scanner broadcasts.
2. Subscribes to RabbitMQ 'scanner/detected_objects' to get G-Station 3-4's live position.
3. Continuously commands Autopilot (/set_target) to intercept & pursue G-Station 3-4.
4. Maintains proximity (< 25 units) for 60 consecutive seconds.
"""

import time
import math
import sys
import os
import threading
import json
import urllib.request
import urllib.parse
import base64
import socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import nav

REQUIRED_SECONDS = 60.0

lock = threading.Lock()
scanner_target = {
    "name": "Searching for G-Station 3-4...",
    "x": None,
    "y": None,
    "vx": 0.0,
    "vy": 0.0,
    "last_updated": 0,
    "total_msgs": 0
}

def start_port_2014_bridge():
    """Background TCP forwarder: 0.0.0.0:2014 -> 127.0.0.1:5672."""
    def forward(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data: break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            src.close()
            dst.close()

    def handle(client):
        try:
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.connect(('127.0.0.1', 5672))
            threading.Thread(target=forward, args=(client, target), daemon=True).start()
            threading.Thread(target=forward, args=(target, client), daemon=True).start()
        except Exception:
            client.close()

    def server_loop():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(('0.0.0.0', 2014))
            srv.listen(128)
            while True:
                c, _ = srv.accept()
                threading.Thread(target=handle, args=(c,), daemon=True).start()
        except Exception:
            pass

    threading.Thread(target=server_loop, daemon=True).start()

def rabbitmq_listener():
    """Consumes live detected objects from RabbitMQ scanner/detected_objects."""
    global scanner_target
    auth = base64.b64encode(b'guest:guest').decode()
    headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}

    def api(ep, method='GET', data=None):
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:15672/api/{ep}",
                data=json.dumps(data).encode() if data else None,
                headers=headers,
                method=method
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                b = r.read().decode()
                return json.loads(b) if b else {}
        except Exception:
            return None

    vhost = urllib.parse.quote('/', safe='')
    qname = f"chase_scanner_{int(time.time())}"
    enc_q = urllib.parse.quote(qname, safe='')
    exchange = urllib.parse.quote('scanner/detected_objects', safe='')

    api(f"exchanges/{vhost}/{exchange}", "PUT", {"type": "fanout", "durable": False, "auto_delete": False})
    api(f"queues/{vhost}/{enc_q}", "PUT", {"auto_delete": True, "durable": False})
    api(f"bindings/{vhost}/e/{exchange}/q/{enc_q}", "POST", {"routing_key": ""})

    last_x, last_y, last_t = None, None, None

    while True:
        try:
            msgs = api(f"queues/{vhost}/{enc_q}/get", "POST", {
                "count": 10,
                "ackmode": "ack_requeue_false",
                "encoding": "auto",
                "truncate": 50000
            })
            if isinstance(msgs, list) and msgs:
                for m in msgs:
                    raw = m.get('payload', '')
                    payload = json.loads(raw) if isinstance(raw, str) else raw
                    items = payload if isinstance(payload, list) else [payload]
                    for obj in items:
                        name = obj.get('name') or obj.get('station') or ''
                        # Match G-Station 3-4
                        if 'g-station' in name.lower() or '3-4' in name or 'station-g' in name.lower():
                            pos = obj.get('pos', {})
                            if 'x' in pos and 'y' in pos:
                                now = time.time()
                                px, py = float(pos['x']), float(pos['y'])
                                vx, vy = 0.0, 0.0
                                if last_x is not None and last_t and (now - last_t) > 0.01:
                                    dt = now - last_t
                                    vx = (px - last_x) / dt
                                    vy = (py - last_y) / dt
                                last_x, last_y, last_t = px, py, now

                                with lock:
                                    scanner_target["name"] = name
                                    scanner_target["x"] = px
                                    scanner_target["y"] = py
                                    scanner_target["vx"] = vx
                                    scanner_target["vy"] = vy
                                    scanner_target["last_updated"] = now
                                    scanner_target["total_msgs"] += 1
        except Exception:
            pass
        time.sleep(0.05)

def main():
    print("=" * 72)
    print("     🛰️  THE SHIP — DIRECT RABBITMQ AUTOPILOT PURSUIT (60s)")
    print("=" * 72)
    print("Scanner Feed : RabbitMQ 'scanner/detected_objects' (fanout)")
    print("Target Object: G-Station 3-4")
    print(f"Target Goal  : Maintain continuous proximity (< 25 units) for {REQUIRED_SECONDS:.0f}s")
    print("-" * 72)

    # Start bridge and telemetry worker
    start_port_2014_bridge()
    threading.Thread(target=rabbitmq_listener, daemon=True).start()
    print("🐰 RabbitMQ telemetry subscriber active. Standing by for coordinates...")

    # Wait for first telemetry lock
    while True:
        with lock:
            if scanner_target["x"] is not None:
                break
        time.sleep(0.2)

    print(f"🎯 INITIAL LOCK: {scanner_target['name']} at ({scanner_target['x']:.1f}, {scanner_target['y']:.1f})")
    print("🚀 Engaging Autopilot pursuit...\n")

    streak = 0.0
    last_in_reach = None
    last_nav_update = 0

    try:
        while streak < REQUIRED_SECONDS:
            now = time.time()
            reach = nav._http_get(2011, "stations_in_reach")
            pos_data = nav._http_get(2011, "pos")

            p = pos_data.get("pos", {}) if isinstance(pos_data, dict) else {}
            v = pos_data.get("velocity", {}) if isinstance(pos_data, dict) else {}
            sx, sy = p.get("x", 0.0), p.get("y", 0.0)
            svx, svy = v.get("x", 0.0), v.get("y", 0.0)
            cur_speed = math.hypot(svx, svy)

            # Check if station is in docking range (< 25 units)
            in_range = False
            detected_name = None
            if isinstance(reach, dict) and reach.get("kind") == "success":
                st_dict = reach.get("stations", {})
                for s in st_dict:
                    if "g-station" in s.lower() or "3-4" in s or "station-g" in s.lower():
                        in_range = True
                        detected_name = s
                        break

            # Read live target from RabbitMQ
            with lock:
                tx = scanner_target["x"]
                ty = scanner_target["y"]
                tvx = scanner_target["vx"]
                tvy = scanner_target["vy"]
                t_age = now - scanner_target["last_updated"] if scanner_target["last_updated"] else 999
                total_msgs = scanner_target["total_msgs"]

            # Calculate distance to station
            dist_to_station = math.hypot(tx - sx, ty - sy) if (tx is not None) else 999.0

            # Autopilot lead projection: predict 1.0s ahead along velocity vector
            if tx is not None and ty is not None and t_age < 3.0:
                lead_x = tx + tvx * 1.0
                lead_y = ty + tvy * 1.0
                if now - last_nav_update >= 0.25:
                    nav.set_target((lead_x, lead_y))
                    last_nav_update = now

            if in_range:
                streak += (now - last_in_reach) if last_in_reach else 0.1
                last_in_reach = now

                pct = min(100.0, streak / REQUIRED_SECONDS * 100)
                bar = "█" * int(streak / REQUIRED_SECONDS * 20)
                sys.stdout.write(
                    f"\r🟢 PURSUIT LOCKED | [{bar:<20}] {streak:.1f}/{REQUIRED_SECONDS:.0f}s ({pct:.0f}%) | "
                    f"Dist: {dist_to_station:4.1f} | Ship Spd: {cur_speed:4.1f} | Target: ({tx:.0f}, {ty:.0f})   "
                )
            else:
                if streak > 0:
                    print(f"\n🔴 Contact lost at {streak:.1f}s. Re-intercepting target...")
                    streak = 0.0
                last_in_reach = None

                sys.stdout.write(
                    f"\r⚡ INTERCEPTING... Dist: {dist_to_station:4.1f} | Ship Spd: {cur_speed:4.1f} | "
                    f"Target Pos: ({tx:.0f}, {ty:.0f}) [msgs: {total_msgs}]   "
                )

            sys.stdout.flush()
            time.sleep(0.05)

        print("\n" + "=" * 72)
        print(f"🎉 60-SECOND CONTINUOUS CONTACT ACHIEVED ({streak:.1f}s)! Mission complete!")
        print("=" * 72)
        nav.stop_ship()

    except KeyboardInterrupt:
        print("\n\n⏹️ Pursuit stopped by user.")
        nav.stop_ship()

if __name__ == "__main__":
    main()
