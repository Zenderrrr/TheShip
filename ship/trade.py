#!/usr/bin/env python3
import config
import nav

def buy(station, resource="IRON", amount=10):
    st = config.normalize_station(station)
    return nav._http_post(2011, "buy", {"station": st, "what": resource.upper(), "amount": int(amount)})

def sell(station, resource="IRON", amount=10):
    st = config.normalize_station(station)
    return nav._http_post(2011, "sell", {"station": st, "what": resource.upper(), "amount": int(amount)})

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "buy"
    st = sys.argv[2] if len(sys.argv) > 2 else "Azura Station"
    res = sys.argv[3] if len(sys.argv) > 3 else "IRON"
    amt = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    print(buy(st, res, amt) if action == "buy" else sell(st, res, amt))
