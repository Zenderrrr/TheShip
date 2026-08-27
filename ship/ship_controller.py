#!/usr/bin/env python3
"""
================================================================================
          THE SHIP — MASTER CONTROLLER
================================================================================
Universal command-line tool and interactive console for controlling your ship.
"""

import sys
import json
import argparse
import config
import nav
import status
import trade
import thrusters

def interactive_menu():
    while True:
        print("\n" + "=" * 60)
        print("   🚀 THE SHIP — COMMAND CONSOLE")
        print("=" * 60)
        print("  [1]  📊 Status Overview")
        print("  [2]  🧭 Fly to Station")
        print("  [3]  📍 Fly to Custom Coordinates (X, Y)")
        print("  [4]  🛑 Emergency Stop")
        print("  [5]  💨 Idle / Drift Mode")
        print("  [6]  📦 Cargo Hold & Inventory")
        print("  [7]  🪐 Nearby Stations & Market Rates")
        print("  [8]  💰 Buy Resources")
        print("  [9]  🏷️  Sell Resources")
        print("  [10] 🔥 Thruster Control")
        print("  [0]  ❌ Exit Console")
        print("=" * 60)

        try:
            choice = input("\nSelect option (0-10): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if choice in ("0", "exit", "quit", "q"):
            print("Exiting console.")
            break

        elif choice == "1":
            print()
            status.print_status()

        elif choice == "2":
            print("\n--- Select Destination Station ---")
            st_keys = list(config.STATIONS.keys())
            for i, name in enumerate(st_keys, 1):
                print(f"  [{i}] {name} {config.STATIONS[name]}")
            st_c = input(f"Choose station (1-{len(st_keys)}): ").strip()
            if st_c.isdigit() and 1 <= int(st_c) <= len(st_keys):
                target_st = st_keys[int(st_c) - 1]
                nav.fly_to(target_st)

        elif choice == "3":
            try:
                x = float(input("Enter X coordinate: ").strip())
                y = float(input("Enter Y coordinate: ").strip())
                nav.fly_to((x, y))
            except ValueError:
                print("Invalid coordinates.")

        elif choice == "4":
            print("Stopping ship:", nav.stop_ship())

        elif choice == "5":
            print("Idling ship:", nav.idle_ship())

        elif choice == "6":
            print(json.dumps(status.get_cargo(), indent=2))

        elif choice == "7":
            print(json.dumps(status.get_stations_in_reach(), indent=2))

        elif choice == "8":
            st = input("Station (default: Azura Station): ").strip() or "Azura Station"
            res = input("Resource (default: IRON): ").strip().upper() or "IRON"
            amt = int(input("Amount (default: 10): ").strip() or 10)
            print(trade.buy(st, res, amt))

        elif choice == "9":
            st = input("Station (default: Core Station): ").strip() or "Core Station"
            res = input("Resource (default: IRON): ").strip().upper() or "IRON"
            amt = int(input("Amount (default: 10): ").strip() or 10)
            print(trade.sell(st, res, amt))

        elif choice == "10":
            tid_str = input("Thruster ID (1-5, or 'all'): ").strip().lower()
            pct = int(input("Power percentage (0-100): ").strip() or 0)
            if tid_str == "all":
                print(thrusters.set_all(pct))
            elif tid_str.isdigit() and 1 <= int(tid_str) <= 5:
                print(thrusters.set_thruster(int(tid_str), pct))


def main():
    parser = argparse.ArgumentParser(description="The Ship — Master Controller")

    sub = parser.add_subparsers(dest="command", help="Command to run")
    sub.add_parser("menu", help="Interactive numbered menu")
    sub.add_parser("status", help="Show ship status")
    sub.add_parser("cargo", help="Show cargo inventory")
    sub.add_parser("stations", help="Show nearby stations")
    sub.add_parser("stop", help="Emergency stop")
    sub.add_parser("idle", help="Idle drift")

    # nav
    nav_p = sub.add_parser("nav", help="Fly to station or (x, y) coords")
    nav_p.add_argument("target", help="Station name or X coordinate")
    nav_p.add_argument("y", nargs="?", help="Y coordinate if target is X", default=None)

    # buy / sell
    b_p = sub.add_parser("buy", help="Buy resources")
    b_p.add_argument("station", help="Station name")
    b_p.add_argument("what", help="Resource name")
    b_p.add_argument("amount", type=int, help="Amount")

    s_p = sub.add_parser("sell", help="Sell resources")
    s_p.add_argument("station", help="Station name")
    s_p.add_argument("what", help="Resource name")
    s_p.add_argument("amount", type=int, help="Amount")

    # thrusters
    t_p = sub.add_parser("thruster", help="Control thrusters")
    t_p.add_argument("id", help="Thruster ID (1-5 or 'all')")
    t_p.add_argument("percent", type=int, help="Thrust power (0-100)")

    args = parser.parse_args()

    if not args.command or args.command == "menu":
        if sys.stdin.isatty():
            interactive_menu()
        else:
            status.print_status()
        return

    if args.command == "status":
        status.print_status()
    elif args.command == "cargo":
        print(json.dumps(status.get_cargo(), indent=2))
    elif args.command == "stations":
        print(json.dumps(status.get_stations_in_reach(), indent=2))
    elif args.command == "stop":
        print(nav.stop_ship())
    elif args.command == "idle":
        print(nav.idle_ship())
    elif args.command == "nav":
        target = (float(args.target), float(args.y)) if args.y is not None else args.target
        print(nav.fly_to(target))
    elif args.command == "buy":
        print(trade.buy(args.station, args.what, args.amount))
    elif args.command == "sell":
        print(trade.sell(args.station, args.what, args.amount))
    elif args.command == "thruster":
        if args.id.lower() == "all":
            print(thrusters.set_all(args.percent))
        else:
            print(thrusters.set_thruster(int(args.id), args.percent))

if __name__ == "__main__":
    main()
