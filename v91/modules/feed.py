
import requests, pandas as pd, json

def parse_prices(x):
    op=x.get("outcomePrices")
    if isinstance(op,list) and len(op)>0:
        try:
            y=float(op[0]); return y,1-y,"outcomePrices"
        except: pass
    if isinstance(op,str):
        try:
            arr=json.loads(op)
            y=float(arr[0]); return y,1-y,"outcomePrices(str)"
        except: pass
    return 0.5,0.5,"fallback"

def fetch_real_markets():
    rows=[]
    try:
        r=requests.get("https://gamma-api.polymarket.com/markets",timeout=10)
        if r.status_code==200:
            data=r.json()[:20]
            for x in data:
                title=x.get("question") or x.get("title") or "Unknown"
                y,n,s=parse_prices(x)
                rows.append({"market":title,"yes_price":y,"no_price":n,"volume":float(x.get("volume",0)),"source":s})
    except:
        pass
    return pd.DataFrame(rows)
