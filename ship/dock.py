#!/usr/bin/env python3
import time
import math
import config
import nav

def attach_to_station(station_name=None):
    st_name = config.normalize_station(station_name) if station_name else None
    print(f"🧲 Locking onto {st_name or 'nearby station'} (Ctrl+C to un-dock)...")
    try:
        while True:
            reach = nav._http_get(2011, "stations_in_reach").get("stations", {})
            if not st_name and reach:
                st_name = list(reach.keys())[0]
            
            p = nav._http_get(2011, "pos").get("pos", {})
            in_reach = st_name in reach if st_name else False
            
            if in_reach:
                print(f"\r🟢 LOCKED: {st_name} | Pos: ({p.get('x',0):.1f}, {p.get('y',0):.1f})   ", end="", flush=True)
            else:
                print(f"\r⚡ RE-ACQUIRING: {st_name or 'Station'}...   ", end="", flush=True)
                if st_name in config.STATIONS:
                    nav.set_target(config.STATIONS[st_name])
            time.sleep(0.2)
    except KeyboardInterrupt:
        print(f"\n🛑 Un-docked from {st_name or 'station'}.")
        nav.stop_ship()

if __name__ == "__main__":
    import sys
    attach_to_station(sys.argv[1] if len(sys.argv) > 1 else None)
