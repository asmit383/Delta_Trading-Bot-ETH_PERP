import requests
import pandas as pd
import time

def fetch_historical_data(symbol="ETHUSDT", resolution="1m", days=120):
    url = "https://api.delta.exchange/v2/history/candles"

    # 1-min candles per day = 1440
    candles_per_day = {"1m": 1440, "5m": 288, "15m": 96, "1h": 24}
    candles_needed  = days * candles_per_day.get(resolution, 1440)
    mins_per_candle = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}.get(resolution, 1)
    limit_per_req   = 2000  # Delta API max

    end_time = int(time.time())
    all_candles = []

    print(f"Fetching ~{candles_needed} candles ({days} days) for {symbol} at {resolution} resolution...")

    while len(all_candles) < candles_needed:
        current_start = end_time - (limit_per_req * mins_per_candle * 60)

        params = {
            "symbol":     symbol,
            "resolution": resolution,
            "start":      current_start,
            "end":        end_time,
        }

        response = requests.get(url, params=params)
        data     = response.json()

        if not data.get("success"):
            print(f"API error: {data}")
            break

        candles = data.get("result", [])
        if not candles:
            print("No more candles returned from API.")
            break

        all_candles.extend(candles)
        print(f"  Fetched {len(candles)} candles | Total so far: {len(all_candles)}")

        # Roll the window backward
        earliest = min(c['time'] for c in candles)
        # time field is in seconds on Delta Exchange
        end_time = int(earliest) - 1

        time.sleep(0.4)   # be nice to the API

    if not all_candles:
        print("No data fetched.")
        return

    df = pd.DataFrame(all_candles)

    # Detect timestamp unit (seconds vs ms vs us)
    sample = df['time'].iloc[0]
    if sample > 1e12:
        unit = 'ms'
    else:
        unit = 's'

    df['timestamp'] = pd.to_datetime(df['time'], unit=unit)
    df = df.drop_duplicates(subset=['time'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Keep only the most recent candles needed
    df = df.tail(candles_needed).reset_index(drop=True)

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df.to_csv("data.csv", index=False)

    print(f"\nDone! Saved {len(df)} rows to data.csv")
    print(f"  From : {df['timestamp'].iloc[0]}")
    print(f"  To   : {df['timestamp'].iloc[-1]}")

if __name__ == "__main__":
    fetch_historical_data(days=360)
