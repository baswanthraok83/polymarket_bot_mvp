
def rank_markets(df):
    df=df.copy()
    df["score"]=(df["volume"]/2000)+(1-df["price"])*50
    return df.sort_values("score", ascending=False)
