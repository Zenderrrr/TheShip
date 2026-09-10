import nav

def show():
    """Queries and displays real-time ship status."""
    pos = nav._http_get(2011, "pos").get("pos", {})
    vel = nav._http_get(2011, "pos").get("velocity", {})
    hold = nav._http_get(2012, "hold").get("hold", {})
    stations = nav._http_get(2011, "stations_in_reach").get("stations", {})

    items = [f"{k}: {v}" for k, v in hold.get("resources", {}).items() if v > 0]
    cargo = ", ".join(items) if items else "Empty"

    print("-" * 40)
    print("          THE SHIP — STATUS")
    print("-" * 40)
    print(f"Position : ({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f}) | Heading: {pos.get('angle', 0):.1f}°")
    print(f"Velocity : ({vel.get('x', 0):.1f}, {vel.get('y', 0):.1f})")
    print(f"Cargo    : {cargo} | Credits: {hold.get('credits', 0)}")
    print(f"In Reach : {', '.join(stations.keys()) if stations else 'None'}")
    print("-" * 40)

if __name__ == "__main__":
    show()
