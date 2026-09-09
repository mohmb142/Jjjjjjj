import os
from dotenv import load_dotenv
load_dotenv()
class PocketDataError(Exception): pass
async def get_closed_candles(pair):
    ssid=os.getenv('POCKET_OPTION_SSID','').strip()
    if not ssid: raise PocketDataError('POCKET_OPTION_SSID is not configured')
    try:
        from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
    except Exception as e: raise PocketDataError(f'BinaryOptionsToolsV2 import failed: {e}')
    try:
        client=PocketOptionAsync(ssid); await client.connect(); rows=[]
        async for closed,forming in client.get_candles_live(pair,period=60,hours=2.0,max_rows=100):
            if closed: rows.append(closed)
            if len(rows)>=100: break
        if not rows: raise PocketDataError('Pocket Option returned no closed real candles')
        return normalize(rows)
    except PocketDataError: raise
    except Exception as e: raise PocketDataError(f'Pocket Option connection/data error: {e}')
def normalize(rows):
    out=[]
    for x in rows:
        d=x if isinstance(x,dict) else (vars(x) if hasattr(x,'__dict__') else {})
        try: out.append({'timestamp':d.get('timestamp',d.get('time')),'open':float(d['open']),'high':float(d['high']),'low':float(d['low']),'close':float(d['close'])})
        except Exception: continue
    if not out: raise PocketDataError('Received candle objects could not be normalized')
    return out
