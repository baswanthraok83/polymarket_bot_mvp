
import pandas as pd, random
def fetch_markets():
    rows=[
      {"market":"BTC > 100k","price":round(random.uniform(.35,.55),2),"volume":120000},
      {"market":"Election X","price":round(random.uniform(.45,.7),2),"volume":90000},
      {"market":"Fed cuts","price":round(random.uniform(.3,.6),2),"volume":100000},
      {"market":"Team A wins","price":round(random.uniform(.2,.8),2),"volume":80000},
    ]
    return pd.DataFrame(rows)
