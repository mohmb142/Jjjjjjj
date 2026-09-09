def generate_signal(a):
    score=0; reasons=[];e9,e21,e50=a['ema9'],a['ema21'],a['ema50'];r=a['rsi14'];m=a['macd']
    if None in (e9,e21,e50,r) or m is None or m['signal'] is None:return {'signal':'NO TRADE','direction':'NEUTRAL','confidence':0,'reason':'بيانات أو مؤشرات غير مكتملة.'}
    if e9>e21:score+=1;reasons.append('EMA 9 أعلى من EMA 21')
    elif e9<e21:score-=1;reasons.append('EMA 9 أسفل EMA 21')
    if e21>e50:score+=1;reasons.append('EMA 21 أعلى من EMA 50')
    elif e21<e50:score-=1;reasons.append('EMA 21 أسفل EMA 50')
    if m['histogram']>0:score+=1;reasons.append('MACD موجب')
    elif m['histogram']<0:score-=1;reasons.append('MACD سالب')
    if 50<r<70:score+=1;reasons.append('RSI يدعم الزخم الصاعد')
    elif 30<r<50:score-=1;reasons.append('RSI يدعم الزخم الهابط')
    else: reasons.append('RSI في منطقة متطرفة أو محايدة')
    if a['recent_up']>a['recent_down']:score+=1;reasons.append('آخر 10 شموع تميل للصعود')
    elif a['recent_down']>a['recent_up']:score-=1;reasons.append('آخر 10 شموع تميل للهبوط')
    sig='CALL' if score>=4 else 'PUT' if score<=-4 else 'NO TRADE'; direction='UP' if sig=='CALL' else 'DOWN' if sig=='PUT' else 'NEUTRAL'
    return {'signal':sig,'direction':direction,'confidence':min(100,round(abs(score)/5*100)),'reason':'؛ '.join(reasons),'score':score}
