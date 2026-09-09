from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from image_analyzer import analyze_chart_image
from indicators import analyze_candles
from openrouter import refine_combined_with_openrouter, refine_with_openrouter
from pocket_data import PocketDataError, get_closed_candles
from signal_engine import generate_signal

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Pocket OTC AI Analyzer",
    version="3.0.0",
    description="READ-ONLY chart analysis with visual + closed-candle data fusion.",
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

PAIRS = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "USDCHF_otc",
    "AUDUSD_otc", "USDCAD_otc", "EURGBP_otc", "EURJPY_otc",
    "EURCHF_otc", "EURAUD_otc", "EURNZD_otc", "EURCAD_otc",
]
MAX_IMAGE_BYTES = 12 * 1024 * 1024


def _api_key(query_key: Optional[str], header_key: Optional[str]) -> str:
    return (header_key or query_key or os.getenv("OPENROUTER_API_KEY") or "").strip()


def _market_source(candles: list) -> tuple[dict, dict]:
    if len(candles) < 60:
        raise HTTPException(status_code=503, detail=f"Insufficient real candles: {len(candles)}")
    analysis = analyze_candles(candles)
    result = generate_signal(analysis)
    return analysis, result


def _conflict_guard(vision: dict, market: dict) -> dict:
    """Deterministic safety gate before the LLM reviewer."""
    vs = vision.get("signal")
    ms = market.get("signal")
    vc = int(vision.get("confidence") or 0)
    mc = int(market.get("confidence") or 0)
    if vs in {"CALL", "PUT"} and ms in {"CALL", "PUT"} and vs != ms:
        return {"signal": "NO TRADE", "direction": "NEUTRAL", "confidence": min(vc, mc, 49),
                "reason": "تعارض مباشر بين التحليل البصري والبيانات الرقمية."}
    if vs == "NO TRADE" or ms == "NO TRADE":
        return {"signal": "NO TRADE", "direction": "NEUTRAL", "confidence": min(vc, mc, 69),
                "reason": "أحد المصدرين لم يؤكد وجود فرصة تداول منضبطة."}
    if vc < 70 or mc < 70:
        return {"signal": "NO TRADE", "direction": "NEUTRAL", "confidence": min(vc, mc),
                "reason": "ثقة أحد المصدرين أقل من الحد الأدنى 70."}
    if vs == ms:
        return {"signal": vs, "direction": "UP" if vs == "CALL" else "DOWN",
                "confidence": min(vc, mc), "reason": "المصدران متوافقان."}
    return {"signal": "NO TRADE", "direction": "NEUTRAL", "confidence": 0,
            "reason": "تعذر التحقق من توافق المصدرين."}


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "READ-ONLY", "version": "3.0.0",
            "vision_model": os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")}


@app.get("/api/pairs")
async def pairs():
    return {"pairs": PAIRS}


@app.post("/api/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    openrouter_key: Optional[str] = None,
    x_openrouter_key: Optional[str] = Header(default=None, alias="X-OpenRouter-Key"),
):
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="يجب رفع صورة شارت بصيغة صورة.")
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="الصورة فارغة.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="حجم الصورة أكبر من 12MB.")
    key = _api_key(openrouter_key, x_openrouter_key)
    if not key:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY غير مفعّل.")
    try:
        vision = await analyze_chart_image(data, content_type, key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"فشل تحليل Vision: {exc}") from exc

    # If the screenshot identifies an OTC pair, use it; otherwise image-only remains available.
    pair = str(vision.get("asset") or "").strip()
    pair = pair if pair in PAIRS else None
    if not pair:
        vision.update(source="VISION", fusion="IMAGE_ONLY", analysis_time=datetime.now(timezone.utc).isoformat(),
                      duration_minutes=5, disclaimer="تحليل للصورة فقط — لا يتم تنفيذ أي صفقة.")
        return vision

    try:
        candles = await get_closed_candles(pair)
        analysis, market = _market_source(candles)
        guard = _conflict_guard(vision, market)
        fused = await refine_combined_with_openrouter(vision, market, analysis, key)
        # Never allow the final LLM to override a hard disagreement gate.
        if guard["signal"] == "NO TRADE":
            fused = guard
        fused.update({
            "pair": pair, "source": "FUSED", "fusion": "VISION+MARKET_DATA",
            "vision_signal": vision.get("signal"), "vision_confidence": vision.get("confidence"),
            "market_signal": market.get("signal"), "market_confidence": market.get("confidence"),
            "analysis": analysis, "analysis_time": datetime.now(timezone.utc).isoformat(),
            "duration_minutes": 5,
            "disclaimer": "تحليل فقط — لا يتم تنفيذ أي صفقة.",
        })
        return fused
    except PocketDataError:
        vision.update(source="VISION", fusion="IMAGE_ONLY", pair=pair,
                      analysis_time=datetime.now(timezone.utc).isoformat(), duration_minutes=5,
                      disclaimer="تعذر جلب بيانات الشموع؛ تم الاحتفاظ بتحليل الصورة فقط.")
        return vision
    except Exception:
        # Never hide a valid visual result if the optional data layer fails.
        vision.update(source="VISION", fusion="IMAGE_ONLY", pair=pair,
                      analysis_time=datetime.now(timezone.utc).isoformat(), duration_minutes=5,
                      disclaimer="تعذر دمج بيانات السوق؛ تم الاحتفاظ بتحليل الصورة فقط.")
        return vision


@app.get("/api/analyze")
async def analyze(
    pair: str,
    openrouter_key: Optional[str] = None,
    x_openrouter_key: Optional[str] = Header(default=None, alias="X-OpenRouter-Key"),
):
    if pair not in PAIRS:
        raise HTTPException(status_code=400, detail="Unsupported pair")
    try:
        candles = await get_closed_candles(pair)
    except PocketDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    analysis, result = _market_source(candles)
    source = "LOCAL"
    key = _api_key(openrouter_key, x_openrouter_key)
    if key:
        try:
            result = await refine_with_openrouter(result, analysis, key)
            source = "OPENROUTER"
        except Exception:
            source = "LOCAL"
    result.update(source=source, pair=pair, analysis_time=datetime.now(timezone.utc).isoformat(),
                  duration_minutes=5, disclaimer="تحليل فقط — لا يتم تنفيذ أي صفقة.")
    return result
