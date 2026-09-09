import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

# Public third-party Pocket Option OTC data service.
# No Pocket Option account, password, or SSID is used by this provider.
DATA_API_BASE = os.getenv("POCKET_OTC_DATA_API", "https://api1.api.cbtraderbd.xyz").rstrip("/")


class PocketDataError(Exception):
    pass


def _extract_price(data: Any) -> float | None:
    """Extract a positive price from common API response shapes."""
    if isinstance(data, dict):
        for key in ("price", "close", "last", "value", "current_price"):
            value = data.get(key)
            if isinstance(value, (int, float, str)):
                try:
                    price = float(value)
                    if price > 0:
                        return price
                except (TypeError, ValueError):
                    pass
        for key in ("data", "result", "ticker", "quote"):
            if key in data:
                price = _extract_price(data[key])
                if price is not None:
                    return price
    elif isinstance(data, list):
        for item in reversed(data):
            price = _extract_price(item)
            if price is not None:
                return price
    return None


def _extract_rows(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "result", "candles", "rows", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def _normalize_candle(row: Any) -> dict | None:
    if not isinstance(row, dict):
        return None
    try:
        timestamp = row.get("timestamp", row.get("time", row.get("t")))
        return {
            "timestamp": timestamp,
            "open": float(row.get("open", row.get("o"))),
            "high": float(row.get("high", row.get("h"))),
            "low": float(row.get("low", row.get("l"))),
            "close": float(row.get("close", row.get("c"))),
        }
    except (TypeError, ValueError):
        return None


async def _get_json(path: str, params: dict[str, Any]) -> Any:
    url = f"{DATA_API_BASE}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        raise PocketDataError(f"OTC data API request failed: {exc}") from exc


async def get_live_price(pair: str) -> float:
    """Get the latest OTC price from the public third-party data API."""
    # The API documentation uses live-price for the realtime quote endpoint.
    data = await _get_json("api/pocket-option/live-price", {"symbol": pair})
    price = _extract_price(data)
    if price is None:
        raise PocketDataError(f"No live price returned for {pair}")
    return price


async def get_closed_candles(pair: str) -> list[dict]:
    """Get real OTC candles without connecting to the user's Pocket Option account."""
    data = await _get_json(
        "api/pocket-option/candles",
        {"symbol": pair, "timeframe": 60, "limit": 100},
    )
    candles = [_normalize_candle(row) for row in _extract_rows(data)]
    candles = [c for c in candles if c is not None]
    if not candles:
        raise PocketDataError(f"No real OTC candles returned for {pair}")
    return candles[-100:]


def normalize(rows):
    """Backward-compatible normalizer for callers/tests."""
    out = [_normalize_candle(row) for row in rows]
    out = [c for c in out if c is not None]
    if not out:
        raise PocketDataError("Received candle objects could not be normalized")
    return out
