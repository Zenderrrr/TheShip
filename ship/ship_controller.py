#!/usr/bin/env python3
import sys
import json
import argparse
import config
import nav
import status
import trade
import thrusters
import dock

def menu():
    while True:
        print("\n" + "=" * 45)
        print("        🚀 THE SHIP — CONSOLE")
        print("=" * 45)
        print("  [1] 📊 Status Overview\n  [2] 🧭 Fly to Station\n  [3] 📍 Fly to (X, Y)\n  [4] 🛑 Stop\n  [5] 💨 Idle\n  [6] 📦 Cargo\n  [7] 💰 Buy Resource\n  [8] 🏷️  Sell Resource\n  [9] 🔥 Thruster Control\n  [10] 🧲 Attach to Station\n  [0] ❌ Exit")
        print("=" * 45)

        try: choice = input("Select (0-10): ").strip()
        except (EOFError, KeyboardInterrupt): break

        if choice in ("0", "exit", "q"): break
        elif choice == "1": status.print_status()
        elif choice == "2":
            st_list = list(config.STATIONS.keys())
            for i, s in enumerate(st_list, 1): print(f"  [{i}] {s}")
            c = input(f"Choose (1-{len(st_list)}): ").strip()
            if c.isdigit() and 1 <= int(c) <= len(st_list): nav.fly_to(st_list[int(c)-1])
        elif choice == "3":
            try: nav.fly_to((float(input("X: ")), float(input("Y: "))))
            except ValueError: print("Invalid coords.")
        elif choice == "4": print(nav.stop_ship())
        elif choice == "5": print(nav.idle_ship())
        elif choice == "6": print(json.dumps(status.get_cargo(), indent=2))
        elif choice == "7":
            s = input("Station (Azura Station): ") or "Azura Station"
            r = input("Resource (IRON): ") or "IRON"
            a = int(input("Amount (10): ") or 10)
            print(trade.buy(s, r, a))
        elif choice == "8":
            s = input("Station (Core Station): ") or "Core Station"
            r = input("Resource (IRON): ") or "IRON"
            a = int(input("Amount (10): ") or 10)
            print(trade.sell(s, r, a))
        elif choice == "9":
            tid = input("Thruster (1-5 or 'all'): ")
            pct = int(input("Percent (0-100): ") or 0)
            print(thrusters.set_all(pct) if tid == "all" else thrusters.set_thruster(tid, pct))
        elif choice == "10": dock.attach_to_station()

def main():
    parser = argparse.ArgumentParser(description="The Ship Controller")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("status")
    sub.add_parser("stop")
    sub.add_parser("idle")
    p_nav = sub.add_parser("nav"); p_nav.add_argument("target"); p_nav.add_argument("y", nargs="?", default=None)
    p_buy = sub.add_parser("buy"); p_buy.add_argument("station"); p_buy.add_argument("what"); p_buy.add_argument("amount", type=int)
    p_sell = sub.add_parser("sell"); p_sell.add_argument("station"); p_sell.add_argument("what"); p_sell.add_argument("amount", type=int)
    p_thr = sub.add_parser("thruster"); p_thr.add_argument("id"); p_thr.add_argument("percent", type=int)

    args = parser.parse_args()
    if not args.cmd: menu()
    elif args.cmd == "status": status.print_status()
    elif args.cmd == "stop": print(nav.stop_ship())
    elif args.cmd == "idle": print(nav.idle_ship())
    elif args.cmd == "nav": nav.fly_to((float(args.target), float(args.y)) if args.y else args.target)
    elif args.cmd == "buy": print(trade.buy(args.station, args.what, args.amount))
    elif args.cmd == "sell": print(trade.sell(args.station, args.what, args.amount))
    elif args.cmd == "thruster": print(thrusters.set_all(args.percent) if args.id == "all" else thrusters.set_thruster(args.id, args.percent))

if __name__ == "__main__":
    main()
