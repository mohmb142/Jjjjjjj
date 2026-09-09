# 📊 Pocket OTC AI Analyzer

محلل بصري للشارتات يعمل بنمط **READ-ONLY**.

## ما الذي يفعله؟

- استقبال صورة شارت من الويب أو Telegram.
- تحليل الصورة عبر OpenRouter Vision.
- النموذج الافتراضي: `google/gemini-2.5-flash`.
- استخراج الاتجاه، بنية السوق، الزخم، التذبذب، EMA، RSI، MACD، الدعم والمقاومة والشموع الظاهرة.
- النتيجة: `CALL` أو `PUT` أو `NO TRADE`.
- الثقة المعروضة **ثقة تحليلية** وليست احتمال ربح.
- إذا كانت الصورة غير واضحة أو الأدلة متعارضة، يجب أن تكون النتيجة `NO TRADE`.
- لا يوجد تسجيل دخول إلى حساب Pocket Option ولا تنفيذ أو فتح أو إغلاق صفقات.

## التشغيل المحلي

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

في Windows استخدم `.venv\\Scripts\\activate` بدل `source`.

ثم افتح `http://127.0.0.1:8000`.

## Telegram + Google Colab

افتح دفتر:

`Pocket_OTC_AI_Colab.ipynb`

أو استخدم زر **Open in Colab** من GitHub. سيطلب الدفتر:

- `TELEGRAM_BOT_TOKEN`
- `OPENROUTER_API_KEY`

ويضعهما في متغيرات البيئة داخل جلسة Colab فقط. لا تحفظ المفاتيح في GitHub.

## الإعدادات

`.env.example`:

```text
TELEGRAM_BOT_TOKEN=
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-2.5-flash
POCKET_OTC_DATA_API=https://api1.api.cbtraderbd.xyz
```

## API

### فحص الصحة

`GET /health`

### الأزواج

`GET /api/pairs`

### تحليل صورة

`POST /api/analyze-image` مع حقل multipart باسم `file`.

إذا لم يكن `OPENROUTER_API_KEY` مضبوطًا على الخادم، يمكن إرسال المفتاح في Header:

`X-OpenRouter-Key: sk-or-...`

يوجد دعم قديم لـ `?openrouter_key=...` للتوافق، لكن **Header هو الطريقة المفضلة** لأن المفتاح لا يظهر في عنوان URL.

## بيانات الشموع الاختيارية

مسار `/api/analyze` يستخدم خدمة بيانات OTC عامة تابعة لجهة خارجية. هذه الخدمة ليست تسجيل دخول إلى حساب Pocket Option. قد تتغير واجهتها أو تتوقف؛ لذلك لا يعتمد محلل الصور عليها.

## الاختبارات

GitHub Actions يفحص:

- ترجمة ملفات Python.
- المؤشرات ومحرك الإشارة.
- FastAPI `/api/pairs`.
- اتصال خدمة بيانات OTC بشكل غير حاجب للبناء.

يمكن تشغيل الاختبارات محليًا عبر:

```bash
python -m compileall -q .
```

## الأمان

- لا تضع `TELEGRAM_BOT_TOKEN` أو `OPENROUTER_API_KEY` داخل الملفات أو commits.
- لا ترسل SSID أو كلمة مرور أو بيانات حساب تداول.
- هذا المشروع لا ينفذ صفقات.
