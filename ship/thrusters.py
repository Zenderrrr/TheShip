#!/usr/bin/env python3
import json
import config

# set power on a specific thruster (1-5)
def set_thruster(thruster_id, percent):
    port = config.THRUSTER_PORTS.get(int(thruster_id))
    if not port:
        return {"error": f"Invalid thruster ID {thruster_id}"}
    payload = json.dumps({"thrust_percent": int(percent)})
    # send thruster command
    return config.curl(f'-XPUT http://{config.HOST}:{port}/thruster -H "Content-Type: application/json" -d \'{payload}\'')

# set power on all thrusters
def set_all(percent):
    results = {}
    for tid in config.THRUSTER_PORTS:
        results[tid] = set_thruster(tid, percent)
    return results

if __name__ == "__main__":
    import sys
    pct = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print(set_all(pct))
