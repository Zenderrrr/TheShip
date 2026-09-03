#!/usr/bin/env python3
import config
import nav

def set_thruster(thruster_id, percent):
    port = config.THRUSTERS.get(int(thruster_id))
    if not port: return {"error": f"Invalid thruster {thruster_id}"}
    return nav._http(port, "thruster", "PUT", {"thrust_percent": int(percent)})

def set_all(percent):
    return {tid: set_thruster(tid, percent) for tid in config.THRUSTERS}

if __name__ == "__main__":
    import sys
    pct = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print(set_all(pct))
