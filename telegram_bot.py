import os
from datetime import datetime
from html import escape

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from indicators import analyze_candles
from openrouter import refine_with_openrouter
from pocket_data import PocketDataError, get_closed_candles, get_live_price
from signal_engine import generate_signal

load_dotenv()

PAIRS = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "USDCHF_otc",
    "AUDUSD_otc", "USDCAD_otc", "EURGBP_otc", "EURJPY_otc",
    "EURCHF_otc", "EURAUD_otc", "EURNZD_otc", "EURCAD_otc",
]

PAIR_LABELS = {
    "EURUSD_otc": "EUR/USD", "GBPUSD_otc": "GBP/USD", "USDJPY_otc": "USD/JPY",
    "USDCHF_otc": "USD/CHF", "AUDUSD_otc": "AUD/USD", "USDCAD_otc": "USD/CAD",
    "EURGBP_otc": "EUR/GBP", "EURJPY_otc": "EUR/JPY", "EURCHF_otc": "EUR/CHF",
    "EURAUD_otc": "EUR/AUD", "EURNZD_otc": "EUR/NZD", "EURCAD_otc": "EUR/CAD",
}

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()


def main_keyboard():
    rows = []
    for i in range(0, len(PAIRS), 2):
        rows.append([
            InlineKeyboardButton(PAIR_LABELS[PAIRS[i]], callback_data=f"pair:{PAIRS[i]}"),
            InlineKeyboardButton(PAIR_LABELS[PAIRS[i + 1]], callback_data=f"pair:{PAIRS[i + 1]}")
            if i + 1 < len(PAIRS) else InlineKeyboardButton("—", callback_data="noop"),
        ])
    rows += [[InlineKeyboardButton("📡 حالة النظام", callback_data="status")],
             [InlineKeyboardButton("ℹ️ حول النظام", callback_data="about")]]
    return InlineKeyboardMarkup(rows)


def home_text():
    return (
        "<b>📊 POCKET OTC AI ANALYZER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 المحرك: Google Colab\n"
        "📡 المصدر: OTC Live Data API (بدون SSID)\n"
        "💹 السعر: بث حي مباشر\n"
        "🧠 التحليل: مؤشرات فنية + اختياري OpenRouter\n\n"
        "اختر زوجًا لقراءة السعر والشموع المغلقة وتحليلها.\n\n"
        "<b>⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة.</b>"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(home_text(), parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


async def analyze_pair(pair: str):
    candles = await get_closed_candles(pair)
    analysis = analyze_candles(candles)
    live_price = await get_live_price(pair)
    analysis["live_price"] = live_price

    result = generate_signal(analysis)
    source = "LOCAL"
    if OPENROUTER_KEY:
        try:
            result = await refine_with_openrouter(result, analysis, OPENROUTER_KEY)
            source = "OPENROUTER"
        except Exception:
            source = "LOCAL (OpenRouter fallback)"
    return candles, analysis, result, source


def format_result(pair, analysis, result, source):
    signal = result.get("signal", "NO TRADE")
    icon = {"CALL": "🟢", "PUT": "🔴", "NO TRADE": "⚪"}.get(signal, "⚪")
    direction = result.get("direction", "NEUTRAL")
    confidence = result.get("confidence", 0)
    reason = escape(str(result.get("reason", "لا يوجد سبب متاح.")))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"<b>📊 {escape(PAIR_LABELS.get(pair, pair))} OTC</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💹 السعر المباشر: <code>{analysis['live_price']:.6f}</code>\n"
        f"🕯️ إغلاق آخر شمعة: <code>{analysis['price']:.6f}</code>\n\n"
        f"🎯 الإشارة: {icon} <b>{signal}</b>\n"
        f"🧭 الاتجاه: <b>{direction}</b>\n"
        f"📈 الثقة التحليلية: <b>{confidence}/100</b>\n"
        "⏱ مدة التحليل: <b>5 دقائق</b>\n\n"
        "<b>المؤشرات</b>\n"
        f"EMA 9: {analysis['ema9']:.6f}\n"
        f"EMA 21: {analysis['ema21']:.6f}\n"
        f"EMA 50: {analysis['ema50']:.6f}\n"
        f"RSI 14: {analysis['rsi14']:.2f}\n"
        f"ATR 14: {analysis['atr14']:.6f}\n"
        f"Support: {analysis['support']:.6f}\n"
        f"Resistance: {analysis['resistance']:.6f}\n"
        f"آخر 10 شموع: صعود {analysis['recent_up']} / هبوط {analysis['recent_down']}\n\n"
        f"🧠 السبب: {reason}\n\n"
        f"📡 المصدر: <b>{escape(source)}</b>\n"
        f"🕐 {now}\n\n"
        "<b>⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة.</b>"
    )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "noop":
        return
    if data == "status":
        text = (
            "<b>📡 حالة النظام</b>\n\n"
            "🟢 Telegram: متصل\n"
            "🟢 Google Colab: يعمل (هذه الجلسة)\n"
            "🟢 مصدر الأسعار: OTC Live Data API\n"
            "🟢 SSID: غير مطلوب\n"
            f"{'🟢' if OPENROUTER_KEY else '⚪'} OpenRouter: {'مفعّل' if OPENROUTER_KEY else 'اختياري/غير مفعّل'}\n\n"
            "⚠️ لا يتم تنفيذ الصفقات."
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())
        return
    if data == "about":
        await query.edit_message_text(
            "<b>ℹ️ عن Pocket OTC AI Analyzer</b>\n\n"
            "يقرأ أسعار وبيانات OTC من مصدر بيانات خارجي، بدون ربط حساب Pocket Option وبدون SSID.\n"
            "يحسب EMA/RSI/MACD/ATR والدعم والمقاومة وآخر 10 شموع.\n\n"
            "النتيجة تحليلية وليست ضمانًا للربح أو احتمالًا للنجاح، ولا توجد أي وظائف لفتح أو إغلاق الصفقات.",
            parse_mode=ParseMode.HTML, reply_markup=main_keyboard(),
        )
        return
    if not data.startswith("pair:"):
        return

    pair = data.split(":", 1)[1]
    if pair not in PAIRS:
        await query.edit_message_text("الزوج غير مدعوم.", reply_markup=main_keyboard())
        return

    await query.edit_message_text(
        f"⏳ جاري قراءة السعر والشموع الحقيقية لـ <b>{escape(PAIR_LABELS[pair])} OTC</b>...",
        parse_mode=ParseMode.HTML,
    )
    try:
        _, analysis, result, source = await analyze_pair(pair)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 إعادة التحليل", callback_data=f"pair:{pair}")],
            [InlineKeyboardButton("⬅️ الأزواج", callback_data="home")],
        ])
        await query.edit_message_text(format_result(pair, analysis, result, source), parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except PocketDataError as e:
        await query.edit_message_text(
            f"❌ <b>تعذر الحصول على بيانات OTC حقيقية</b>\n\n<code>{escape(str(e))}</code>\n\nلم يتم استخدام بيانات عشوائية أو تجريبية.",
            parse_mode=ParseMode.HTML, reply_markup=main_keyboard(),
        )
    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحليل:\n<code>{escape(str(e))}</code>", parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


async def home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(home_text(), parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


def run():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(home_callback, pattern=r"^home$"))
    app.add_handler(CallbackQueryHandler(callbacks))
    print("Telegram bot is running. READ-ONLY mode: no trade execution.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run()
