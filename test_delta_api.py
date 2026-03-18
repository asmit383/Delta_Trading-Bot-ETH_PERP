import requests
import time

BASE_URL = "https://api.india.delta.exchange"

def test():
    # Find ETHUSDT product and its ID
    url = f"{BASE_URL}/v2/products"
    data = requests.get(url).json()
    eth_products = [
        {"symbol": p["symbol"], "id": p["id"], "description": p.get("description", ""), "type": p.get("product_type", "")}
        for p in data.get("result", [])
        if "ETH" in p["symbol"].upper() and "USD" in p["symbol"].upper()
        and "C-" not in p["symbol"] and "P-" not in p["symbol"]  # exclude options
    ]
    print(f"ETH/USD non-option products ({len(eth_products)} found):")
    for p in eth_products:
        print(f"  symbol={p['symbol']}  id={p['id']}  type={p['type']}  desc={p['description']}")

    # Try fetching candles with required 'end' param
    symbol = "ETHUSD"
    end   = int(time.time())
    start = end - 60 * 10   # last 10 minutes

    url_candles = f"{BASE_URL}/v2/history/candles"
    params = {"symbol": symbol, "resolution": "1m", "start": start, "end": end}
    res_json = requests.get(url_candles, params=params).json()

    if res_json.get("success"):
        candles = res_json.get("result", [])
        print(f"\nCandles fetch OK — got {len(candles)} candles for {symbol}")
        if candles:
            print("Latest candle:", candles[-1])
    else:
        print("\nFailed to fetch candles:", res_json)

test()
