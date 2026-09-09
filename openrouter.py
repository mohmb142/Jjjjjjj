import json
import os
from typing import Any

import httpx

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("OpenRouter did not return valid JSON")
        obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("OpenRouter response is not a JSON object")
    return obj


async def refine_with_openrouter(result: dict[str, Any], analysis: dict[str, Any], api_key: str) -> dict[str, Any]:
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    prompt = (
        "Review this READ-ONLY technical analysis. Do not execute or promise a trade. "
        "Return JSON with only signal, direction, confidence, and reason. "
        "signal must be CALL, PUT, or NO TRADE; direction UP, DOWN, or NEUTRAL; "
        "confidence is analytical confidence 0-100. If evidence conflicts, use NO TRADE.\n"
        f"Local result: {json.dumps(result, ensure_ascii=False)}\n"
        f"Indicators: {json.dumps(analysis, ensure_ascii=False)}"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 500,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/mohmb142/Jjjjjjj",
        "X-Title": "Pocket OTC AI Analyzer",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise ValueError("OpenRouter returned no choices")
    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    obj = _parse_json(str(content))

    signal = obj.get("signal")
    if signal not in {"CALL", "PUT", "NO TRADE"}:
        raise ValueError("Invalid OpenRouter signal")
    direction = obj.get("direction")
    if direction not in {"UP", "DOWN", "NEUTRAL"}:
        direction = {"CALL": "UP", "PUT": "DOWN", "NO TRADE": "NEUTRAL"}[signal]
    try:
        confidence = max(0, min(100, int(obj.get("confidence", 0))))
    except (TypeError, ValueError):
        confidence = 0

    return {
        "signal": signal,
        "direction": direction,
        "confidence": confidence,
        "reason": str(obj.get("reason") or "لا يوجد سبب إضافي."),
    }
