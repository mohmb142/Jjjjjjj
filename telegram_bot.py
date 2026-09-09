import os
from datetime import datetime
from html import escape

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from image_analyzer import analyze_chart_image

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 تحليل صورة شارت", callback_data="help_image")],
        [InlineKeyboardButton("📡 حالة النظام", callback_data="status")],
        [InlineKeyboardButton("ℹ️ حول النظام", callback_data="about")],
    ])


def home_text():
    return (
        "<b>📊 POCKET OTC AI IMAGE ANALYZER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🧠 تحليل بصري عميق للشارت\n"
        "⚡ تحليل سريع عبر OpenRouter Vision\n"
        "📷 ارفع صورة الشارت مباشرة\n\n"
        "سيتم فحص الاتجاه، بنية السعر، الشموع، الدعم والمقاومة، والمؤشرات الظاهرة مثل EMA وRSI وMACD.\n\n"
        "<b>⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة.</b>"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(home_text(), parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


async def help_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📷 <b>أرسل الآن صورة الشارت</b>\n\n"
        "يفضل أن تكون الصورة واضحة وتحتوي على أكبر قدر ممكن من الشموع والمؤشرات.\n\n"
        "⚠️ لا ترسل بيانات حسابك أو أي معلومات حساسة داخل الصورة.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard(),
    )


def _fmt(value, default="غير واضح"):
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return str(value)
    return escape(str(value))


def format_analysis(result):
    signal = result.get("signal", "NO TRADE")
    icon = {"CALL": "🟢", "PUT": "🔴", "NO TRADE": "⚪"}.get(signal, "⚪")
    confidence = result.get("confidence", 0)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "<b>📊 تحليل الشارت</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💹 الأصل: <b>{_fmt(result.get('asset'))}</b>\n"
        f"⏱ الفريم: <b>{_fmt(result.get('timeframe'))}</b>\n"
        f"🖼️ جودة الصورة: {_fmt(result.get('image_quality'))}\n\n"
        f"🎯 الإشارة: {icon} <b>{signal}</b>\n"
        f"🧭 الاتجاه: <b>{_fmt(result.get('direction'))}</b>\n"
        f"📈 الثقة التحليلية: <b>{confidence}/100</b>\n"
        "⏱ الأفق المطلوب: <b>5 دقائق</b>\n\n"
        "<b>🔬 التحليل الفني</b>\n"
        f"Trend: {_fmt(result.get('trend'))}\n"
        f"Structure: {_fmt(result.get('structure'))}\n"
        f"Momentum: {_fmt(result.get('momentum'))}\n"
        f"Volatility: {_fmt(result.get('volatility'))}\n"
        f"EMA: {_fmt(result.get('ema'))}\n"
        f"RSI: {_fmt(result.get('rsi'))}\n"
        f"MACD: {_fmt(result.get('macd'))}\n"
        f"Support: {_fmt(result.get('support'))}\n"
        f"Resistance: {_fmt(result.get('resistance'))}\n"
        f"Candles: {_fmt(result.get('candle_patterns'))}\n\n"
        f"<b>🧩 التوافق:</b> {_fmt(result.get('confluence'))}\n"
        f"<b>🧠 السبب:</b> {_fmt(result.get('reason'))}\n"
        f"<b>⚠️ المخاطر/التعارضات:</b> {_fmt(result.get('risks'))}\n\n"
        f"🤖 النموذج: <code>{_fmt(result.get('model'))}</code>\n"
        f"🕐 {now}\n\n"
        "<b>⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة.</b>"
    )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not OPENROUTER_KEY:
        await update.effective_message.reply_text(
            "❌ OpenRouter غير مفعّل. شغّل البوت مع OPENROUTER_API_KEY أولًا."
        )
        return

    photo = update.effective_message.photo[-1]
    status = await update.effective_message.reply_text("🔍 جاري تحليل الصورة بعمق...\n⚡ الرجاء الانتظار قليلًا")
    try:
        telegram_file = await context.bot.get_file(photo.file_id)
        data = await telegram_file.download_as_bytearray()
        result = await analyze_chart_image(bytes(data), "image/jpeg", OPENROUTER_KEY)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 إعادة إرسال صورة أخرى", callback_data="help_image")],
            [InlineKeyboardButton("⬅️ الرئيسية", callback_data="home")],
        ])
        await status.edit_text(format_analysis(result), parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as exc:
        await status.edit_text(
            "❌ تعذر تحليل الصورة.\n\n"
            f"<code>{escape(str(exc))}</code>\n\n"
            "تأكد من أن OPENROUTER_API_KEY صحيح وأن النموذج المختار يدعم الصور.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard(),
        )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "home":
        await query.edit_message_text(home_text(), parse_mode=ParseMode.HTML, reply_markup=main_keyboard())
    elif query.data == "help_image":
        await help_image(update, context)
    elif query.data == "status":
        await query.edit_message_text(
            "<b>📡 حالة النظام</b>\n\n"
            "🟢 Telegram: متصل\n"
            "🟢 Google Colab: يعمل (هذه الجلسة)\n"
            f"{'🟢' if OPENROUTER_KEY else '🔴'} OpenRouter Vision: {'مفعّل' if OPENROUTER_KEY else 'غير مفعّل'}\n"
            "🟢 وضع التنفيذ: READ-ONLY\n\n"
            "لا يتم فتح أو إغلاق أو تنفيذ أي صفقة.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard(),
        )
    elif query.data == "about":
        await query.edit_message_text(
            "<b>ℹ️ عن النظام</b>\n\n"
            "محلل شارت بالصور. يستخرج من الصورة اتجاه السوق وبنية السعر والشموع والمؤشرات الظاهرة والدعم والمقاومة، ثم يراجع الأدلة والتعارضات قبل إعطاء CALL أو PUT أو NO TRADE.\n\n"
            "الثقة تحليلية فقط وليست احتمالًا للربح.\n\n"
            "⚠️ لا توجد أي وظيفة لتنفيذ الصفقات.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard(),
        )


def run():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(callbacks))
    print("Telegram bot is running. IMAGE READ-ONLY mode: no trade execution.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run()
