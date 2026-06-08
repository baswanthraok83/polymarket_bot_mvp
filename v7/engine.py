import time
from modules.feed import fetch_real_markets
from modules.db import save_snapshots
print('V7 Real Data Engine started')
while True:
 df=fetch_real_markets(); save_snapshots(df); print('Fetched',len(df),'real markets'); time.sleep(60)
