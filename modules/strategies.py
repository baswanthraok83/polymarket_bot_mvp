
def generate_signals(df):
    out=[]
    for _,r in df.iterrows():
        side="YES" if r["price"]<0.45 else "NO"
        score=int((r["volume"]/2000)+(50 if r["price"]<0.5 else 20))
        out.append({"market":r["market"],"side":side,"price":r["price"],"score":score})
    return out
