# تشغيل Pocket OTC AI Analyzer على Google Colab + Telegram

هذا الوضع يجعل Google Colab محرك التحليل وTelegram واجهة الاستخدام.

## 1) افتح Google Colab

أنشئ Notebook جديدًا، ثم نفّذ الخلايا بالترتيب.

## 2) تثبيت المشروع

```python
!git clone https://github.com/mohmb142/Jjjjjjj.git
%cd Jjjjjjj
!python -m pip install -r colab_requirements.txt
```

`BinaryOptionsToolsV2` الإصدار 0.2.15 لديه wheel جاهز لـ Linux x86-64 وARM64 وARMv7l؛ لذلك Colab، بخلاف Termux Android ARM32، هو البيئة المقصودة لهذا التشغيل. تحقق من إصدار الحزمة قبل الاعتماد على أي تغيير مستقبلي.

## 3) ضبط الأسرار

لا تضع التوكن أو SSID داخل ملفات GitHub.

```python
import os
from getpass import getpass

os.environ['TELEGRAM_BOT_TOKEN'] = getpass('Telegram Bot Token: ')
os.environ['POCKET_OPTION_SSID'] = getpass('Pocket Option SSID: ')

# اختياري:
# os.environ['OPENROUTER_API_KEY'] = getpass('OpenRouter API Key: ')
os.environ['OPENROUTER_MODEL'] = 'openai/gpt-oss-120b:free'
```

## 4) تشغيل البوت

```python
!python telegram_bot.py
```

ستظهر في الخلية رسالة:

```text
Telegram bot is running. READ-ONLY mode: no trade execution.
```

بعدها افتح البوت في Telegram واضغط `/start`.

## 5) الوظائف

- اختيار الزوج من أزرار Telegram.
- جلب الشموع المغلقة الحقيقية فقط.
- EMA 9 / 21 / 50.
- RSI 14.
- MACD.
- ATR 14.
- Support / Resistance.
- اتجاه آخر 10 شموع.
- CALL / PUT / NO TRADE.
- الثقة التحليلية 0-100 وليست احتمال ربح.
- تحليل لمدة 5 دقائق كما هو محدد في الواجهة.
- OpenRouter اختياري مع fallback محلي عند فشله.
- لا توجد أوامر شراء/بيع أو فتح/إغلاق صفقات.

## 6) اختبار الاتصال

إذا ظهر `تعذر الحصول على بيانات حقيقية` فلا يتم توليد شموع وهمية. افحص SSID واتصال Pocket Option وإصدار BinaryOptionsToolsV2.

## ملاحظة مهمة عن Colab

جلسة Colab ليست خادمًا دائمًا؛ قد تنتهي الجلسة أو تعاد تهيئتها. عند انتهاء الجلسة يتوقف البوت. هذا مناسب للاختبار والتشغيل المؤقت، وليس لاستضافة بوت 24/7.
