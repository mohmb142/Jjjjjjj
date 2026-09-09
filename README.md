# Pocket OTC AI Analyzer

محلل تقني READ-ONLY لـ Pocket Option OTC.

- يقرأ شموع 1 دقيقة مغلقة عبر BinaryOptionsToolsV2.
- لا يحتوي على تنفيذ صفقات.
- لا يستخدم بيانات عشوائية أو Demo fallback.
- CALL / PUT / NO TRADE.
- الثقة المعروضة هي ثقة تحليلية وليست احتمال ربح.
- OpenRouter اختياري.

## Termux
```bash
pkg update
pkg install python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# ضع POCKET_OPTION_SSID محلياً فقط
uvicorn main:app --host 0.0.0.0 --port 8000
```

افتح `http://127.0.0.1:8000`.

ملاحظة: BinaryOptionsToolsV2 مكتبة غير رسمية وقد تتغير واجهتها؛ يجب اختبار الإصدار المثبت فعلياً.
