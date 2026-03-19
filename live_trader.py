"""
Live Trader — Delta Exchange India
  Entry  : Market order (next candle open)
  SL     : Stop-Market  at entry ± STOP_LOSS_PCT
  TP     : Limit order  at entry ± TAKE_PROFIT_PCT
  TIME   : Market close after TIME_EXIT_CANDLES candles regardless of P&L
  Signal : Same mean-reversion logic as backtester
  WS     : wss://socket.india.delta.exchange  (candlestick_1m + orders)
"""

import asyncio
import websockets
import json
import time
import hmac
import hashlib
import requests
import logging
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def is_asian_session() -> bool:
    """Returns True if current IST time is within Asian session (05:30 - 11:30)."""
    now = datetime.now(IST)
    start = now.replace(hour=5,  minute=30, second=0, microsecond=0)
    end   = now.replace(hour=11, minute=30, second=0, microsecond=0)
    return start <= now <= end

from secret import API_KEY, API_SECRET, ETH_PRODUCT_ID
from config import Config

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL     = "https://api.india.delta.exchange"
WS_URL       = "wss://socket.india.delta.exchange"
SYMBOL       = "ETHUSD"
RECONNECT_DELAY = 5   # seconds to wait before reconnecting on WS drop

cfg = Config()

session = requests.Session()  # persistent connection — reused for all REST calls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _rest_headers(method: str, path: str, body: str = "") -> dict:
    ts  = str(int(time.time()))
    msg = method + ts + path + body
    sig = hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return {
        "api-key":      API_KEY,
        "timestamp":    ts,
        "signature":    sig,
        "Content-Type": "application/json",
    }


def _ws_auth_payload() -> dict:
    ts  = str(int(time.time()))
    sig = hmac.new(API_SECRET.encode(), f"GET{ts}/live".encode(), hashlib.sha256).hexdigest()
    return {"api-key": API_KEY, "signature": sig, "timestamp": ts}


# ── Leverage setup ────────────────────────────────────────────────────────────

def set_leverage():
    path = "/v2/products/leverage"
    body = json.dumps({"product_id": ETH_PRODUCT_ID, "leverage": int(cfg.LEVERAGE)})
    try:
        resp = session.post(BASE_URL + path, headers=_rest_headers("POST", path, body), data=body, timeout=5)
        data = resp.json()
        if data.get("success"):
            log.info(f"Leverage set to {int(cfg.LEVERAGE)}x on exchange")
        else:
            log.warning(f"Could not set leverage: {data}")
    except Exception as e:
        log.error(f"Leverage set exception: {e}")


# ── Position sync ─────────────────────────────────────────────────────────────

def has_open_position() -> bool:
    """Returns True if there is already an open ETHUSD position on the exchange."""
    path = f"/v2/positions?product_id={ETH_PRODUCT_ID}"
    try:
        resp = session.get(BASE_URL + path, headers=_rest_headers("GET", path), timeout=5)
        data = resp.json()
    except Exception as e:
        log.error(f"Position sync exception: {e}")
        return False
    if not data.get("success"):
        log.error(f"Position sync failed: {data}")
        return False
    result = data.get("result", {})
    size = float(result.get("size", 0)) if isinstance(result, dict) else 0
    if size != 0:
        log.info(f"Open position detected on startup | size={size} | syncing in_position=True")
        return True
    log.info("No open position on startup")
    return False


# ── Signal ────────────────────────────────────────────────────────────────────

def get_signal(open_: float, close_: float) -> int:
    body_pct = (close_ - open_) / open_
    if abs(body_pct) >= cfg.REVERSAL_CANDLE_PCT:
        return -1 if body_pct > 0 else 1
    return 0


# ── Order placement ───────────────────────────────────────────────────────────

def place_bracket_order(side: str, size: int, entry_price: float) -> dict:
    if side == "buy":
        sl_trigger = round(entry_price * (1 - cfg.STOP_LOSS_PCT), 2)
        tp_price   = round(entry_price * (1 + cfg.TAKE_PROFIT_PCT), 2)
    else:
        sl_trigger = round(entry_price * (1 + cfg.STOP_LOSS_PCT), 2)
        tp_price   = round(entry_price * (1 - cfg.TAKE_PROFIT_PCT), 2)

    body = json.dumps({
        "product_id":                      ETH_PRODUCT_ID,
        "order_type":                      "market_order",
        "side":                            side,
        "size":                            size,
        "bracket_stop_loss_price":         str(sl_trigger),   # stop market — no limit price
        "bracket_take_profit_price":       str(tp_price),
        "bracket_take_profit_limit_price": str(tp_price),
    })

    path = "/v2/orders"
    try:
        resp = session.post(BASE_URL + path, headers=_rest_headers("POST", path, body), data=body, timeout=5)
        return resp.json()
    except Exception as e:
        log.error(f"Order placement exception: {e}")
        return {}


def close_position(side: str, size: int) -> dict:
    """Market close — opposite side, reduce_only. Also cancels bracket orders."""
    close_side = "sell" if side == "buy" else "buy"
    body = json.dumps({
        "product_id":  ETH_PRODUCT_ID,
        "order_type":  "market_order",
        "side":        close_side,
        "size":        size,
        "reduce_only": True,
    })
    path = "/v2/orders"
    try:
        resp = session.post(BASE_URL + path, headers=_rest_headers("POST", path, body), data=body, timeout=5)
        return resp.json()
    except Exception as e:
        log.error(f"Close position exception: {e}")
        return {}


# ── WS session ────────────────────────────────────────────────────────────────

async def _session(in_position: bool, current_candle: dict):
    in_position         = has_open_position()
    candle_count        = 0
    trade_side          = None
    trade_size          = 0
    traded_candle_start = None
    check_task          = None

    # ── T-300ms scheduled check ───────────────────────────────────────────────
    async def _check_at_t_minus_300(scheduled_candle_start, fire_at: float):
        nonlocal in_position, traded_candle_start, trade_side, trade_size, candle_count

        sleep_for = fire_at - time.time()
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)

        # Guards
        if in_position:
            return
        if traded_candle_start == scheduled_candle_start:
            return
        if current_candle is None or current_candle["start"] != scheduled_candle_start:
            return  # candle already closed before we woke up
        if not is_asian_session():
            log.info("Outside Asian session (05:30-11:30 IST) — skipping")
            return

        signal = get_signal(current_candle["open"], current_candle["close"])
        if signal == 0:
            log.info(f"T-400ms check: body < {cfg.REVERSAL_CANDLE_PCT*100:.2f}% — no trade")
            return

        traded_candle_start = scheduled_candle_start
        t_signal    = time.time()
        side        = "buy" if signal == 1 else "sell"
        entry_price = current_candle["close"]
        size        = cfg.ORDER_SIZE

        if side == "buy":
            sl_p = round(entry_price * (1 - cfg.STOP_LOSS_PCT), 2)
            tp_p = round(entry_price * (1 + cfg.TAKE_PROFIT_PCT), 2)
        else:
            sl_p = round(entry_price * (1 + cfg.STOP_LOSS_PCT), 2)
            tp_p = round(entry_price * (1 - cfg.TAKE_PROFIT_PCT), 2)

        log.info(f"T-300ms Signal: {'LONG' if signal == 1 else 'SHORT'} | "
                 f"entry≈{entry_price} | SL={sl_p} | TP={tp_p} | contracts={size}")

        result = place_bracket_order(side, size, entry_price)
        t_order = time.time()

        if result.get("success"):
            in_position  = True
            candle_count = 0
            trade_side   = side
            trade_size   = size
            log.info(f"Bracket order placed | id={result['result']['id']} | "
                     f"delay={t_order - t_signal:.3f}s")
        else:
            log.error(f"Order failed: {result}")

    # ── WS connection ─────────────────────────────────────────────────────────
    async with websockets.connect(WS_URL) as ws:

        await ws.send(json.dumps({"type": "auth", "payload": _ws_auth_payload()}))
        await ws.send(json.dumps({
            "type": "subscribe",
            "payload": {
                "channels": [
                    {"name": "candlestick_1m", "symbols": [SYMBOL]},
                    {"name": "orders",          "symbols": [SYMBOL]},
                ]
            }
        }))

        log.info(f"Connected | symbol={SYMBOL} | leverage={cfg.LEVERAGE}x | "
                 f"reversal={cfg.REVERSAL_CANDLE_PCT*100:.2f}% "
                 f"TP={cfg.TAKE_PROFIT_PCT*100:.2f}% "
                 f"SL={cfg.STOP_LOSS_PCT*100:.2f}% "
                 f"TIME={cfg.TIME_EXIT_CANDLES} candles")
        if in_position:
            log.info("Resuming — position still open from before reconnect")

        async for raw in ws:
            msg      = json.loads(raw)
            msg_type = msg.get("type")

            # ── Order update: TP or SL hit ────────────────────────────────────
            if msg_type == "orders":
                order = msg.get("order", {})
                state = order.get("state", "")
                if state in ("closed", "cancelled") and in_position:
                    reason = order.get("close_reason", "unknown")
                    log.info(f"Position closed | reason={reason} | ready for next signal")
                    in_position  = False
                    candle_count = 0
                    trade_side   = None
                    trade_size   = 0

            # ── Candlestick update ────────────────────────────────────────────
            elif msg_type == "candlestick_1m":
                new_start = msg.get("candle_start_time")
                o = float(msg.get("open",  0))
                c = float(msg.get("close", 0))

                # ── New candle detected ───────────────────────────────────────
                if current_candle and new_start != current_candle["start"]:

                    # Cancel previous T-300ms task (it's stale)
                    if check_task and not check_task.done():
                        check_task.cancel()

                    # Time exit counter
                    if in_position:
                        if not has_open_position():
                            log.info("Position already closed by TP/SL — resetting")
                            in_position  = False
                            candle_count = 0
                            trade_side   = None
                            trade_size   = 0

                    if in_position:
                        candle_count += 1
                        log.info(f"Candle {candle_count}/{cfg.TIME_EXIT_CANDLES} in position")

                        if candle_count >= cfg.TIME_EXIT_CANDLES:
                            log.info(f"TIME EXIT — {cfg.TIME_EXIT_CANDLES} candles elapsed, closing now")
                            result = close_position(trade_side, trade_size)
                            if result.get("success"):
                                log.info("Time exit order placed successfully")
                            elif result.get("error", {}).get("code") == "no_position_for_reduce_only":
                                log.info("Time exit: position already closed by TP/SL — flag was stale")
                            else:
                                log.error(f"Time exit order failed: {result}")
                            in_position  = False
                            candle_count = 0
                            trade_side   = None
                            trade_size   = 0

                    # Schedule T-300ms check for the new candle
                    if not in_position:
                        candle_start_unix = new_start / 1_000_000 if new_start > 1e12 else new_start
                        fire_at = candle_start_unix + 60 - 0.4
                        check_task = asyncio.create_task(
                            _check_at_t_minus_300(new_start, fire_at)
                        )

                current_candle = {"open": o, "close": c, "start": new_start}

    return in_position, current_candle


# ── Entry point with auto-reconnect ──────────────────────────────────────────

async def run():
    in_position    = False
    current_candle = None

    set_leverage()

    while True:
        try:
            in_position, current_candle = await _session(in_position, current_candle)
        except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
            log.warning(f"WS disconnected: {e} — reconnecting in {RECONNECT_DELAY}s "
                        f"(in_position={in_position})")
            await asyncio.sleep(RECONNECT_DELAY)
        except Exception as e:
            log.error(f"Unexpected error: {e} — reconnecting in {RECONNECT_DELAY}s")
            await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    asyncio.run(run())
