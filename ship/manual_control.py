#!/usr/bin/env python3
"""
================================================================================
          THE SHIP — MANUAL WASD FLIGHT CONTROL
================================================================================
Interactive real-time WASD keyboard controller for ship thrusters.
- Continuous thrust stream: while holding a key, thrusters fire continuously at 100%.
- 0% power on release: when key is released, thrusters immediately set to 0%.
- Calibrated Thruster Mapping based on ship physics:
    • [W] / [↑] : Thruster 1 (Port 2003) -> Main Forward Propulsion
    • [S] / [↓] : Thruster 2 (Port 2004) -> Retro / Reverse / Braking Engine
    • [A] / [←] : Thruster 5 (Port 2008) -> Turn Left (Counter-Clockwise Yaw)
    • [D] / [→] : Thruster 4 (Port 2007) -> Turn Right (Clockwise Yaw)
    • [Q]       : Thruster 5 (Port 2008) -> Turn Left
    • [E]       : Thruster 4 (Port 2007) -> Turn Right
    • [SPACE]   : Set all thrusters to 0%
"""

import sys
import time
import termios
import tty
import select
import threading
import json
import urllib.request
import urllib.error
import config
import nav

# Calibrated Thruster Mapping:
# 1: Forward Propulsion (W)
# 2: Turn Right / Starboard Yaw (D)
# 3: Starboard Maneuvering
# 4: Turn Left / Port Yaw (A)
# 5: Backwards / Reverse Engine (S)

KEY_MAP = {
    'w': 1,      # Forward
    'W': 1,
    's': 5,      # Backwards / Reverse / Brake
    'S': 5,
    'a': 4,      # Turn Left
    'A': 4,
    'd': 2,      # Turn Right
    'D': 2,
    'q': 4,      # Turn Left
    'Q': 4,
    'e': 2,      # Turn Right
    'E': 2,
}

# Timeout to bridge OS keyboard repeat delay (~300-450ms)
KEY_TIMEOUT = 0.45

class ManualFlightController:
    def __init__(self):
        self.running = False
        self.active_keys = {}  # thruster_id -> last_pressed_time
        self.active_status = {tid: False for tid in config.THRUSTER_PORTS}
        self.lock = threading.Lock()
        self.telemetry = {
            "pos": {"x": 0.0, "y": 0.0, "angle": 0.0},
            "velocity": {"x": 0.0, "y": 0.0, "angle": 0.0}
        }

    def send_thrust(self, thruster_id, percent):
        """Send HTTP PUT request to set thruster percentage."""
        port = config.THRUSTER_PORTS.get(thruster_id)
        if not port:
            return
        url = f"http://{config.HOST}:{port}/thruster"
        payload = json.dumps({"thrust_percent": int(percent)}).encode("utf-8")
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=0.4) as resp:
                pass
        except Exception:
            pass

    def stop_all_thrusters(self):
        """Immediately reset all thrusters to 0%."""
        with self.lock:
            self.active_keys.clear()
            for tid in config.THRUSTER_PORTS:
                self.active_status[tid] = False
        for tid in config.THRUSTER_PORTS:
            self.send_thrust(tid, 0)

    def continuous_thruster_worker(self):
        """
        Continuously stream 100% thrust to active thrusters while held down,
        and send 0% immediately when key release is detected.
        """
        while self.running:
            now = time.time()
            to_fire = []
            to_stop = []

            with self.lock:
                for tid in config.THRUSTER_PORTS:
                    last_time = self.active_keys.get(tid, 0)
                    is_active = (now - last_time < KEY_TIMEOUT)

                    if is_active:
                        self.active_status[tid] = True
                        to_fire.append(tid)
                    else:
                        if self.active_status[tid]:
                            self.active_status[tid] = False
                            to_stop.append(tid)

            # Fire active thrusters at 100%
            for tid in to_fire:
                threading.Thread(target=self.send_thrust, args=(tid, 100), daemon=True).start()

            # Set released thrusters to 0%
            for tid in to_stop:
                threading.Thread(target=self.send_thrust, args=(tid, 0), daemon=True).start()

            time.sleep(0.08)

    def telemetry_worker(self):
        """Poll telemetry data periodically in background."""
        while self.running:
            try:
                url = f"http://{config.HOST}:2011/pos"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=0.8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, dict) and data.get("kind") == "success":
                        self.telemetry = data
            except Exception:
                pass
            time.sleep(0.25)

    def draw_hud(self):
        """Render live cockpit HUD."""
        pos = self.telemetry.get("pos", {})
        vel = self.telemetry.get("velocity", {})
        px, py, angle = pos.get("x", 0.0), pos.get("y", 0.0), pos.get("angle", 0.0)
        vx, vy = vel.get("x", 0.0), vel.get("y", 0.0)
        speed = (vx**2 + vy**2) ** 0.5

        def t_str(tid):
            active = self.active_status.get(tid, False)
            return "🔥 [100%]" if active else "   [  0%]"

        sys.stdout.write("\033[H\033[J")
        sys.stdout.write("=" * 68 + "\n")
        sys.stdout.write("       🚀 THE SHIP — MANUAL WASD FLIGHT CONTROLLER\n")
        sys.stdout.write("=" * 68 + "\n")
        sys.stdout.write("  [W] Forward (T1)       [A] Turn Left (T4)     [D] Turn Right (T2)\n")
        sys.stdout.write("  [S] Reverse/Brake (T5) [Q/E] Yaw Left/Right   [SPACE] Set All 0%\n")
        sys.stdout.write("  [X] / [ESC] / [Ctrl+C] Exit to Console\n")
        sys.stdout.write("-" * 68 + "\n")
        sys.stdout.write("  THRUSTER STATUS:\n")
        sys.stdout.write(f"    • T1 (Main Fwd)  : {t_str(1):<12} • T2 (Yaw Right) : {t_str(2):<12}\n")
        sys.stdout.write(f"    • T3 (Maneuver)  : {t_str(3):<12} • T4 (Yaw Left)  : {t_str(4):<12}\n")
        sys.stdout.write(f"    • T5 (Retro/Brk) : {t_str(5):<12}\n")
        sys.stdout.write("-" * 68 + "\n")
        sys.stdout.write(f"  📍 POSITION : X: {px:10.1f} | Y: {py:10.1f} | Heading: {angle:5.1f}°\n")
        sys.stdout.write(f"  💨 VELOCITY : X: {vx:10.1f} | Y: {vy:10.1f} | Speed:   {speed:5.1f}\n")
        sys.stdout.write("=" * 68 + "\n")
        sys.stdout.write("  Hold key to fire thruster at 100%. Release to set 0%.\n")
        sys.stdout.flush()

    def run(self):
        """Main manual flight loop with raw keyboard listener."""
        if not sys.stdin.isatty():
            print("Error: Manual WASD flight control requires an interactive terminal (TTY).")
            return

        # Ensure autopilot target is stopped and all thrusters start at 0%
        nav.stop_ship()
        self.stop_all_thrusters()

        old_settings = termios.tcgetattr(sys.stdin)
        self.running = True

        # Start continuous thruster stream and telemetry workers
        t_thrust = threading.Thread(target=self.continuous_thruster_worker, daemon=True)
        t_telemetry = threading.Thread(target=self.telemetry_worker, daemon=True)
        t_thrust.start()
        t_telemetry.start()

        try:
            tty.setcbreak(sys.stdin.fileno())
            last_hud_draw = 0

            while self.running:
                now = time.time()
                if now - last_hud_draw >= 0.1:
                    self.draw_hud()
                    last_hud_draw = now

                rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                if rlist:
                    ch = sys.stdin.read(1)

                    # Exit conditions
                    if ch in ('\x03', '\x04', 'x', 'X', '\x1b'):
                        if ch == '\x1b':
                            r2, _, _ = select.select([sys.stdin], [], [], 0.02)
                            if r2:
                                ch2 = sys.stdin.read(1)
                                if ch2 == '[':
                                    ch3 = sys.stdin.read(1)
                                    if ch3 == 'A': ch = 'w'  # Up -> Forward (T1)
                                    elif ch3 == 'B': ch = 's'  # Down -> Reverse (T2)
                                    elif ch3 == 'C': ch = 'd'  # Right -> Yaw Right (T4)
                                    elif ch3 == 'D': ch = 'a'  # Left -> Yaw Left (T5)
                            else:
                                break
                        else:
                            break

                    if ch == ' ':
                        self.stop_all_thrusters()
                    elif ch in KEY_MAP:
                        tid = KEY_MAP[ch]
                        with self.lock:
                            self.active_keys[tid] = time.time()

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.stop_all_thrusters()
            sys.stdout.write("\n\nManual control ended. All thrusters set to 0%.\n")
            sys.stdout.flush()

def start_manual_control():
    controller = ManualFlightController()
    controller.run()

if __name__ == "__main__":
    start_manual_control()
