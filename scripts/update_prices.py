"""抓取觀察清單的最新收盤價，寫入 prices.json（不需要 API key）。
來源：Yahoo Finance chart API，失敗時改用 Stooq CSV。代號清單從 index.html 的 GROUPS 讀取。"""
import json, re, urllib.request, datetime, pathlib, csv, io
ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode()
def yahoo(t):
    j = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5d&interval=1d"))["chart"]["result"][0]
    rows = [(ts, c) for ts, c in zip(j["timestamp"], j["indicators"]["quote"][0]["close"]) if c is not None]
    m = j["meta"]; ts, c = rows[-1]; prev = rows[-2][1] if len(rows) > 1 else m.get("chartPreviousClose")
    tz = datetime.timezone(datetime.timedelta(seconds=m.get("gmtoffset", 0)))
    return {"close": round(c, 4), "prev": round(prev, 4) if prev else None, "date": datetime.datetime.fromtimestamp(ts, tz).date().isoformat(), "src": "yahoo"}
def stooq(t):
    rows = list(csv.DictReader(io.StringIO(get(f"https://stooq.com/q/d/l/?s={t.lower()}.us&i=d"))))[-2:]
    return {"close": float(rows[-1]["Close"]), "prev": float(rows[0]["Close"]) if len(rows) > 1 else None, "date": rows[-1]["Date"], "src": "stooq"}
html = (ROOT / "index.html").read_text(encoding="utf-8")
syms = sorted({s.split(":")[-1] for s in re.findall(r'"[A-Z]+:([A-Z.]+)"', html)} | set(re.findall(r'"(?:NASDAQ|NYSE|AMEX):([A-Z.]+)"', html)))
old = {}
p = ROOT / "prices.json"
if p.exists(): old = json.loads(p.read_text()).get("prices", {})
out, fails = {}, []
for t in syms:
    for f in (yahoo, stooq):
        try: out[t] = f(t); break
        except Exception as e: err = e
    else:
        fails.append(t)
        if t in old: out[t] = old[t]
print("ok:", len(out) - len(fails), "fail:", fails)
p.write_text(json.dumps({"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "prices": out}, ensure_ascii=False, indent=1))
