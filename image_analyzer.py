import base64
import json
import os
from typing import Any

import httpx

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"

SYSTEM_PROMPT = """
You are an expert chart-vision and technical-analysis engine.
Analyze ONLY the chart image supplied by the user. Do not invent unreadable values.
This application is READ-ONLY: never place, open, close, or automate trades.

Perform a deep but fast visual analysis:
1) Identify symbol/asset and timeframe if visible; otherwise say unknown.
2) Inspect the latest 15-30 visible candles and market structure: trend, HH/HL/LH/LL,
   momentum, volatility, breakouts, pullbacks and rejection candles.
3) Read visible indicators such as EMA 9/21/50, RSI, MACD, ATR, support/resistance.
   Only report numerical values when they are actually readable.
4) Identify important support/resistance and nearby reaction zones.
5) Check candlestick patterns and confluence.
6) Look for contradictions and image-quality limitations.
7) Produce CALL, PUT, or NO TRADE. If evidence is weak, contradictory, cropped,
   blurry, or indicators cannot be read reliably, choose NO TRADE.
8) confidence is ANALYTICAL CONFIDENCE (0-100), NOT probability of profit.
9) The requested horizon is 5 minutes, but do not claim certainty about future price.

Return STRICT JSON only, with exactly these keys:
asset, timeframe, image_quality, trend, structure, momentum, volatility,
ema, rsi, macd, support, resistance, candle_patterns, confluence,
signal, direction, confidence, reason, risks
"""


def _data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Vision model did not return JSON")
    return json.loads(text[start:end + 1])


async def analyze_chart_image(image_bytes: bytes, mime_type: str, api_key: str) -> dict[str, Any]:
    if not image_bytes:
        raise ValueError("Empty image")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this trading chart image deeply and return the required JSON."},
                    {"type": "image_url", "image_url": {"url": _data_url(image_bytes, mime_type)}},
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 1200,
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
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

    result = _parse_json(str(content))
    signal = result.get("signal")
    if signal not in {"CALL", "PUT", "NO TRADE"}:
        result["signal"] = "NO TRADE"
    try:
        result["confidence"] = max(0, min(100, int(result.get("confidence", 0))))
    except (TypeError, ValueError):
        result["confidence"] = 0
    result["model"] = model
    return result
