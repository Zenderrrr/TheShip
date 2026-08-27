#!/usr/bin/env python3
import json
import nav
import config

# buy resources from a station
def buy(station, resource="IRON", amount=10):
    st_name = config.normalize_station(station)
    payload = json.dumps({"station": st_name, "what": resource.upper(), "amount": int(amount)})
    # send buy request
    return config.curl(f'-XPOST http://{config.HOST}:2011/buy -H "Content-Type: application/json" -d \'{payload}\'')

# sell resources to a station
def sell(station, resource="IRON", amount=10):
    st_name = config.normalize_station(station)
    payload = json.dumps({"station": st_name, "what": resource.upper(), "amount": int(amount)})
    # send sell request
    return config.curl(f'-XPOST http://{config.HOST}:2011/sell -H "Content-Type: application/json" -d \'{payload}\'')

def main():
    print("1) Buy Iron in Azura Station")
    print("2) Sell Iron in Core Station")
    choice = input("Choose option (1-2): ").strip()

    if choice not in ["1", "2"]:
        print("Invalid choice.")
        return

    amount_str = input("Amount (default 10): ").strip() or "10"
    amount = int("".join(c for c in amount_str if c.isdigit()) or 10)

    if choice == "1":
        station = "Azura Station"
        nav.fly_to(station)
        print(f"\nExecuting buy ({amount} IRON at {station})...")
        res = buy(station, "IRON", amount)
    else:
        station = "Core Station"
        nav.fly_to(station)
        print(f"\nExecuting sell ({amount} IRON at {station})...")
        res = sell(station, "IRON", amount)

    print("Response:", res)

if __name__ == "__main__":
    main()
