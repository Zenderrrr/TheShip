#!/usr/bin/env python3
"""
================================================================================
     THE SHIP — CONTINUOUS RABBITMQ ESCORT & AUTOPILOT TRACKER (INFINITE)
================================================================================
Continuously tracks and escorts 'G-Station 3-4' indefinitely using live RabbitMQ
telemetry and adaptive autopilot lookahead navigation.
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

TARGET_NAME = "G-Station 3-4"

lock = threading.Lock()
scanner_target = {
    "name": TARGET_NAME,
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
    """Strictly consumes only 'G-Station 3-4' from RabbitMQ scanner/detected_objects."""
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
    smooth_vx, smooth_vy = 0.0, 0.0

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
                        name = str(obj.get('name') or obj.get('station') or '').strip()
                        
                        if "3-4" in name or name.lower() == "g-station 3-4":
                            pos = obj.get('pos', {})
                            if isinstance(pos, dict) and 'x' in pos and 'y' in pos:
                                now = time.time()
                                px, py = float(pos['x']), float(pos['y'])
                                
                                if last_x is not None and last_t:
                                    dt = now - last_t
                                    if dt > 0.01:
                                        dist_jump = math.hypot(px - last_x, py - last_y)
                                        if dist_jump < 300.0:
                                            raw_vx = (px - last_x) / dt
                                            raw_vy = (py - last_y) / dt
                                            smooth_vx = 0.6 * raw_vx + 0.4 * smooth_vx
                                            smooth_vy = 0.6 * raw_vy + 0.4 * smooth_vy
                                
                                last_x, last_y, last_t = px, py, now

                                with lock:
                                    scanner_target["name"] = name
                                    scanner_target["x"] = px
                                    scanner_target["y"] = py
                                    scanner_target["vx"] = smooth_vx
                                    scanner_target["vy"] = smooth_vy
                                    scanner_target["last_updated"] = now
                                    scanner_target["total_msgs"] += 1
        except Exception:
            pass
        time.sleep(0.04)

def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def main():
    print("=" * 72)
    print("     🛰️  THE SHIP — CONTINUOUS 'G-STATION 3-4' ESCORT CONTROLLER")
    print("=" * 72)
    print(f"Target Object : '{TARGET_NAME}' (Strict Single-Target Filter)")
    print("Mode          : Continuous Infinite Escort (Ctrl+C to stop)")
    print("-" * 72)

    start_port_2014_bridge()
    threading.Thread(target=rabbitmq_listener, daemon=True).start()
    print(f"🐰 Listening on RabbitMQ. Waiting for lock on '{TARGET_NAME}'...")

    while True:
        with lock:
            if scanner_target["x"] is not None:
                break
        time.sleep(0.1)

    print(f"🎯 LOCKED ONTO {scanner_target['name']} at ({scanner_target['x']:.1f}, {scanner_target['y']:.1f})")
    print("🚀 Autopilot continuous escort active...\n")

    start_time = time.time()
    total_locked_time = 0.0
    current_streak = 0.0
    best_streak = 0.0
    last_in_reach = None
    last_nav_update = 0

    try:
        while True:
            now = time.time()
            reach = nav._http_get(2011, "stations_in_reach")
            pos_data = nav._http_get(2011, "pos")

            p = pos_data.get("pos", {}) if isinstance(pos_data, dict) else {}
            v = pos_data.get("velocity", {}) if isinstance(pos_data, dict) else {}
            sx, sy = p.get("x", 0.0), p.get("y", 0.0)
            svx, svy = v.get("x", 0.0), v.get("y", 0.0)
            cur_speed = math.hypot(svx, svy)

            # Check if G-Station 3-4 is within docking reach (< 25 units)
            in_range = False
            if isinstance(reach, dict) and reach.get("kind") == "success":
                st_dict = reach.get("stations", {})
                for s in st_dict:
                    if "3-4" in s or "g-station 3-4" in s.lower():
                        in_range = True
                        break

            # Read live target coordinates
            with lock:
                tx = scanner_target["x"]
                ty = scanner_target["y"]
                tvx = scanner_target["vx"]
                tvy = scanner_target["vy"]
                t_age = now - scanner_target["last_updated"] if scanner_target["last_updated"] else 999
                total_msgs = scanner_target["total_msgs"]

            dist_to_target = math.hypot(tx - sx, ty - sy) if (tx is not None) else 999.0

            # Adaptive lead lookahead
            if dist_to_target < 12.0:
                lead_t = 0.4
            elif dist_to_target < 20.0:
                lead_t = 0.75
            else:
                lead_t = 1.2

            if tx is not None and ty is not None and t_age < 3.0:
                lead_x = tx + tvx * lead_t
                lead_y = ty + tvy * lead_t
                if now - last_nav_update >= 0.15:
                    nav.set_target((lead_x, lead_y))
                    last_nav_update = now

            if in_range:
                dt = (now - last_in_reach) if last_in_reach else 0.1
                current_streak += dt
                total_locked_time += dt
                best_streak = max(best_streak, current_streak)
                last_in_reach = now

                sys.stdout.write(
                    f"\r🟢 ESCORT LOCKED | Streak: {format_time(current_streak)} (Best: {format_time(best_streak)}) | "
                    f"Dist: {dist_to_target:4.1f} | Ship Spd: {cur_speed:4.1f} | Lead: {lead_t:.2f}s   "
                )
            else:
                if current_streak > 0:
                    print(f"\n🔴 Contact dropped (Streak: {format_time(current_streak)}). Re-intercepting '{TARGET_NAME}'...")
                    current_streak = 0.0
                last_in_reach = None

                sys.stdout.write(
                    f"\r⚡ INTERCEPTING... Dist: {dist_to_target:4.1f} | Ship Spd: {cur_speed:4.1f} | "
                    f"Target Pos: ({tx:.0f}, {ty:.0f}) [msgs: {total_msgs}]   "
                )

            sys.stdout.flush()
            time.sleep(0.04)

    except KeyboardInterrupt:
        total_runtime = time.time() - start_time
        print("\n\n" + "=" * 72)
        print("🛑 ESCORT COMPLETED")
        print(f"Total Runtime     : {format_time(total_runtime)}")
        print(f"Total Locked Time : {format_time(total_locked_time)}")
        print(f"Longest Streak    : {format_time(best_streak)}")
        print("=" * 72)
        nav.stop_ship()

if __name__ == "__main__":
    main()
