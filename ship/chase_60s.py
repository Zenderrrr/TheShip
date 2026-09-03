#!/usr/bin/env python3
"""
THE SHIP — CONTINUOUS RABBITMQ AUTOPILOT PURSUIT
Tracks and escorts G-Station 3-4 indefinitely via live RabbitMQ scanner feed.
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
target = {"x": None, "y": None, "vx": 0.0, "vy": 0.0, "ts": 0}

def start_port_2014_bridge():
    """Forward port 2014 to local RabbitMQ 5672."""
    def forward(s1, s2):
        try:
            while data := s1.recv(4096): s2.sendall(data)
        except Exception: pass
        finally: s1.close(); s2.close()

    def srv():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('0.0.0.0', 2014))
            s.listen(64)
            while True:
                c, _ = s.accept()
                r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                r.connect(('127.0.0.1', 5672))
                threading.Thread(target=forward, args=(c, r), daemon=True).start()
                threading.Thread(target=forward, args=(r, c), daemon=True).start()
        except Exception: pass

    threading.Thread(target=srv, daemon=True).start()

def rabbitmq_listener():
    """Consumes G-Station 3-4 coordinates from RabbitMQ exchange."""
    global target
    auth = base64.b64encode(b'guest:guest').decode()
    headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}

    def req(path, method='GET', data=None):
        try:
            r = urllib.request.Request(
                f"http://127.0.0.1:15672/api/{path}",
                data=json.dumps(data).encode() if data else None,
                headers=headers, method=method
            )
            with urllib.request.urlopen(r, timeout=2) as resp:
                return json.loads(resp.read().decode() or '{}')
        except Exception: return None

    vhost = urllib.parse.quote('/', safe='')
    qname = f"chase_{int(time.time())}"
    ex = urllib.parse.quote('scanner/detected_objects', safe='')

    req(f"exchanges/{vhost}/{ex}", "PUT", {"type": "fanout", "durable": False, "auto_delete": False})
    req(f"queues/{vhost}/{qname}", "PUT", {"auto_delete": True, "durable": False})
    req(f"bindings/{vhost}/e/{ex}/q/{qname}", "POST", {"routing_key": ""})

    last_x, last_y, last_t, vx, vy = None, None, None, 0.0, 0.0

    while True:
        try:
            msgs = req(f"queues/{vhost}/{qname}/get", "POST", {"count": 10, "ackmode": "ack_requeue_false", "encoding": "auto"})
            if isinstance(msgs, list):
                for m in msgs:
                    payload = json.loads(m.get('payload', '{}'))
                    items = payload if isinstance(payload, list) else [payload]
                    for obj in items:
                        name = str(obj.get('name') or obj.get('station') or '').strip()
                        if "3-4" in name or name.lower() == "g-station 3-4":
                            pos = obj.get('pos', {})
                            if 'x' in pos and 'y' in pos:
                                now = time.time()
                                px, py = float(pos['x']), float(pos['y'])
                                if last_x is not None and last_t and (now - last_t) > 0.01:
                                    dt = now - last_t
                                    if math.hypot(px - last_x, py - last_y) < 300.0:
                                        vx = 0.6 * ((px - last_x) / dt) + 0.4 * vx
                                        vy = 0.6 * ((py - last_y) / dt) + 0.4 * vy
                                last_x, last_y, last_t = px, py, now
                                with lock:
                                    target.update({"x": px, "y": py, "vx": vx, "vy": vy, "ts": now})
        except Exception: pass
        time.sleep(0.04)

def fmt_time(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def main():
    print(f"🛰️ THE SHIP — Tracking {TARGET_NAME} (Ctrl+C to stop)...")
    start_port_2014_bridge()
    threading.Thread(target=rabbitmq_listener, daemon=True).start()

    while True:
        with lock:
            if target["x"] is not None: break
        time.sleep(0.1)

    print(f"🎯 Locked onto {TARGET_NAME} at ({target['x']:.1f}, {target['y']:.1f}). Pursuit active.\n")

    streak, best_streak, last_contact, last_nav = 0.0, 0.0, None, 0

    try:
        while True:
            now = time.time()
            reach = nav._http_get(2011, "stations_in_reach")
            pos_data = nav._http_get(2011, "pos")

            p = pos_data.get("pos", {}) if isinstance(pos_data, dict) else {}
            v = pos_data.get("velocity", {}) if isinstance(pos_data, dict) else {}
            sx, sy = p.get("x", 0.0), p.get("y", 0.0)
            cur_spd = math.hypot(v.get("x", 0.0), v.get("y", 0.0))

            in_range = any("3-4" in s for s in reach.get("stations", {})) if (isinstance(reach, dict) and reach.get("kind") == "success") else False

            with lock:
                tx, ty, tvx, tvy, t_age = target["x"], target["y"], target["vx"], target["vy"], now - target["ts"]

            dist = math.hypot(tx - sx, ty - sy) if (tx is not None) else 999.0
            lead_t = 0.4 if dist < 12.0 else (0.75 if dist < 20.0 else 1.2)

            if tx is not None and ty is not None and t_age < 3.0:
                if now - last_nav >= 0.15:
                    nav.set_target((tx + tvx * lead_t, ty + tvy * lead_t))
                    last_nav = now

            if in_range:
                dt = (now - last_contact) if last_contact else 0.1
                streak += dt
                best_streak = max(best_streak, streak)
                last_contact = now
                sys.stdout.write(f"\r🟢 LOCKED | Streak: {fmt_time(streak)} (Best: {fmt_time(best_streak)}) | Dist: {dist:4.1f} | Speed: {cur_spd:4.1f}   ")
            else:
                if streak > 0:
                    print(f"\n🔴 Contact dropped (Streak: {fmt_time(streak)}). Re-intercepting...")
                    streak = 0.0
                last_contact = None
                sys.stdout.write(f"\r⚡ INTERCEPTING... Dist: {dist:4.1f} | Speed: {cur_spd:4.1f} | Target: ({tx:.0f}, {ty:.0f})   ")

            sys.stdout.flush()
            time.sleep(0.04)

    except KeyboardInterrupt:
        print(f"\n\n🛑 Stopped. Longest Streak: {fmt_time(best_streak)}")
        nav.stop_ship()

if __name__ == "__main__":
    main()
