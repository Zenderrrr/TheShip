import config
import nav
import status
import trade
import thrusters
import dock
import laser

def menu():
    while True:
        print("\n" + "=" * 40)
        print("         🚀 THE SHIP — CONSOLE")
        print("=" * 40)
        print("  [1] 📊 Status Overview")
        print("  [2] 🧭 Fly to Station")
        print("  [3] 📍 Fly to Coordinates (X, Y)")
        print("  [4] 🛑 Emergency Stop")
        print("  [5] 💨 Drift / Idle")
        print("  [6] 💰 Buy Resource")
        print("  [7] 🏷️  Sell Resource")
        print("  [8] 🔥 Set Thrusters")
        print("  [9] 🧲 Dock at Station")
        print("  [10] 🔴 Mining Laser Controls")
        print("  [0] ❌ Exit")
        print("=" * 40)

        try:
            choice = input("Select an option (0-10): ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice in ("0", "exit", "q"):
            break
        elif choice == "1":
            status.show()
        elif choice == "2":
            stations = list(config.STATIONS.keys())
            for i, name in enumerate(stations, 1):
                print(f"  [{i}] {name}")
            c = input(f"Select station (1-{len(stations)}): ").strip()
            if c.isdigit() and 1 <= int(c) <= len(stations):
                nav.fly_to(stations[int(c) - 1])
        elif choice == "3":
            try:
                x = float(input("X coordinate: "))
                y = float(input("Y coordinate: "))
                nav.fly_to((x, y))
            except ValueError:
                print("Invalid numbers entered.")
        elif choice == "4":
            print(nav.stop_ship())
        elif choice == "5":
            print(nav.idle_ship())
        elif choice == "6":
            st = input("Station (default: Azura Station): ") or "Azura Station"
            res = input("Resource (default: IRON): ") or "IRON"
            amt = int(input("Amount (default: 10): ") or 10)
            print(trade.buy(st, res, amt))
        elif choice == "7":
            st = input("Station (default: Core Station): ") or "Core Station"
            res = input("Resource (default: IRON): ") or "IRON"
            amt = int(input("Amount (default: 10): ") or 10)
            print(trade.sell(st, res, amt))
        elif choice == "8":
            tid = input("Thruster number (1-5 or 'all'): ")
            pct = int(input("Thrust percent (0-100): ") or 0)
            print(thrusters.set_all(pct) if tid == "all" else thrusters.set_thruster(tid, pct))
        elif choice == "9":
            st = input("Station to dock with (leave blank for nearby): ").strip()
            dock.hold_dock(st or None)
        elif choice == "10":
            print(f"State: {laser.state()}")
            sub = input("Action (activate/deactivate/angle/login): ").strip().lower()
            if sub in ("activate", "on"):
                print(laser.activate())
            elif sub in ("deactivate", "off"):
                print(laser.deactivate())
            elif sub == "angle":
                deg = float(input("Angle degrees: ") or 0)
                print(laser.set_angle(deg))
            elif sub == "login":
                print(laser.login())

menu()
