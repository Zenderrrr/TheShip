import sys
import time
import math
import json
import urllib.request
import config

# Helper function to send HTTP requests to ship subsystem ports
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
            return json.loads(r.read().decode() or "{}")
    except Exception as e:
        return {"kind": "error", "message": str(e)}

_http_get = lambda port, path: _http(port, path, "GET")
_http_post = lambda port, path, data: _http(port, path, "POST", data)


def set_target(target):
    """Sets the autopilot navigation target (station name, coordinates, or stop/idle)."""
    if isinstance(target, (tuple, list)):
        return _http_post(2009, "set_target", {"target": {"x": float(target[0]), "y": float(target[1])}})
    st = config.normalize_station(str(target))
    if st in config.STATIONS:
        tx, ty = config.STATIONS[st]
        return _http_post(2009, "set_target", {"target": {"x": tx, "y": ty}})
    return _http_post(2009, "set_target", {"target": str(target)})


def stop_ship():
    """Commands the autopilot to perform an emergency stop."""
    return _http_post(2009, "set_target", {"target": "stop"})


def idle_ship():
    """Sets the autopilot into idle / drift mode."""
    return _http_post(2009, "set_target", {"target": "idle"})


def fly_to(target):
    """Flies to a station or (X, Y) coordinate and tracks progress until arrival."""
    name = config.normalize_station(target) if isinstance(target, str) else f"({target[0]:.0f}, {target[1]:.0f})"
    tx, ty = config.STATIONS.get(name, target if isinstance(target, (tuple, list)) else (0, 0))

    print(f"Flying to {name}...")
    set_target(target)

    try:
        while True:
            pos = _http_get(2011, "pos").get("pos", {})
            reach = _http_get(2011, "stations_in_reach").get("stations", {})
            dist = math.hypot(tx - pos.get("x", 0), ty - pos.get("y", 0))

            print(f"\rPos: ({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f}) | Dist: {dist:4.1f}", end="", flush=True)

            if (isinstance(target, str) and name in reach) or dist <= 25:
                print(f"\nArrived at {name}!")
                stop_ship()
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nStopped.")
        stop_ship()


# Direct CLI execution
if __name__ == "__main__" and len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg.lower() == "stop":
        print(stop_ship())
    elif arg.lower() == "idle":
        print(idle_ship())
    elif len(sys.argv) > 2:
        fly_to((float(sys.argv[1]), float(sys.argv[2])))
    else:
        fly_to(arg)