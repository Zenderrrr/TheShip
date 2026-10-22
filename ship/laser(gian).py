#!/usr/bin/env python3
"""
================================================================================
   LASER CONTROLLER CLI (Client Execution Script)
================================================================================

WIE DIESES SKRIPT FUNKTIONIERT:
  - Dieses Skript sendet direkte HTTP-Befehle an das Laser-Subsystem auf Port 2018.
  - WARUM KEIN TOKEN IM HEADER STEHT:
    In diesem Lab hat sich das Laser-Subsystem zuvor ueber den OAuth-Server
    (Port 2015) authentifiziert und haelt das Token fuer 1h im eigenen Speicher (RAM).
    Das Subsystem befindet sich daher in einem "entsperrten / ARMED" Zustand.
  - Wenn die 1 Stunde ablaeuft (oder niemand sich eingeloggt hat), geben diese
    Aufrufe einen 401 / Authorization-Fehler zurueck!
================================================================================
"""

import sys
import config
import nav

# Port 2018 = Die Laser-Hardware-API auf dem Schiff (Resource Server)
LASER_PORT = 2018

def state():
    """Gibt den aktuellen Status des Lasers zurueck (z.B. aktiv, Winkel, Temperatur)."""
    return nav._http_get(LASER_PORT, "state")

def activate():
    """
    Aktiviert/feuert den Laser.
    Akzeptiert nur, wenn das Laser-Subsystem zuvor per OAuth autorisiert wurde!
    """
    return nav._http_post(LASER_PORT, "activate", {})

def deactivate():
    """Deaktiviert / schaltet den Laser aus."""
    return nav._http_post(LASER_PORT, "deactivate", {})

def set_angle(angle):
    """Setzt den Zielwinkel des Lasers (PUT /angle)."""
    return nav._http(LASER_PORT, "angle", "PUT", {"angle": float(angle)})

# Direkte CLI-Ausfuehrung (z.B. python3 laser(gian).py on  oder  python3 laser(gian).py angle 45)
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ("on", "activate"):
            print(activate())
        elif cmd in ("off", "deactivate"):
            print(deactivate())
        elif cmd == "angle" and len(sys.argv) > 2:
            print(set_angle(sys.argv[2]))
        else:
            print(state())
    else:
        print(state())

