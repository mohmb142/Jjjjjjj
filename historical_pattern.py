"""Historical pattern matching engine for OTC M1 candles.

It deliberately refuses weak samples. It does not claim that a historical
match guarantees the next candle; it only reports what happened after similar
historical windows.
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Iterable


LOOKBACK = 8
HORIZON = 1
MIN_MATCHES = int(os.getenv("PATTERN_MIN_MATCHES", "8"))
MIN_WIN_RATE = float(os.getenv("PATTERN_MIN_WIN_RATE", "0.65"))
MAX_DISTANCE = float(os.getenv("PATTERN_MAX_DISTANCE", "0.55"))


def _close(row):
    try:
        return float(row.get("close", row.get("c")))
    except (TypeError, ValueError):
        return None


def _feature_window(rows):
    prices = [_close(x) for x in rows]
    if len(prices) != LOOKBACK + 1 or any(x is None or x <= 0 for x in prices):
        return None
    returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
    scale = max(sum(abs(x) for x in returns) / len(returns), 1e-8)
    # Normalize shape so matching is about movement structure, not price level.
    return [x / scale for x in returns]


def _distance(a, b):
    if len(a) != len(b):
        return 999.0
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def _load_file(path: str, asset: str | None = None):
    p = Path(path)
    if not p.exists():
        return []
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("candles") or data.get("data") or data.get("rows") or []
        return [x for x in data if isinstance(x, dict) and (not asset or str(x.get("asset", "")).lower() in {asset.lower(), asset.lower().replace("_otc", "")})]
    if p.suffix.lower() in {".csv", ".gz"} or p.name.endswith(".csv.gz"):
        with p.open("rt", encoding="utf-8", newline="") as fh:
            return [x for x in csv.DictReader(fh) if not asset or str(x.get("asset", "")).lower() in {asset.lower(), asset.lower().replace("_otc", "")}]
    return []


def _find_source(asset: str):
    root = os.getenv("PATTERN_DATASET_DIR", "data/patterns")
    candidates = [
        os.path.join(root, f"{asset}.json"),
        os.path.join(root, f"{asset}.csv"),
        os.path.join(root, f"{asset}.csv.gz"),
        os.path.join(root, "candles.json"),
        os.path.join(root, "candles.csv"),
    ]
    for path in candidates:
        rows = _load_file(path, asset)
        if len(rows) >= LOOKBACK + HORIZON + MIN_MATCHES:
            return rows, path
    return [], None


def _result(signal="NO TRADE", confidence=0, matches=0, win_rate=None, reason=""):
    return {
        "signal": signal,
        "direction": "UP" if signal == "CALL" else "DOWN" if signal == "PUT" else "NEUTRAL",
        "confidence": int(max(0, min(99, confidence))),
        "matches": matches,
        "win_rate": None if win_rate is None else round(win_rate * 100, 1),
        "reason": reason,
        "method": "HISTORICAL_PATTERN_MATCHING",
        "expiry_minutes": 1,
    }


def analyze_historical_pattern(candles: list[dict], asset: str | None = None):
    """Find similar historical windows and measure their next-candle outcome.

    If PATTERN_DATASET_DIR contains a larger dataset, it is preferred. Otherwise
    the supplied candle history is used as a small local history and the engine
    stays conservative.
    """
    if len(candles) < LOOKBACK + HORIZON + MIN_MATCHES:
        return _result(reason="لا توجد شموع تاريخية كافية لبناء عينة موثوقة.")

    source_rows, source_path = _find_source(asset or "") if asset else ([], None)
    rows = source_rows or candles
    query = _feature_window(candles[-(LOOKBACK + 1):])
    if query is None:
        return _result(reason="تعذر بناء نمط سعري من الشموع الحالية.")

    candidates = []
    # Exclude the current query window and require a full future candle.
    limit = len(rows) - LOOKBACK - HORIZON
    for i in range(max(0, limit)):
        window = rows[i:i + LOOKBACK + 1]
        feat = _feature_window(window)
        if feat is None:
            continue
        distance = _distance(query, feat)
        if distance > MAX_DISTANCE:
            continue
        base = _close(rows[i + LOOKBACK])
        future = _close(rows[i + LOOKBACK + HORIZON])
        if base is None or future is None or base <= 0:
            continue
        change = future / base - 1
        outcome = 1 if change > 0 else -1 if change < 0 else 0
        candidates.append((distance, outcome, change))

    candidates.sort(key=lambda x: x[0])
    candidates = candidates[:30]
    if len(candidates) < MIN_MATCHES:
        return _result(matches=len(candidates), reason=f"وجدت {len(candidates)} حالات مشابهة فقط؛ الحد الأدنى {MIN_MATCHES}. القرار: NO TRADE.")

    usable = [x for x in candidates if x[1] != 0]
    ups = sum(1 for x in usable if x[1] > 0)
    downs = sum(1 for x in usable if x[1] < 0)
    total = len(usable)
    if total < MIN_MATCHES:
        return _result(matches=total, reason="العينات المتشابهة تحتوي على نتائج محايدة كثيرة؛ لا توجد أفضلية إحصائية كافية.")

    if ups >= downs:
        win_rate = ups / total
        signal = "CALL" if win_rate >= MIN_WIN_RATE else "NO TRADE"
    else:
        win_rate = downs / total
        signal = "PUT" if win_rate >= MIN_WIN_RATE else "NO TRADE"

    # Confidence is tied to both edge and sample size; it is not an AI guess.
    edge = abs(max(ups, downs) / total - 0.5) * 2
    sample_factor = min(1.0, total / 20)
    confidence = round(50 + 45 * edge * sample_factor) if signal != "NO TRADE" else round(50 + 20 * edge)
    source_note = f" من المصدر {source_path}" if source_path else " من سجل الشموع المتاح"
    reason = f"تمت مطابقة {total} حالة تاريخية مشابهة{source_note}. النتيجة: صعود {ups} مقابل هبوط {downs}؛ أفضلية {win_rate*100:.1f}%."
    if signal == "NO TRADE":
        reason += " الأفضلية لم تتجاوز الحد المطلوب."
    return _result(signal, confidence, total, win_rate, reason)


def load_candles_from_dataset(path: str, asset: str | None = None):
    """Utility for converting a downloaded CSV/JSON candle file into rows."""
    return _load_file(path, asset)
