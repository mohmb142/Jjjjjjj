def ema(v,p):
    if len(v)<p:return None
    k=2/(p+1); x=sum(v[:p])/p
    for z in v[p:]: x=z*k+x*(1-k)
    return x
def rsi(v,p=14):
    if len(v)<=p:return None
    g=[];l=[]
    for a,b in zip(v[-p-1:-1],v[-p:]):
        c=b-a;g.append(max(c,0));l.append(max(-c,0))
    ag=sum(g)/p;al=sum(l)/p
    return 100 if al==0 else 100-100/(1+ag/al)
def macd(v):
    f=ema(v,12);s=ema(v,26)
    if f is None or s is None:return None
    line=f-s; series=[]
    for i in range(26,len(v)+1): series.append(ema(v[:i],12)-ema(v[:i],26))
    sig=ema(series,9) if len(series)>=9 else None
    return {'line':line,'signal':sig,'histogram':None if sig is None else line-sig}
def atr(c,p=14):
    if len(c)<=p:return None
    t=[]
    for i in range(1,len(c)):
        x=c[i];q=c[i-1]['close'];t.append(max(x['high']-x['low'],abs(x['high']-q),abs(x['low']-q)))
    return sum(t[-p:])/p
def analyze_candles(c):
    v=[x['close'] for x in c];r=c[-10:]
    up=sum(b['close']>a['close'] for a,b in zip(r,r[1:]));down=sum(b['close']<a['close'] for a,b in zip(r,r[1:]))
    return {'price':v[-1],'ema9':ema(v,9),'ema21':ema(v,21),'ema50':ema(v,50),'rsi14':rsi(v),'macd':macd(v),'atr14':atr(c),'support':min(x['low'] for x in c[-20:]),'resistance':max(x['high'] for x in c[-20:]),'recent_up':up,'recent_down':down,'candles_used':len(c)}
