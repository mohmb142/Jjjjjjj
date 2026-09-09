import os
from dotenv import load_dotenv

load_dotenv()

class PocketDataError(Exception):
    pass


async def _client():
    ssid = os.getenv("POCKET_OPTION_SSID", "").strip()
    if not ssid:
        raise PocketDataError("POCKET_OPTION_SSID is not configured")
    try:
        from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
    except Exception as e:
        raise PocketDataError(f"BinaryOptionsToolsV2 import failed: {e}")
    client = PocketOptionAsync(ssid)
    await client.connect()
    return client


async def get_live_price(pair: str) -> float:
    """Read the latest real-time Pocket Option price without placing any trade."""
    client = await _client()
    try:
        stream = await client.subscribe_symbol(pair)
        async for tick in stream:
            if not isinstance(tick, dict):
                continue
            raw = tick.get("close", tick.get("price"))
            if raw is not None:
                price = float(raw)
                if price > 0:
                    return price
        raise PocketDataError(f"No live price received for {pair}")
    except PocketDataError:
        raise
    except Exception as e:
        raise PocketDataError(f"Live price error for {pair}: {e}")
    finally:
        try:
            await client.shutdown()
        except Exception:
            pass


async def get_closed_candles(pair: str):
    client = await _client()
    try:
        rows = []
        async for closed, forming in client.get_candles_live(
            pair, period=60, hours=2.0, max_rows=100
        ):
            if closed:
                rows.append(closed)
            if len(rows) >= 100:
                break
        if not rows:
            raise PocketDataError("Pocket Option returned no closed real candles")
        return normalize(rows)
    except PocketDataError:
        raise
    except Exception as e:
        raise PocketDataError(f"Pocket Option connection/data error: {e}")
    finally:
        try:
            await client.shutdown()
        except Exception:
            pass


def normalize(rows):
    out = []
    for x in rows:
        d = x if isinstance(x, dict) else (vars(x) if hasattr(x, "__dict__") else {})
        try:
            out.append({
                "timestamp": d.get("timestamp", d.get("time")),
                "open": float(d["open"]),
                "high": float(d["high"]),
                "low": float(d["low"]),
                "close": float(d["close"]),
            })
        except Exception:
            continue
    if not out:
        raise PocketDataError("Received candle objects could not be normalized")
    return out
