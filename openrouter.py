import os,httpx,json
ENDPOINT='https://openrouter.ai/api/v1/chat/completions'
async def refine_with_openrouter(result,analysis,api_key):
    prompt=('Review this READ-ONLY technical analysis. Do not execute or recommend a trade. Return JSON with signal limited to CALL, PUT, NO TRADE; direction; confidence 0-100 as analytical confidence only; and reason. If evidence conflicts, use NO TRADE. Local result: '+str(result)+' Indicators: '+str(analysis))
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(ENDPOINT,headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},json={'model':os.getenv('OPENROUTER_MODEL','openai/gpt-oss-120b:free'),'messages':[{'role':'user','content':prompt}],'temperature':0})
        r.raise_for_status();d=r.json()
    obj=json.loads(d['choices'][0]['message']['content'])
    if obj.get('signal') not in {'CALL','PUT','NO TRADE'}:raise ValueError('Invalid OpenRouter signal')
    obj['confidence']=max(0,min(100,int(obj.get('confidence',0))))
    return obj
