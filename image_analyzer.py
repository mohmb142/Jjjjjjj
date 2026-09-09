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
أنت محرك تحليل فني بصري احترافي. حلل صورة الشارت فقط ولا تخترع أي قيمة غير واضحة.
يجب أن تكون جميع القيم النصية والتفسيرات والسبب والمخاطر باللغة العربية، مع إبقاء أسماء
المؤشرات والاختصارات والأصل مثل EMA وRSI وMACD وCALL وPUT وNO TRADE كما هي.

هذا النظام READ-ONLY: ممنوع تنفيذ أو فتح أو إغلاق أي صفقة.
الأفق المطلوب 5 دقائق. الثقة درجة جودة تحليلية من 0 إلى 100 وليست احتمال ربح.

قواعد صارمة لاتخاذ القرار:
1) افحص الاتجاه وبنية السوق والزخم والشموع والدعم والمقاومة والمؤشرات الظاهرة.
2) لا تعط CALL أو PUT لمجرد أن الاتجاه العام صاعد/هابط.
3) إذا كان السعر قريباً جداً من مقاومة مع ضعف زخم صاعد، فاعتبر ذلك تعارضاً قوياً وقدّم NO TRADE.
4) إذا كان السعر قريباً جداً من دعم مع ضعف زخم هابط، فاعتبر ذلك تعارضاً قوياً وقدّم NO TRADE.
5) إذا تعارضت إشارتان أو أكثر من العوامل الرئيسية، خفّض الثقة وفضّل NO TRADE.
6) إذا كانت الصورة ضبابية أو مقصوصة أو المؤشرات غير قابلة للقراءة أو لا توجد أدلة كافية، استخدم NO TRADE.
7) لا تعتبر 60-69 ثقة كافية لإشارة تداول: عند هذه الدرجة استخدم NO TRADE إلا إذا كانت الأدلة قوية جداً ومتوافقة.
8) 70-79 يمكن أن تكون إشارة، و80-100 إشارة قوية، لكن لا تدّعِ اليقين أو الربح المضمون.
9) حاول دائماً ذكر ما قد يجعل الإشارة خاطئة في risks.

Return JSON only. Use exactly these keys:
asset, timeframe, image_quality, trend, structure, momentum, volatility,
ema, rsi, macd, support, resistance, candle_patterns, confluence,
signal, direction, confidence, reason, risks

signal must be exactly CALL, PUT, or NO TRADE.
direction must be UP, DOWN, or NEUTRAL.
confidence must be an integer from 0 to 100.
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
    # Analytical confidence below 70 is intentionally filtered from actionable signals.
    if signal in {"CALL", "PUT"} and confidence < 70:
        signal = "NO TRADE"
    normalized["signal"] = signal
    normalized["direction"] = (
        "UP" if signal == "CALL" else "DOWN" if signal == "PUT" else "NEUTRAL"
    )
    normalized["confidence"] = confidence
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
                {"type": "text", "text": "حلل هذه الصورة وأعد JSON بالمفاتيح المطلوبة. اكتب الشرح كله بالعربية."},
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
