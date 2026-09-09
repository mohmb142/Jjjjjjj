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
from openrouter import refine_with_openrouter
from pocket_data import PocketDataError, get_closed_candles
from signal_engine import generate_signal

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Pocket OTC AI Analyzer",
    version="2.1.0",
    description="READ-ONLY chart analysis. No trade execution.",
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

PAIRS = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "USDCHF_otc",
    "AUDUSD_otc", "USDCAD_otc", "EURGBP_otc", "EURJPY_otc",
    "EURCHF_otc", "EURAUD_otc", "EURNZD_otc", "EURCAD_otc",
]
MAX_IMAGE_BYTES = 12 * 1024 * 1024


def _api_key(query_key: Optional[str], header_key: Optional[str]) -> str:
    # Header is preferred so secrets do not appear in URLs/browser history.
    return (header_key or query_key or os.getenv("OPENROUTER_API_KEY") or "").strip()


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "READ-ONLY", "vision_model": os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")}


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
        result = await analyze_chart_image(data, content_type, key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"فشل الاتصال بخدمة Vision: {exc}") from exc

    result.update(
        source="VISION",
        analysis_time=datetime.now(timezone.utc).isoformat(),
        duration_minutes=5,
        disclaimer="تحليل للصورة فقط — لا يتم تنفيذ أي صفقة.",
    )
    return result


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

    if len(candles) < 60:
        raise HTTPException(status_code=503, detail=f"Insufficient real candles: {len(candles)}")

    analysis = analyze_candles(candles)
    result = generate_signal(analysis)
    source = "LOCAL"
    key = _api_key(openrouter_key, x_openrouter_key)

    if key:
        try:
            result = await refine_with_openrouter(result, analysis, key)
            source = "OPENROUTER"
        except Exception:
            # Keep the deterministic local result if the optional AI refinement fails.
            source = "LOCAL"

    result.update(
        source=source,
        pair=pair,
        analysis_time=datetime.now(timezone.utc).isoformat(),
        duration_minutes=5,
        disclaimer="تحليل فقط — لا يتم تنفيذ أي صفقة.",
    )
    return result
