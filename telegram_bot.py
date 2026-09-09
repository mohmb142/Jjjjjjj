import os
from datetime import datetime, timezone
from html import escape
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from image_analyzer import analyze_chart_image
from indicators import analyze_candles
from pocket_data import PocketDataError, get_closed_candles
from historical_pattern import analyze_historical_pattern

PAIRS={"EURUSD_OTC":"EURUSD_otc","GBPUSD_OTC":"GBPUSD_otc","USDJPY_OTC":"USDJPY_otc","USDCHF_OTC":"USDCHF_otc","AUDUSD_OTC":"AUDUSD_otc","USDCAD_OTC":"USDCAD_otc","EURGBP_OTC":"EURGBP_otc","EURJPY_OTC":"EURJPY_otc","EURCHF_OTC":"EURCHF_otc","EURAUD_OTC":"EURAUD_otc","EURNZD_OTC":"EURNZD_otc","EURCAD_OTC":"EURCAD_otc"}

def format_result(r):
    s=str(r.get("signal","NO TRADE")); icon="🟢" if s=="CALL" else "🔴" if s=="PUT" else "🟡"
    pair=str(r.get("pair", "")); pl=f"📌 الزوج: <b>{escape(pair)}</b>\n" if pair else ""
    matches=r.get("matches")
    stats=f"\n🔎 الحالات المشابهة: <b>{escape(str(matches))}</b>" if matches is not None else ""
    wr=r.get("win_rate")
    if wr is not None: stats+=f"\n📈 نتيجة الحالات: <b>{escape(str(wr))}%</b>"
    return f"{icon} <b>الإشارة: {escape(s)}</b>\n{pl}📊 الثقة الإحصائية: <b>{escape(str(r.get('confidence',0)))}%</b>\n📈 الاتجاه: {escape(str(r.get('direction','NEUTRAL')))}\n⏱️ الأفق: <b>1 دقيقة</b>{stats}\n\n🧠 <b>السبب:</b>\n{escape(str(r.get('reason','غير متوفر')))}\n\n⚠️ تحليل إحصائي فقط — لا يتم تنفيذ أي صفقة ولا توجد ضمانات للنتيجة."

async def start(update,context):
    if update.message: await update.message.reply_text("🤖 <b>Pocket OTC AI Analyzer</b>\n\nأرسل صورة شارت واضحة. سيستخدم البوت الآن مطابقة الأنماط التاريخية بدلاً من الاعتماد على المؤشرات وحدها.\n\nلا ينفذ صفقات.",parse_mode="HTML")

async def help_cmd(update,context):
    if update.message: await update.message.reply_text("أرسل صورة الشارت مباشرة، واجعل الزوج والفريم ظاهرين بوضوح. المحرك يبحث عن حالات تاريخية مشابهة، وإذا لم يجد عينة كافية يعيد NO TRADE.")

async def photo(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:return
    key=os.getenv("OPENROUTER_API_KEY","").strip()
    if not key: await update.message.reply_text("❌ مفتاح OpenRouter غير مضبوط."); return
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        f=await context.bot.get_file(update.message.photo[-1].file_id); data=await f.download_as_bytearray()
        vision=await analyze_chart_image(bytes(data),"image/jpeg",key); pair=str(vision.get("asset") or "").strip()
        if pair not in PAIRS.values():
            vision["reason"]="لم أتعرف على زوج OTC مدعوم من الصورة؛ أظهر اسم الزوج بوضوح."
            await update.message.reply_text(format_result(vision),parse_mode="HTML"); return
        try:
            candles=await get_closed_candles(pair)
            # Pattern matching is the primary decision engine. Indicators are retained
            # only as contextual data and are not allowed to override historical evidence.
            pattern=analyze_historical_pattern(candles, pair)
            pattern.update(pair=pair, source="HISTORICAL_PATTERN_MATCHING", analysis_time=datetime.now(timezone.utc).isoformat())
            await update.message.reply_text(format_result(pattern),parse_mode="HTML")
        except PocketDataError as exc:
            await update.message.reply_text(format_result({"signal":"NO TRADE","confidence":0,"reason":f"تعذر جلب شموع OTC للتحقق التاريخي: {exc}","pair":pair}),parse_mode="HTML")
    except Exception as exc:
        await update.message.reply_text("❌ فشل التحليل: "+escape(str(exc)),parse_mode="HTML")

def main():
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    if not token: raise RuntimeError("TELEGRAM_BOT_TOKEN غير مضبوط")
    app=Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",start)); app.add_handler(CommandHandler("help",help_cmd)); app.add_handler(MessageHandler(filters.PHOTO,photo))
    print("🤖 Telegram Bot يعمل الآن — Historical Pattern Matching فعال.")
    app.run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates=False)

if __name__=="__main__": main()
