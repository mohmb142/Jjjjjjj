"""Conservative rule-based signal engine for candle-derived indicators."""


def generate_signal(a):
    score = 0
    reasons = []
    e9, e21, e50 = a.get('ema9'), a.get('ema21'), a.get('ema50')
    r = a.get('rsi14')
    m = a.get('macd') or {}
    hist = m.get('histogram')

    if any(v is None for v in (e9, e21, e50, r, m.get('signal'), hist)):
        return {'signal': 'NO TRADE', 'direction': 'NEUTRAL', 'confidence': 0,
                'reason': 'بيانات أو مؤشرات غير مكتملة.', 'score': 0}

    if e9 > e21:
        score += 1; reasons.append('EMA 9 أعلى من EMA 21')
    elif e9 < e21:
        score -= 1; reasons.append('EMA 9 أسفل EMA 21')

    if e21 > e50:
        score += 1; reasons.append('EMA 21 أعلى من EMA 50')
    elif e21 < e50:
        score -= 1; reasons.append('EMA 21 أسفل EMA 50')

    if hist > 0:
        score += 1; reasons.append('MACD موجب')
    elif hist < 0:
        score -= 1; reasons.append('MACD سالب')

    if 50 < r < 70:
        score += 1; reasons.append('RSI يدعم الصعود')
    elif 30 < r < 50:
        score -= 1; reasons.append('RSI يدعم الهبوط')
    else:
        reasons.append('RSI متطرف أو محايد')

    up = a.get('recent_up', 0)
    down = a.get('recent_down', 0)
    if up > down:
        score += 1; reasons.append('آخر 10 شموع تميل للصعود')
    elif down > up:
        score -= 1; reasons.append('آخر 10 شموع تميل للهبوط')

    # Require strong agreement. Scores 3/-3 are deliberately NO TRADE.
    if score >= 4:
        signal, direction = 'CALL', 'UP'
    elif score <= -4:
        signal, direction = 'PUT', 'DOWN'
    else:
        signal, direction = 'NO TRADE', 'NEUTRAL'

    confidence = min(100, round(abs(score) / 5 * 100))
    if confidence < 70:
        signal, direction = 'NO TRADE', 'NEUTRAL'

    return {
        'signal': signal,
        'direction': direction,
        'confidence': confidence,
        'reason': '؛ '.join(reasons),
        'score': score,
    }
