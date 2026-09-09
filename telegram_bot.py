import os
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from image_analyzer import analyze_chart_image
from indicators import analyze_candles
from pocket_data import PocketDataError, get_closed_candles
from signal_engine import generate_signal
from openrouter import refine_combined_with_openrouter

PAIRS = {
    "EURUSD_OTC": "EURUSD_otc", "GBPUSD_OTC": "GBPUSD_otc", "USDJPY_OTC": "USDJPY_otc",
    "USDCHF_OTC": "USDCHF_otc", "AUDUSD_OTC": "AUDUSD_otc", "USDCAD_OTC": "USDCAD_otc",
    "EURGBP_OTC": "EURGBP_otc", "EURJPY_OTC": "EURJPY_otc", "EURCHF_OTC": "EURCHF_otc",
    "EURAUD_OTC": "EURAUD_otc", "EURNZD_OTC": "EURNZD_otc", "EURCAD_OTC": "EURCAD_otc",
}


def guard(vision, market):
    vs, ms = vision.get("signal"), market.get("signal")
    vc, mc = int(vision.get("confidence") or 0), int(market.get("confidence") or 0)
    if vs in {"CALL", "PUT"} and ms in {"CALL", "PUT"} and vs != ms:
        return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":min(vc, mc, 49),"reason":"تعارض مباشر بين التحليل البصري والبيانات الرقمية."}
    if vs == "NO TRADE" or ms == "NO TRADE":
        return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":min(vc, mc, 69),"reason":"أحد المصدرين لم يؤكد فرصة تداول منضبطة."}
    if vc < 70 or mc < 70:
        return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":min(vc, mc),"reason":"ثقة أحد المصدرين أقل من 70%."}
    if vs == ms:
        return {"signal":vs,"direction":"UP" if vs == "CALL" else "DOWN","confidence":min(vc, mc),"reason":"توافق التحليل البصري والبيانات الرقمية."}
    return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":0,"reason":"تعذر التحقق من التوافق."}


def format_result(result):
    signal = result.get("signal", "NO TRADE")
    icon = "🟢" if signal == "CALL" else "🔴" if signal == "PUT" else "🟡"
    return (
        f"{icon} **الإشارة: {signal}**\n"
        f"📊 الثقة: **{result.get('confidence', 0)}%**\n"
        f"📈 الاتجاه: {result.get('direction', 'NEUTRAL')}\n"
        f"⏱️ الأفق: **1 دقيقة**\n\n"
        f"🧠 السبب:\n{result.get('reason', 'غير متوفر')}\n\n"
        f"⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Pocket OTC AI Analyzer**\n\nأرسل صورة شارت واضحة وسأحللها.\n\n"
        "يدعم التحليل البصري + بيانات الشموع المغلقة، مع NO TRADE عند التعارض.\n"
        "\nهذا البوت للقراءة والتحليل فقط ولا ينفذ صفقات.", parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل صورة الشارت مباشرة. للحصول على أفضل نتيجة اجعل الزوج والفريم ظاهرين بوضوح.")


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        await update.message.reply_text("❌ OPENROUTER_API_KEY غير مضبوط في بيئة التشغيل.")
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        tg_photo = update.message.photo[-1]
        tg_file = await context.bot.get_file(tg_photo.file_id)
        data = await tg_file.download_as_bytearray()
        vision = await analyze_chart_image(bytes(data), "image/jpeg", key)
        pair = str(vision.get("asset") or "").strip()
        if pair not in PAIRS.values():
            await update.message.reply_text(format_result(vision), parse_mode="Markdown")
            return
        try:
            candles = await get_closed_candles(pair)
            market_analysis = analyze_candles(candles)
            market = generate_signal(market_analysis)
            fused = guard(vision, market)
            if fused["signal"] != "NO TRADE":
                try:
                    fused = await refine_combined_with_openrouter(vision, market, market_analysis, key)
                except Exception:
                    pass
            if guard(vision, market)["signal"] == "NO TRADE":
                fused = guard(vision, market)
            fused.update(pair=pair, source="TELEGRAM_FUSED", analysis_time=datetime.now(timezone.utc).isoformat())
            await update.message.reply_text(format_result(fused), parse_mode="Markdown")
        except PocketDataError:
            await update.message.reply_text(format_result(vision), parse_mode="Markdown")
    except Exception as exc:
        await update.message.reply_text(f"❌ فشل التحليل: {exc}")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN غير مضبوط")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    print("🤖 Telegram Bot يعمل الآن... أرسل صورة شارت إلى البوت.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
