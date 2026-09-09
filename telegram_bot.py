import os
from datetime import datetime, timezone
from html import escape
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from image_analyzer import analyze_chart_image
from indicators import analyze_candles
from pocket_data import PocketDataError, get_closed_candles
from signal_engine import generate_signal
from openrouter import refine_combined_with_openrouter

PAIRS={"EURUSD_OTC":"EURUSD_otc","GBPUSD_OTC":"GBPUSD_otc","USDJPY_OTC":"USDJPY_otc","USDCHF_OTC":"USDCHF_otc","AUDUSD_OTC":"AUDUSD_otc","USDCAD_OTC":"USDCAD_otc","EURGBP_OTC":"EURGBP_otc","EURJPY_OTC":"EURJPY_otc","EURCHF_OTC":"EURCHF_otc","EURAUD_OTC":"EURAUD_otc","EURNZD_OTC":"EURNZD_otc","EURCAD_OTC":"EURCAD_otc"}

def guard(v,m):
    vs,ms=v.get("signal"),m.get("signal"); vc,mc=int(v.get("confidence") or 0),int(m.get("confidence") or 0)
    if vs in {"CALL","PUT"} and ms in {"CALL","PUT"} and vs!=ms:return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":min(vc,mc,49),"reason":"تعارض مباشر بين التحليل البصري والبيانات الرقمية."}
    if vs=="NO TRADE" or ms=="NO TRADE":return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":min(vc,mc,69),"reason":"أحد المصدرين لم يؤكد فرصة تداول منضبطة."}
    if vc<70 or mc<70:return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":min(vc,mc),"reason":"ثقة أحد المصدرين أقل من 70%."}
    if vs==ms:return {"signal":vs,"direction":"UP" if vs=="CALL" else "DOWN","confidence":min(vc,mc),"reason":"توافق التحليل البصري والبيانات الرقمية."}
    return {"signal":"NO TRADE","direction":"NEUTRAL","confidence":0,"reason":"تعذر التحقق من التوافق."}

def format_result(r):
    s=str(r.get("signal","NO TRADE")); icon="🟢" if s=="CALL" else "🔴" if s=="PUT" else "🟡"
    pair=str(r.get("pair", "")); pl=f"📌 الزوج: <b>{escape(pair)}</b>\n" if pair else ""
    return f"{icon} <b>الإشارة: {escape(s)}</b>\n{pl}📊 الثقة: <b>{escape(str(r.get('confidence',0)))}%</b>\n📈 الاتجاه: {escape(str(r.get('direction','NEUTRAL')))}\n⏱️ الأفق: <b>1 دقيقة</b>\n\n🧠 <b>السبب:</b>\n{escape(str(r.get('reason','غير متوفر')))}\n\n⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة."

async def start(update,context):
    if update.message: await update.message.reply_text("🤖 <b>Pocket OTC AI Analyzer</b>\n\nأرسل صورة شارت واضحة وسأحللها.\n\nهذا البوت للقراءة والتحليل فقط ولا ينفذ صفقات.",parse_mode="HTML")

async def help_cmd(update,context):
    if update.message: await update.message.reply_text("أرسل صورة الشارت مباشرة، واجعل الزوج والفريم ظاهرين بوضوح.")

async def photo(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:return
    key=os.getenv("OPENROUTER_API_KEY","").strip()
    if not key: await update.message.reply_text("❌ مفتاح OpenRouter غير مضبوط."); return
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        f=await context.bot.get_file(update.message.photo[-1].file_id); data=await f.download_as_bytearray()
        vision=await analyze_chart_image(bytes(data),"image/jpeg",key); pair=str(vision.get("asset") or "").strip()
        if pair not in PAIRS.values(): await update.message.reply_text(format_result(vision),parse_mode="HTML"); return
        try:
            candles=await get_closed_candles(pair); ma=analyze_candles(candles); market=generate_signal(ma); final=guard(vision,market)
            if final["signal"]!="NO TRADE":
                try: final=await refine_combined_with_openrouter(vision,market,ma,key)
                except Exception: pass
            g=guard(vision,market)
            if g["signal"]=="NO TRADE": final=g
            final.update(pair=pair,source="TELEGRAM_FUSED",analysis_time=datetime.now(timezone.utc).isoformat())
            await update.message.reply_text(format_result(final),parse_mode="HTML")
        except PocketDataError:
            await update.message.reply_text(format_result(vision),parse_mode="HTML")
    except Exception as exc:
        await update.message.reply_text("❌ فشل التحليل: "+escape(str(exc)),parse_mode="HTML")

def main():
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    if not token: raise RuntimeError("TELEGRAM_BOT_TOKEN غير مضبوط")
    app=Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",start)); app.add_handler(CommandHandler("help",help_cmd)); app.add_handler(MessageHandler(filters.PHOTO,photo))
    print("🤖 Telegram Bot يعمل الآن — أرسل /start ثم صورة الشارت.")
    app.run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates=False)

if __name__=="__main__": main()
