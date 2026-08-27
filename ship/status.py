#!/usr/bin/env python3
import config

# query ship position and velocity
def get_telemetry():
    # fetch position telemetry
    return config.curl(f"http://{config.HOST}:2011/pos")

# query cargo hold inventory and credits
def get_cargo():
    # fetch cargo inventory
    return config.curl(f"http://{config.HOST}:2012/hold")

# query nearby stations and resource prices
def get_stations_in_reach():
    # check stations in reach
    return config.curl(f"http://{config.HOST}:2011/stations_in_reach")

# print status overview
def print_status():
    telemetry = get_telemetry()
    cargo = get_cargo()
    stations = get_stations_in_reach()

    print("=" * 60)
    print("                 THE SHIP — STATUS OVERVIEW")
    print("=" * 60)

    # position & velocity
    if isinstance(telemetry, dict) and telemetry.get("kind") == "success":
        pos = telemetry.get("pos", {})
        vel = telemetry.get("velocity", {})
        print(f"📍 POSITION : X: {pos.get('x', 0):.1f} | Y: {pos.get('y', 0):.1f} | Angle: {pos.get('angle', 0):.1f}°")
        print(f"💨 VELOCITY : X: {vel.get('x', 0):.1f} | Y: {vel.get('y', 0):.1f} | Speed: {vel.get('angle', 0):.1f}")
    else:
        print("📍 POSITION : Offline / Unreachable")

    print("-" * 60)

    # cargo
    if isinstance(cargo, dict) and cargo.get("kind") == "success":
        hold = cargo.get("hold", {})
        res = hold.get("resources", {})
        credits_val = hold.get("credits", 0)
        h_size = hold.get("hold_size", 12)
        h_free = hold.get("hold_free", 12)
        active_res = [f"{k}: {v}" for k, v in res.items() if v > 0]
        inv_str = ", ".join(active_res) if active_res else "(Empty)"

        print(f"📦 CARGO    : {h_size - h_free}/{h_size} used ({h_free} free)")
        print(f"💰 CREDITS  : {credits_val} ¢")
        print(f"💎 HOLD     : {inv_str}")
    else:
        print("📦 CARGO    : Offline")

    print("-" * 60)

    # nearby stations
    reach = stations.get("stations", {}) if isinstance(stations, dict) else {}
    if reach:
        print("🪐 NEARBY STATIONS:")
        for name, data in reach.items():
            print(f"  • {name}:")
            for r_name, p in data.get("resources", {}).items():
                print(f"      - {r_name}: Buy={p.get('buy_price')}¢ | Sell={p.get('sell_price')}¢")
    else:
        print("🪐 NEARBY STATIONS: None in range.")
    print("=" * 60)

if __name__ == "__main__":
    print_status()
