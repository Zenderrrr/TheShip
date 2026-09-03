#!/usr/bin/env python3
import nav

def get_telemetry(): return nav._http_get(2011, "pos")
def get_cargo(): return nav._http_get(2012, "hold")
def get_stations_in_reach(): return nav._http_get(2011, "stations_in_reach")

def print_status():
    t = get_telemetry()
    c = get_cargo()
    s = get_stations_in_reach()

    print("=" * 50)
    print("           THE SHIP — STATUS OVERVIEW")
    print("=" * 50)
    p = t.get("pos", {})
    v = t.get("velocity", {})
    print(f"📍 Pos : ({p.get('x', 0):.1f}, {p.get('y', 0):.1f}) | Angle: {p.get('angle', 0):.1f}°")
    print(f"💨 Vel : ({v.get('x', 0):.1f}, {v.get('y', 0):.1f})")

    hold = c.get("hold", {})
    res = [f"{k}:{v}" for k, v in hold.get("resources", {}).items() if v > 0]
    print(f"📦 Hold: {', '.join(res) if res else '(Empty)'} | Credits: {hold.get('credits', 0)}¢")

    reach = s.get("stations", {})
    print(f"🪐 Near: {', '.join(reach.keys()) if reach else 'None in range'}")
    print("=" * 50)

if __name__ == "__main__":
    print_status()
