#!/usr/bin/env python3
"""
================================================================================
          THE SHIP — STATION ATTACH & DOCK LOCK (TETHER CONTROLLER)
================================================================================
Attaches your spacecraft to any nearby station (static or moving).
- Continuously matches velocity and position to keep the ship inside the docking
  envelope (< 25 units) so moving stations cannot fly away.
- Provides real-time trade (buy/sell) and cargo management while locked on.
"""

import sys
import time
import math
import json
import threading
import termios
import tty
import select
import urllib.request
import urllib.error
import config
import nav
import status
import trade

class StationAttacher:
    def __init__(self, station_name=None):
        self.station_name = config.normalize_station(station_name) if station_name else None
        self.running = False
        self.locked = False
        self.lock = threading.Lock()
        
        # Telemetry & Station tracking
        self.ship_pos = (0.0, 0.0)
        self.ship_vel = (0.0, 0.0)
        self.ship_angle = 0.0
        self.station_pos = None
        self.station_vel = (0.0, 0.0)
        self.last_in_reach_time = 0
        self.market_data = {}
        self.status_msg = "Searching for nearby station..."

    def fetch_data(self):
        """Fetch current ship position and stations in reach."""
        # Telemetry
        try:
            pos_data = config.curl(f"http://{config.HOST}:2011/pos")
            if isinstance(pos_data, dict) and pos_data.get("kind") == "success":
                p = pos_data.get("pos", {})
                v = pos_data.get("velocity", {})
                self.ship_pos = (p.get("x", 0.0), p.get("y", 0.0))
                self.ship_angle = p.get("angle", 0.0)
                self.ship_vel = (v.get("x", 0.0), v.get("y", 0.0))
        except Exception:
            pass

        # Stations in reach
        try:
            reach = config.curl(f"http://{config.HOST}:2011/stations_in_reach")
            if isinstance(reach, dict) and reach.get("kind") == "success":
                st_dict = reach.get("stations", {})
                return st_dict
        except Exception:
            pass
        return {}

    def tether_worker(self):
        """Background thread keeping the ship tethered to the moving station."""
        last_check_pos = None
        last_check_time = time.time()

        while self.running:
            st_dict = self.fetch_data()
            now = time.time()
            dt = max(0.05, now - last_check_time)
            last_check_time = now

            # If no station selected yet, select first station in reach
            if not self.station_name and st_dict:
                self.station_name = list(st_dict.keys())[0]

            in_reach = (self.station_name in st_dict) if self.station_name else False

            with self.lock:
                if in_reach:
                    self.locked = True
                    self.last_in_reach_time = now
                    self.market_data = st_dict.get(self.station_name, {}).get("resources", {})
                    self.status_msg = "🟢 LOCKED & TETHERED"
                    
                    # Update station position estimate from current ship pos
                    if last_check_pos:
                        dx = self.ship_pos[0] - last_check_pos[0]
                        dy = self.ship_pos[1] - last_check_pos[1]
                        # Estimate station speed
                        self.station_vel = (dx / dt, dy / dt)
                    last_check_pos = self.ship_pos
                    self.station_pos = self.ship_pos
                else:
                    # Not in reach right now
                    if now - self.last_in_reach_time < 3.0:
                        self.locked = True
                        self.status_msg = "🟡 RE-ACQUIRING POSITION..."
                        # Station is drifting away! Nudge autopilot in direction of station
                        if self.station_pos:
                            target_x = self.station_pos[0] + self.station_vel[0] * 1.5
                            target_y = self.station_pos[1] + self.station_vel[1] * 1.5
                            nav.set_target((target_x, target_y))
                    else:
                        self.locked = False
                        self.status_msg = "🔴 OUT OF REACH"

            time.sleep(0.2)

    def draw_hud(self):
        """Draw interactive tether HUD."""
        sx, sy = self.ship_pos
        vx, vy = self.ship_vel
        speed = math.hypot(vx, vy)

        sys.stdout.write("\033[H\033[J")
        sys.stdout.write("=" * 68 + "\n")
        sys.stdout.write("       🧲 THE SHIP — STATION TETHER & DOCK LOCK\n")
        sys.stdout.write("=" * 68 + "\n")
        sys.stdout.write(f"  TARGET STATION : {self.station_name or 'Auto-Detecting...'}\n")
        sys.stdout.write(f"  LOCK STATUS    : {self.status_msg}\n")
        sys.stdout.write(f"  SHIP POSITION  : ({sx:.1f}, {sy:.1f}) | Speed: {speed:.1f} | Angle: {self.ship_angle:.1f}°\n")
        sys.stdout.write("-" * 68 + "\n")
        
        sys.stdout.write("  🪐 LIVE MARKET AT STATION:\n")
        if self.market_data:
            for r_name, p in self.market_data.items():
                sys.stdout.write(f"    • {r_name:<10}: Buy Price = {p.get('buy_price', 0):>4}¢ | Sell Price = {p.get('sell_price', 0):>4}¢\n")
        else:
            sys.stdout.write("    (No market data available yet — waiting for docking sync)\n")

        sys.stdout.write("-" * 68 + "\n")
        sys.stdout.write("  ACTIONS:\n")
        sys.stdout.write("    [B] Buy Resource       [S] Sell Resource\n")
        sys.stdout.write("    [C] Check Cargo Hold   [U] / [ESC] Un-attach & Return\n")
        sys.stdout.write("=" * 68 + "\n")
        sys.stdout.flush()

    def run(self):
        """Run interactive tether control console."""
        print(f"\nScanning for stations within docking reach (< 25 units)...")
        st_dict = self.fetch_data()
        
        if not self.station_name:
            if st_dict:
                self.station_name = list(st_dict.keys())[0]
                print(f"Detected nearby station: {self.station_name}!")
            else:
                print("No station currently in reach.")
                print("Available known stations to approach:")
                st_keys = list(config.STATIONS.keys())
                for idx, name in enumerate(st_keys, 1):
                    print(f"  [{idx}] {name} {config.STATIONS[name]}")
                print("  [0] Cancel")
                try:
                    c = input("\nSelect station to fly to and attach (0-{}): ".format(len(st_keys))).strip()
                    if c.isdigit() and 1 <= int(c) <= len(st_keys):
                        self.station_name = st_keys[int(c) - 1]
                        print(f"Approaching {self.station_name}...")
                        nav.fly_to(self.station_name)
                    else:
                        print("Attachment cancelled.")
                        return
                except (KeyboardInterrupt, EOFError):
                    return

        print(f"Engaging tether lock with {self.station_name}...")
        self.running = True

        t_tether = threading.Thread(target=self.tether_worker, daemon=True)
        t_tether.start()

        if not sys.stdin.isatty():
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            return

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            last_draw = 0

            while self.running:
                now = time.time()
                if now - last_draw >= 0.25:
                    self.draw_hud()
                    last_draw = now

                rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                if rlist:
                    ch = sys.stdin.read(1)
                    if ch in ('\x03', '\x04', 'u', 'U', 'q', 'Q', 'x', 'X', '\x1b'):
                        break

                    # Buy command
                    elif ch in ('b', 'B'):
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        print("\n--- BUY RESOURCES ---")
                        r_name = input("Resource name (e.g. IRON, GOLD): ").strip().upper() or "IRON"
                        amt_str = input("Amount to buy (default 5): ").strip() or "5"
                        amt = int("".join(c for c in amt_str if c.isdigit()) or 5)
                        res = trade.buy(self.station_name, r_name, amt)
                        print("Result:", res)
                        input("Press Enter to continue...")
                        tty.setcbreak(sys.stdin.fileno())

                    # Sell command
                    elif ch in ('s', 'S'):
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        print("\n--- SELL RESOURCES ---")
                        r_name = input("Resource name (e.g. IRON, GOLD): ").strip().upper() or "IRON"
                        amt_str = input("Amount to sell (default 5): ").strip() or "5"
                        amt = int("".join(c for c in amt_str if c.isdigit()) or 5)
                        res = trade.sell(self.station_name, r_name, amt)
                        print("Result:", res)
                        input("Press Enter to continue...")
                        tty.setcbreak(sys.stdin.fileno())

                    # Cargo check
                    elif ch in ('c', 'C'):
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        print()
                        status.print_status()
                        input("Press Enter to continue...")
                        tty.setcbreak(sys.stdin.fileno())

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            nav.stop_ship()
            sys.stdout.write(f"\n\nUn-attached from {self.station_name or 'station'}. Ship stopped.\n")
            sys.stdout.flush()

def attach_to_station(station_name=None):
    attacher = StationAttacher(station_name)
    attacher.run()

if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else None
    attach_to_station(st)
