import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pocket_data import PocketDataError, get_closed_candles
from indicators import analyze_candles
from signal_engine import generate_signal
from openrouter import refine_with_openrouter
from image_analyzer import analyze_chart_image

load_dotenv()
app = FastAPI(title="Pocket OTC AI Image Analyzer", version="2.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

PAIRS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "USDCHF_otc", "AUDUSD_otc", "USDCAD_otc", "EURGBP_otc", "EURJPY_otc", "EURCHF_otc", "EURAUD_otc", "EURNZD_otc", "EURCAD_otc"]

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/api/pairs")
async def pairs():
    return {"pairs": PAIRS}

@app.post("/api/analyze-image")
async def analyze_image(file: UploadFile = File(...), openrouter_key: Optional[str] = None):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "يجب رفع صورة شارت")
    data = await file.read()
    if not data:
        raise HTTPException(400, "الصورة فارغة")
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "حجم الصورة أكبر من 12MB")
    key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise HTTPException(503, "OPENROUTER_API_KEY غير مفعّل")
    try:
        result = await analyze_chart_image(data, file.content_type, key)
        result.update(source="VISION", analysis_time=datetime.now(timezone.utc).isoformat(), duration_minutes=5, disclaimer="تحليل للصورة فقط — لا يتم تنفيذ أي صفقة.")
        return result
    except Exception as exc:
        raise HTTPException(502, f"فشل تحليل الصورة: {exc}") from exc

@app.get("/api/analyze")
async def analyze(pair: str, openrouter_key: Optional[str] = None):
    if pair not in PAIRS:
        raise HTTPException(400, "Unsupported pair")
    try:
        candles = await get_closed_candles(pair)
    except PocketDataError as e:
        raise HTTPException(503, str(e))
    if len(candles) < 60:
        raise HTTPException(503, f"Insufficient real candles: {len(candles)}")
    analysis = analyze_candles(candles)
    result = generate_signal(analysis)
    source = "LOCAL"
    key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
    if key:
        try:
            result = await refine_with_openrouter(result, analysis, key)
            source = "OPENROUTER"
        except Exception:
            source = "LOCAL"
    result.update(source=source, pair=pair, analysis_time=datetime.now(timezone.utc).isoformat(), duration_minutes=5, disclaimer="تحليل فقط — لا يتم تنفيذ أي صفقة.")
    return result
