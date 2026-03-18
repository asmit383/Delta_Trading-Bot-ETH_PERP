import asyncio
import websockets
import json

async def test_delta_ws():
    # Use the India socket as we saw it connect fine
    uri = "wss://socket.india.delta.exchange" 
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Subscribing to what appeared in your previous successful log
            subscribe_msg = {
                "type": "subscribe",
                "payload": {
                    "channels": [
                        {
                            "name": "candlestick_1m",
                            "symbols": ["ETHUSD"]
                        },
                        {
                            "name": "v2/ticker",
                            "symbols": ["ETHUSD"]
                        }
                    ]
                }
            }
            
            await websocket.send(json.dumps(subscribe_msg))
            print("Subscription message sent...")
            
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print("Received:", json.dumps(data, indent=2))
                    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_delta_ws())