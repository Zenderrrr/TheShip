#!/usr/bin/env python3
import math
import time
import json
import urllib.request
import config

def _http(port, path, method="GET", data=None):
    url = f"http://{config.HOST}:{port}/{path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json"} if data else {},
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.loads(r.read().decode() or '{}')
    except Exception as e:
        return {"kind": "error", "message": str(e)}

_http_get = lambda port, path: _http(port, path, "GET")
_http_post = lambda port, path, data: _http(port, path, "POST", data)

def set_target(target):
    if isinstance(target, str):
        st = config.normalize_station(target)
        if st in config.STATIONS:
            tx, ty = config.STATIONS[st]
            return _http_post(2009, "set_target", {"target": {"x": tx, "y": ty}})
        return _http_post(2009, "set_target", {"target": st})
    elif isinstance(target, (tuple, list)):
        return _http_post(2009, "set_target", {"target": {"x": float(target[0]), "y": float(target[1])}})
    return _http_post(2009, "set_target", {"target": str(target)})

def stop_ship(): return _http_post(2009, "set_target", {"target": "stop"})
def idle_ship(): return _http_post(2009, "set_target", {"target": "idle"})

def fly_to(target):
    name = config.normalize_station(target) if isinstance(target, str) else f"({target[0]:.1f}, {target[1]:.1f})"
    tx, ty = config.STATIONS.get(name, target if isinstance(target, tuple) else (0, 0))
    print(f"🚀 Flying to {name}...")
    set_target(target)
    try:
        while True:
            p = _http_get(2011, "pos").get("pos", {})
            d = math.hypot(tx - p.get("x", 0), ty - p.get("y", 0))
            reach = _http_get(2011, "stations_in_reach").get("stations", {})
            print(f"Pos: ({p.get('x',0):.1f}, {p.get('y',0):.1f}) | Dist: {d:.1f}      ", end="\r", flush=True)
            if (isinstance(target, str) and name in reach) or d <= 25:
                print(f"\n✅ Arrived at {name}!")
                stop_ship()
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n⏹️ Stopped.")
        stop_ship()