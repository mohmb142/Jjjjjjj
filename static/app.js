const image = document.getElementById('image');
const out = document.getElementById('out');
const key = document.getElementById('key');

document.getElementById('go').onclick = async () => {
  const file = image.files[0];
  if (!file) { out.textContent = 'اختر صورة شارت أولاً.'; return; }
  out.textContent = '🔍 جاري تحليل صورة الشارت عبر Vision...';
  try {
    const form = new FormData();
    form.append('file', file);
    const query = key.value.trim() ? '?openrouter_key=' + encodeURIComponent(key.value.trim()) : '';
    const r = await fetch('/api/analyze-image' + query, { method: 'POST', body: form });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'تعذر التحليل');
    out.textContent = formatResult(d);
  } catch (e) {
    out.textContent = '❌ خطأ: ' + e.message;
  }
};

function formatResult(d) {
  return [
    '📊 نتيجة تحليل الشارت',
    '━━━━━━━━━━━━━━━━━━━━',
    `الأصل: ${d.asset ?? 'غير واضح'}`,
    `الفريم: ${d.timeframe ?? 'غير واضح'}`,
    `جودة الصورة: ${d.image_quality ?? 'غير واضح'}`,
    '',
    `🎯 الإشارة: ${d.signal ?? 'NO TRADE'}`,
    `🧭 الاتجاه: ${d.direction ?? 'NEUTRAL'}`,
    `🧠 الثقة التحليلية: ${d.confidence ?? 0}/100`,
    '',
    `Trend: ${d.trend ?? 'غير واضح'}`,
    `Structure: ${d.structure ?? 'غير واضح'}`,
    `Momentum: ${d.momentum ?? 'غير واضح'}`,
    `Volatility: ${d.volatility ?? 'غير واضح'}`,
    `EMA: ${d.ema ?? 'غير واضح'}`,
    `RSI: ${d.rsi ?? 'غير واضح'}`,
    `MACD: ${d.macd ?? 'غير واضح'}`,
    `Support: ${d.support ?? 'غير واضح'}`,
    `Resistance: ${d.resistance ?? 'غير واضح'}`,
    `Candles: ${d.candle_patterns ?? 'غير واضح'}`,
    '',
    `🧩 التوافق: ${d.confluence ?? 'غير واضح'}`,
    `🧠 السبب: ${d.reason ?? 'غير واضح'}`,
    `⚠️ المخاطر: ${d.risks ?? 'غير واضح'}`,
    '',
    '⚠️ تحليل فقط — لا يتم تنفيذ أي صفقة.'
  ].join('\n');
}
