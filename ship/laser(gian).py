import sys
import config
import nav

def state():
    """Returns current status of the laser."""
    return nav._http_get(2018, "state")

def activate():
    """Activates the laser."""
    return nav._http_post(2018, "activate", {})

def deactivate():
    """Deactivates the laser."""
    return nav._http_post(2018, "deactivate", {})

def set_angle(angle):
    """Sets the aim angle."""
    return nav._http(2018, "angle", "PUT", {"angle": float(angle)})

# Direct CLI execution (e.g. python laser.py activate  or  python laser.py angle 42)
if len(sys.argv) > 1:
    cmd = sys.argv[1].lower()
    if cmd in ("on"):
        print(activate())
    elif cmd in ("off"):
        print(deactivate())
    elif cmd == "angle" and len(sys.argv) > 2:
        print(set_angle(sys.argv[2]))
    else:
        print(state())
else:
    print(state())
