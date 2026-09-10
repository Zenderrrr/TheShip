import sys
import config
import nav

def set_thruster(thruster_id, percent):
    """Sets an individual thruster (1-5) to a thrust percentage (0-100)."""
    port = config.THRUSTERS.get(int(thruster_id))
    if not port:
        return {"error": f"Invalid thruster {thruster_id}"}
    return nav._http(port, "thruster", "PUT", {"thrust_percent": int(percent)})

def set_all(percent):
    """Sets all 5 thrusters to the given percentage."""
    return {tid: set_thruster(tid, percent) for tid in config.THRUSTERS}

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print(set_thruster(sys.argv[1], sys.argv[2]))
    elif len(sys.argv) > 1:
        print(set_all(sys.argv[1]))
