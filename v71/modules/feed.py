import requests,pandas as pd,json

def parse_prices(x):
 src='fallback'; yes=0.5
 op=x.get('outcomePrices')
 if isinstance(op,list) and len(op)>=2:
  try:
   yes=float(op[0]); src='outcomePrices'
   return yes,1-yes,src
  except: pass
 if isinstance(op,str):
  try:
   arr=json.loads(op); yes=float(arr[0]); src='outcomePrices(str)'; return yes,1-yes,src
  except: pass
 bb=x.get('bestBid'); ba=x.get('bestAsk')
 if bb is not None and ba is not None:
  try:
   yes=(float(bb)+float(ba))/2; src='bidask_mid'; return yes,1-yes,src
  except: pass
 lp=x.get('lastTradePrice')
 if lp is not None:
  try:
   yes=float(lp); src='lastTradePrice'; return yes,1-yes,src
  except: pass
 return yes,1-yes,src

def fetch_real_markets():
 u='https://gamma-api.polymarket.com/markets'
 try:
  r=requests.get(u,timeout=10)
  if r.status_code==200:
   data=r.json(); rows=[]
   for x in data[:25]:
    title=x.get('question') or x.get('title') or 'Unknown'
    y,n,s=parse_prices(x)
    rows.append({'market':title,'yes_price':round(y,4),'no_price':round(n,4),'volume':float(x.get('volume',0)),'source':s})
   return pd.DataFrame(rows)
 except Exception:
  pass
 return pd.DataFrame(columns=['market','yes_price','no_price','volume','source'])
