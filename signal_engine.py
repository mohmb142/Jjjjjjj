"""Conservative 1-minute signal engine for candle-derived indicators.

The engine deliberately avoids trend-only entries. A 1-minute signal needs
short-term momentum, EMA structure, and room away from nearby support/resistance.
"""


def _pct_distance(price, level):
    if price in (None, 0) or level is None:
        return None
    return abs(price - level) / price * 100


def generate_signal(a):
    score = 0
    reasons = []
    price = a.get('price')
    e9, e21, e50 = a.get('ema9'), a.get('ema21'), a.get('ema50')
    r = a.get('rsi14')
    m = a.get('macd') or {}
    hist = m.get('histogram')
    macd_line, macd_signal = m.get('line'), m.get('signal')
    atr14 = a.get('atr14')
    support, resistance = a.get('support'), a.get('resistance')

    if any(v is None for v in (price, e9, e21, e50, r, macd_line, macd_signal, hist, atr14)):
        return {'signal': 'NO TRADE', 'direction': 'NEUTRAL', 'confidence': 0,
                'reason': 'بيانات أو مؤشرات غير مكتملة لإشارة دقيقة واحدة.', 'score': 0}

    # 1) Fast EMA structure: useful for the next minute, but not enough alone.
    if e9 > e21:
        score += 2; reasons.append('EMA 9 فوق EMA 21')
    elif e9 < e21:
        score -= 2; reasons.append('EMA 9 تحت EMA 21')

    if e21 > e50:
        score += 1; reasons.append('EMA 21 فوق EMA 50')
    elif e21 < e50:
        score -= 1; reasons.append('EMA 21 تحت EMA 50')

    # 2) MACD direction and histogram are separate confirmations.
    if macd_line > macd_signal and hist > 0:
        score += 2; reasons.append('MACD صاعد والهستوغرام موجب')
    elif macd_line < macd_signal and hist < 0:
        score -= 2; reasons.append('MACD هابط والهستوغرام سالب')
    else:
        reasons.append('MACD غير متوافق بالكامل')

    # 3) RSI: avoid chasing extremes on a 1-minute expiry.
    if 52 <= r <= 68:
        score += 1; reasons.append('RSI يدعم الصعود دون تشبع واضح')
    elif 32 <= r <= 48:
        score -= 1; reasons.append('RSI يدعم الهبوط دون تشبع واضح')
    elif r > 72:
        score -= 2; reasons.append('RSI مرتفع جداً: خطر مطاردة الصعود')
    elif r < 28:
        score += 2; reasons.append('RSI منخفض جداً: احتمال ارتداد لكن يحتاج تأكيداً')
    else:
        reasons.append('RSI محايد')

    # 4) Recent candle direction. Require a meaningful short-term imbalance.
    up = a.get('recent_up', 0)
    down = a.get('recent_down', 0)
    if up - down >= 3:
        score += 1; reasons.append('آخر الشموع تميل للصعود')
    elif down - up >= 3:
        score -= 1; reasons.append('آخر الشموع تميل للهبوط')
    else:
        reasons.append('لا يوجد تفوق واضح في آخر الشموع')

    # 5) Do not enter directly into nearby S/R. This was a major source of bad reversals.
    room = max(atr14 * 0.45, price * 0.00025)
    near_support = support is not None and abs(price - support) <= room
    near_resistance = resistance is not None and abs(price - resistance) <= room
    if near_resistance and score > 0:
        score -= 3; reasons.append('السعر قريب من المقاومة: رفض CALL')
    if near_support and score < 0:
        score += 3; reasons.append('السعر قريب من الدعم: رفض PUT')

    # A one-minute expiry needs stronger agreement than a generic direction call.
    if score >= 6:
        signal, direction = 'CALL', 'UP'
    elif score <= -6:
        signal, direction = 'PUT', 'DOWN'
    else:
        signal, direction = 'NO TRADE', 'NEUTRAL'

    confidence = min(95, max(0, round(abs(score) / 8 * 100)))
    if confidence < 75:
        signal, direction = 'NO TRADE', 'NEUTRAL'
        reasons.append('التوافق غير قوي بما يكفي لأفق دقيقة واحدة')

    return {
        'signal': signal,
        'direction': direction,
        'confidence': confidence,
        'reason': '؛ '.join(reasons),
        'score': score,
        'expiry_minutes': 1,
        'near_support': near_support,
        'near_resistance': near_resistance,
    }
