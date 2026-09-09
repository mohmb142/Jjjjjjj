import base64
import json
import os
from typing import Any

import httpx

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"
REQUIRED_KEYS = (
    "asset", "timeframe", "image_quality", "trend", "structure", "momentum",
    "volatility", "ema", "rsi", "macd", "support", "resistance",
    "candle_patterns", "confluence", "signal", "direction", "confidence",
    "reason", "risks",
)

SYSTEM_PROMPT = """
You are a chart-vision technical-analysis engine.
Analyze ONLY the supplied chart image. Never invent values that are unreadable.
This application is strictly READ-ONLY: never place, open, close, or automate trades.

Inspect the visible candles, market structure, momentum, volatility, support/resistance,
and visible indicators such as EMA, RSI and MACD. Identify contradictions and image
quality limitations. If the image is blurry, cropped, ambiguous, or evidence conflicts,
choose NO TRADE.

The requested horizon is 5 minutes. Do not claim certainty or guaranteed profit.
confidence is analytical confidence from 0 to 100, NOT probability of profit.

Return JSON only. Use exactly these keys:
asset, timeframe, image_quality, trend, structure, momentum, volatility,
ema, rsi, macd, support, resistance, candle_patterns, confluence,
signal, direction, confidence, reason, risks

signal must be exactly CALL, PUT, or NO TRADE.
direction must be UP, DOWN, or NEUTRAL.
"""


def _data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Vision model did not return valid JSON")
        obj = json.loads(text[start:end + 1])

    if not isinstance(obj, dict):
        raise ValueError("Vision response is not a JSON object")
    return obj


def _normalize_result(result: dict[str, Any], model: str) -> dict[str, Any]:
    normalized = {key: result.get(key) for key in REQUIRED_KEYS}
    if normalized["signal"] not in {"CALL", "PUT", "NO TRADE"}:
        normalized["signal"] = "NO TRADE"
    if normalized["direction"] not in {"UP", "DOWN", "NEUTRAL"}:
        normalized["direction"] = {
            "CALL": "UP", "PUT": "DOWN", "NO TRADE": "NEUTRAL"
        }[normalized["signal"]]
    try:
        normalized["confidence"] = max(0, min(100, int(normalized["confidence"] or 0)))
    except (TypeError, ValueError):
        normalized["confidence"] = 0
    normalized["model"] = model
    return normalized


async def analyze_chart_image(image_bytes: bytes, mime_type: str, api_key: str) -> dict[str, Any]:
    if not image_bytes:
        raise ValueError("Empty image")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")
    if not mime_type.startswith("image/"):
        raise ValueError("Unsupported image MIME type")

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this chart image and return the required JSON."},
                    {"type": "image_url", "image_url": {"url": _data_url(image_bytes, mime_type)}},
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 1400,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/mohmb142/Jjjjjjj",
        "X-Title": "Pocket OTC AI Analyzer",
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(OPENROUTER_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise ValueError("OpenRouter returned no choices")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict) and part.get("text")
        )
    if not str(content).strip():
        raise ValueError("OpenRouter returned empty Vision content")

    return _normalize_result(_parse_json(str(content)), model)
