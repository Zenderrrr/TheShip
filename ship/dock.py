import sys
import time
import config
import nav

def hold_dock(station_name=None):
    """Holds position near a target station."""
    st = config.normalize_station(station_name) if station_name else None
    print(f"Holding position at {st or 'nearby station'} (press Ctrl+C to stop)...")

    try:
        while True:
            reach = nav._http_get(2011, "stations_in_reach").get("stations", {})

            # Latch onto any station in range if none specified
            if not st and reach:
                st = list(reach.keys())[0]

            in_reach = st in reach if st else False
            pos = nav._http_get(2011, "pos").get("pos", {})

            if in_reach:
                print(f"\rDocked at {st} | Pos: ({pos.get('x', 0):.0f}, {pos.get('y', 0):.0f})", end="", flush=True)
            else:
                print(f"\rRe-aligning with {st or 'station'}...", end="", flush=True)
                if st in config.STATIONS:
                    nav.set_target(config.STATIONS[st])

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        nav.stop_ship()

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    hold_dock(target)
