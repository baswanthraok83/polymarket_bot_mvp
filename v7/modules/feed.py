import requests,pandas as pd

def fetch_real_markets():
 u='https://gamma-api.polymarket.com/markets'
 try:
  r=requests.get(u,timeout=10)
  if r.status_code==200:
   data=r.json(); rows=[]
   for x in data[:25]:
    title=x.get('question') or x.get('title') or 'Unknown'
    op=x.get('outcomePrices')
    yesp=float(op[0]) if isinstance(op,list) and len(op)>0 else 0.5
    rows.append({'market':title,'yes_price':yesp,'no_price':1-yesp,'volume':float(x.get('volume',0))})
   return pd.DataFrame(rows)
 except Exception:
  pass
 return pd.DataFrame(columns=['market','yes_price','no_price','volume'])
