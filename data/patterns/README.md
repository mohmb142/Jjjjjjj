# Historical OTC pattern data

ضع هنا شموع تاريخية بصيغة CSV أو JSON. يقرأ المحرك `historical_pattern.py` المجلد عبر `PATTERN_DATASET_DIR` (الافتراضي: `data/patterns`).

يفضل ملف باسم الزوج، مثل:

- `EURUSD_otc.csv`
- `GBPUSD_otc.csv`

الحد الأدنى للأعمدة: `open,high,low,close`، ويمكن وجود `timestamp` و`asset`.

## المصدر البحثي المقترح

Dataset عام للبحث في OTC:
https://github.com/PHCStanton/pocket-option-otc-dataset

المستودع يحتوي على بيانات Tick ويمكن تحويلها إلى شموع M1. لا تعتبر هذه البيانات ضماناً بأنها مطابقة لكل جلسة OTC مستقبلية، لذلك يستخدم المحرك قاعدة محافظة: إذا لم يجد عينة تاريخية كافية يعيد `NO TRADE`.

## الإعداد في Colab

يمكن وضع ملف CSV/JSON في `data/patterns/` أو تحديد مسار آخر:

```bash
export PATTERN_DATASET_DIR=/content/otc_dataset
```

ثم شغّل البوت كالمعتاد.
