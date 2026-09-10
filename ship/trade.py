import sys
import config
import nav

def buy(station, resource="IRON", amount=10):
    """Buys resources from a nearby station."""
    st = config.normalize_station(station)
    return nav._http_post(2011, "buy", {"station": st, "what": resource.upper(), "amount": int(amount)})

def sell(station, resource="IRON", amount=10):
    """Sells resources to a nearby station."""
    st = config.normalize_station(station)
    return nav._http_post(2011, "sell", {"station": st, "what": resource.upper(), "amount": int(amount)})

if __name__ == "__main__":
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        st = sys.argv[2] if len(sys.argv) > 2 else "Azura Station"
        res = sys.argv[3] if len(sys.argv) > 3 else "IRON"
        amt = int(sys.argv[4]) if len(sys.argv) > 4 else 10

        if action == "buy":
            print(buy(st, res, amt))
        elif action == "sell":
            print(sell(st, res, amt))
