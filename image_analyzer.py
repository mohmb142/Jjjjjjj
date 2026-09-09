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
أنت محرك تحليل فني بصري محافظ جداً لشارت Pocket Option OTC.
الهدف هو توقع حركة الشمعة/الدقيقة التالية فقط، وليس توقع 5 دقائق.
لا تخترع أي قيمة غير واضحة في الصورة.

اكتب التفسير بالعربية، مع إبقاء EMA وRSI وMACD وCALL وPUT وNO TRADE كما هي.
النظام READ-ONLY: ممنوع تنفيذ أو فتح أو إغلاق أي صفقة.

قواعد 1 دقيقة الصارمة:
1) لا تدخل بناءً على الاتجاه العام وحده. يجب اجتماع بنية السوق + زخم قصير الأجل + شموع/سلوك سعري واضح.
2) افحص آخر الشموع أولاً، ثم EMA وMACD وRSI، ثم الدعم والمقاومة.
3) CALL فقط عندما يكون الزخم الصاعد الحالي واضحاً، وEMA 9/21 داعماً، وMACD متوافقاً، ولا يوجد رفض هابط واضح أو مقاومة قريبة جداً.
4) PUT فقط عندما يكون الزخم الهابط الحالي واضحاً، وEMA 9/21 داعماً، وMACD متوافقاً، ولا يوجد رفض صاعد واضح أو دعم قريب جداً.
5) إذا كان السعر يختبر مقاومة قريبة بعد صعود، لا تطارد CALL؛ ابحث عن رفض أو NO TRADE.
6) إذا كان السعر يختبر دعماً قريباً بعد هبوط، لا تطارد PUT؛ ابحث عن ارتداد أو NO TRADE.
7) RSI فوق 70 أو تحت 30 ليس إشارة دخول تلقائية؛ اعتبره خطر انعكاس/تشبع حتى يظهر تأكيد سعري.
8) إذا تعارض عاملان رئيسيان أو كانت الشموع متذبذبة، استخدم NO TRADE.
9) إذا كانت الصورة ضبابية أو المؤشرات غير قابلة للقراءة، استخدم NO TRADE.
10) لأفق دقيقة واحدة، لا تعط CALL/PUT إلا عند ثقة تحليلية 75 أو أكثر. الثقة ليست احتمال ربح ولا ضماناً.
11) إذا لم توجد أفضلية واضحة للدقيقة التالية، NO TRADE أفضل من إشارة ضعيفة.
12) اذكر في risks السبب الأقوى الذي قد يجعل التوقع خاطئاً.

Return JSON only. Use exactly these keys:
asset, timeframe, image_quality, trend, structure, momentum, volatility,
ema, rsi, macd, support, resistance, candle_patterns, confluence,
signal, direction, confidence, reason, risks

signal must be exactly CALL, PUT, or NO TRADE.
direction must be UP, DOWN, or NEUTRAL.
confidence must be an integer from 0 to 100.
timeframe must describe the chart timeframe if visible; the forecast horizon is 1 minute.
"""


def _data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
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
    signal = normalized["signal"]
    if signal not in {"CALL", "PUT", "NO TRADE"}:
        signal = "NO TRADE"
    try:
        confidence = max(0, min(100, int(normalized["confidence"] or 0)))
    except (TypeError, ValueError):
        confidence = 0
    if signal in {"CALL", "PUT"} and confidence < 75:
        signal = "NO TRADE"
    normalized["signal"] = signal
    normalized["direction"] = (
        "UP" if signal == "CALL" else "DOWN" if signal == "PUT" else "NEUTRAL"
    )
    normalized["confidence"] = confidence
    normalized["forecast_horizon_minutes"] = 1
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
            {"role": "user", "content": [
                {"type": "text", "text": "حلل الصورة للدقيقة التالية فقط. لا تعط إشارة إلا إذا كان هناك توافق قوي؛ وإلا NO TRADE. أعد JSON فقط."},
                {"type": "image_url", "image_url": {"url": _data_url(image_bytes, mime_type)}},
            ]},
        ],
        "temperature": 0,
        "max_tokens": 1600,
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
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict) and part.get("text"))
    if not str(content).strip():
        raise ValueError("OpenRouter returned empty Vision content")
    return _normalize_result(_parse_json(str(content)), model)
