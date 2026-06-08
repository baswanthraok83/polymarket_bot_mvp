import requests, time

url = "https://clob.polymarket.com/markets"

success = 0
fail = 0

for i in range(30):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            success += 1
            print(i, "OK")
        else:
            fail += 1
            print(i, "BAD STATUS", r.status_code)
    except Exception as e:
        fail += 1
        print(i, "FAIL", e)

    time.sleep(2)

print("\nSuccess:", success, "Fail:", fail)