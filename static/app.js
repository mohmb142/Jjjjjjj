const image = document.getElementById('image');
const out = document.getElementById('out');
const key = document.getElementById('key');
const button = document.getElementById('go');

button.addEventListener('click', async () => {
  const file = image.files[0];
  if (!file) {
    out.textContent = 'اختر صورة شارت أولاً.';
    return;
  }

  if (!file.type.startsWith('image/')) {
    out.textContent = '❌ الملف المختار ليس صورة.';
    return;
  }

  if (file.size > 12 * 1024 * 1024) {
    out.textContent = '❌ حجم الصورة أكبر من 12MB.';
    return;
  }

  button.disabled = true;
  out.textContent = '🔍 جاري تحليل صورة الشارت عبر Vision...';

  try {
    const form = new FormData();
    form.append('file', file);

    const headers = {};
    const apiKey = key.value.trim();
    if (apiKey) headers['X-OpenRouter-Key'] = apiKey;

    const response = await fetch('/api/analyze-image', {
      method: 'POST',
      body: form,
      headers,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    out.textContent = formatResult(data);
  } catch (error) {
    out.textContent = '❌ خطأ: ' + (error.message || error);
  } finally {
    button.disabled = false;
  }
});

function value(v, fallback = 'غير واضح') {
  return v === null || v === undefined || v === '' ? fallback : String(v);
}

function formatResult(d) {
  return [
    '📊 نتيجة تحليل الشارت',
    '━━━━━━━━━━━━━━━━━━━━',
    `الأصل: ${value(d.asset)}`,
    `الفريم: ${value(d.timeframe)}`,
    `جودة الصورة: ${value(d.image_quality)}`,
    '',
    `🎯 الإشارة: ${value(d.signal, 'NO TRADE')}`,
    `🧭 الاتجاه: ${value(d.direction, 'NEUTRAL')}`,
    `🧠 الثقة التحليلية: ${value(d.confidence, 0)}/100`,
    `⏱ الأفق: ${value(d.duration_minutes, 5)} دقائق`,
    '',
    `Trend: ${value(d.trend)}`,
    `Structure: ${value(d.structure)}`,
    `Momentum: ${value(d.momentum)}`,
    `Volatility: ${value(d.volatility)}`,
    `EMA: ${value(d.ema)}`,
    `RSI: ${value(d.rsi)}`,
    `MACD: ${value(d.macd)}`,
    `Support: ${value(d.support)}`,
    `Resistance: ${value(d.resistance)}`,
    `Candles: ${value(d.candle_patterns)}`,
    '',
    `🧩 التوافق: ${value(d.confluence)}`,
    `🧠 السبب: ${value(d.reason)}`,
    `⚠️ المخاطر: ${value(d.risks)}`,
    '',
    `🤖 النموذج: ${value(d.model)}`,
    '',
    value(d.disclaimer, '⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة.'),
  ].join('\n');
}
