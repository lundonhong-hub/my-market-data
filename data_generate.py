import os
import json
import requests
from datetime import datetime, timezone, timedelta
import yfinance as yf
import time

# 시간 설정 (KST)
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
today = now.strftime("%Y-%m-%d")
update_time = now.strftime("%Y-%m-%d %H:%M:%S")
next_hour = (now + timedelta(hours=1)).strftime("%H:00")

print(f"🚀 데이터 수집 시작: {update_time} KST")

# ── 1. 헬퍼 함수 ──────────────────────────────────────
def get_yf(name, ticker):
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        if hist.empty:
            print(f"  ⚠️ {name}: 데이터 없음")
            return {}
        latest = hist.iloc[-1]
        prev   = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]
        close  = round(float(latest["Close"]), 2)
        prev_c = round(float(prev["Close"]), 2)
        chg    = round((close - prev_c) / prev_c * 100, 2)
        print(f"  ✅ {name}: {close} ({chg:+.2f}%)")
        time.sleep(0.3)
        return {"close": close, "prev_close": prev_c, "change_pct": chg,
                "high": round(float(latest["High"]), 2),
                "low":  round(float(latest["Low"]), 2)}
    except Exception as e:
        print(f"  ⚠️ {name} 오류: {e}")
        return {}

def fmt_krw(v):
    if not v or v == "N/A": return "N/A"
    if v >= 1_000_000: return f"₩{v/1_000_000:.1f}M"
    if v >= 10_000:    return f"₩{int(v):,}"
    return f"₩{int(v):,}"

def color(v, invert=False):
    if v == "N/A" or v is None: return "#7a8a9a"
    try:
        v = float(v)
        if invert: v = -v
        return "#00e676" if v > 0 else "#ff3d57" if v < 0 else "#7a8a9a"
    except: return "#7a8a9a"

def arrow(v):
    try:
        val = float(v)
        return "▲" if val > 0 else "▼" if val < 0 else "—"
    except: return "—"

def fg_color(v):
    try:
        v = int(v)
        if v <= 25: return "#ff3d57" # Extreme Fear
        if v <= 45: return "#ffb300" # Fear
        if v <= 55: return "#e2eaf4" # Neutral
        if v <= 75: return "#00b4d8" # Greed
        return "#00e676"             # Extreme Greed
    except: return "#7a8a9a"

def vix_pct(v):
    try: return min(max(float(v) / 50 * 100, 5), 95)
    except: return 50

# ── 2. 시장 데이터 수집 (yfinance) ──────────────────────────
print("📊 yfinance 시장 데이터 수집 중...")
sp500  = get_yf("SP500",   "^GSPC")
nasdaq = get_yf("NASDAQ",  "^NDX")
vix    = get_yf("VIX",     "^VIX")
gold   = get_yf("GOLD",    "GC=F")
wti    = get_yf("WTI",     "CL=F")
kospi  = get_yf("KOSPI",   "^KS11")
usdkrw = get_yf("USDKRW",  "KRW=X")
tnx    = get_yf("TNX",     "^TNX")

# ── 3. 크립토 데이터 수집 (CoinGecko) ───────────────────────
print("₿ CoinGecko 크립토 데이터 수집 중...")
btc, sol = {}, {}
btc_dominance = "N/A"
try:
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency": "krw", "ids": "bitcoin,solana", "price_change_percentage": "24h,7d,30d"},
        timeout=10
    )
    for coin in r.json():
        data = {
            "krw": coin["current_price"],
            "usd": round(coin["current_price"] / (usdkrw.get("close") or 1400), 0),
            "change_24h": round(coin.get("price_change_percentage_24h") or 0, 2),
            "change_7d":  round(coin.get("price_change_percentage_7d_in_currency") or 0, 2),
            "change_30d": round(coin.get("price_change_percentage_30d_in_currency") or 0, 2),
            "high_24h":   coin.get("high_24h", 0),
            "low_24h":    coin.get("low_24h", 0),
            "ath_change": round(coin.get("ath_change_percentage") or 0, 1),
        }
        if coin["id"] == "bitcoin": btc = data
        elif coin["id"] == "solana": sol = data

    # 7일 고점 추가 수집 (비트코인)
    r2 = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart", params={"vs_currency": "krw", "days": "7", "interval": "daily"}, timeout=10)
    btc["high_7d"] = int(max([p[1] for p in r2.json().get("prices", [])])) if r2.status_code == 200 else btc.get("krw")

    # 도미넌스 수집
    r_global = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
    btc_dominance = round(r_global.json()["data"]["market_cap_percentage"]["btc"], 1)
except Exception as e:
    print(f"  ⚠️ 크립토 수집 오류: {e}")

# ── 4. 공포탐욕지수 (CNN 미러 API 적용) ──────────────────────
print("😨 공포탐욕지수 수집 중...")
# 1) CNN Fear & Greed (미러 API 활용)
fg_cnn_value, fg_cnn_label = "N/A", "점검 중"
try:
    r_cnn = requests.get("https://api.viewer.xyz/fng", timeout=15)
    if r_cnn.status_code == 200:
        cnn_data = r_cnn.json()
        fg_cnn_value = int(round(float(cnn_data.get('score', 0))))
        fg_cnn_label = cnn_data.get('rating', 'N/A').upper()
        print(f"  ✅ CNN F&G: {fg_cnn_value} ({fg_cnn_label})")
except: pass

# 2) Crypto Fear & Greed
fg_crypto_value, fg_crypto_label, fg_crypto_prev = "N/A", "", "N/A"
try:
    r_fng = requests.get("https://api.alternative.me/fng/?limit=2", timeout=10)
    fng_data = r_fng.json()["data"]
    fg_crypto_value = int(fng_data[0]["value"])
    fg_crypto_label = fng_data[0]["value_classification"]
    fg_crypto_prev  = int(fng_data[1]["value"]) if len(fng_data) > 1 else "N/A"
except: pass

# ── 5. HTML 생성 ──────────────────────────────────────
print("🖥️ HTML 생성 중...")

# 시장 변수 정리
sp_v, sp_c = sp500.get("close", "N/A"), sp500.get("change_pct", "N/A")
nq_v, nq_c = nasdaq.get("close", "N/A"), nasdaq.get("change_pct", "N/A")
vx_v, vx_c = vix.get("close", "N/A"), vix.get("change_pct", "N/A")
fx_v, fx_c = usdkrw.get("close", "N/A"), usdkrw.get("change_pct", "N/A")

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Market Dashboard · {update_time}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@400;600&display=swap');
  :root {{
    --bg:#080c10; --card:#111720; --border:#1e2836;
    --up:#00e676; --down:#ff3d57; --warn:#ffb300;
    --accent:#00b4d8; --text:#e2eaf4; --muted:#7a8a9a;
    --btc:#f7931a; --sol:#9945ff;
    --mono:'IBM Plex Mono',monospace; --sans:'IBM Plex Sans KR',sans-serif;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:var(--sans);padding:16px;line-height:1.5}}
  .wrap{{max-width:920px;margin:0 auto}}
  .header{{display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border);margin-bottom:20px}}
  .dot{{width:8px;height:8px;border-radius:50%;background:var(--up);box-shadow:0 0 8px var(--up);display:inline-block;margin-right:8px}}
  .fg-box{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:20px;margin-bottom:20px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
  .fg-item{{text-align:center;border-right:1px solid var(--border)}}
  .fg-item:last-child{{border-right:none}}
  .fg-val{{font-family:var(--mono);font-size:2.2rem;font-weight:600}}
  .g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;position:relative}}
  .card::after{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--muted)}}
  .card.u::after{{background:var(--up)}} .card.d::after{{background:var(--down)}}
  .clbl{{font-family:var(--mono);font-size:.7rem;color:var(--muted);text-transform:uppercase;margin-bottom:8px}}
  .cval{{font-family:var(--mono);font-size:1.3rem;font-weight:600}}
  .cchg{{font-family:var(--mono);font-size:.8rem;font-weight:500}}
  .cc{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:18px;margin-bottom:10px}}
  .cc-meta{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;border-top:1px solid var(--border);padding-top:12px;margin-top:10px}}
  @media(max-width:700px){{.g4,.fg-box{{grid-template-columns:1fr}}.fg-item{{border-right:none;border-bottom:1px solid var(--border);padding:10px}}}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div><span class="dot"></span><strong>MARKET DASHBOARD</strong></div>
    <div style="font-family:var(--mono);font-size:.8rem;color:var(--muted)">{update_time} KST</div>
  </div>

  <div class="fg-box">
    <div class="fg-item">
      <div class="clbl">CNN Fear &amp; Greed</div>
      <div class="fg-val" style="color:{fg_color(fg_cnn_value)}">{fg_cnn_value}</div>
      <div style="font-size:.8rem;color:{fg_color(fg_cnn_value)}">{fg_cnn_label}</div>
    </div>
    <div class="fg-item">
      <div class="clbl">Crypto Fear &amp; Greed</div>
      <div class="fg-val" style="color:{fg_color(fg_crypto_value)}">{fg_crypto_value}</div>
      <div style="font-size:.8rem;color:{fg_color(fg_crypto_value)}">{fg_crypto_label}</div>
    </div>
    <div class="fg-item">
      <div class="clbl">Prev. Crypto F&amp;G</div>
      <div class="fg-val" style="color:{fg_color(fg_crypto_prev)}">{fg_crypto_prev}</div>
      <div style="font-size:.8rem;color:var(--muted)">Yesterday</div>
    </div>
  </div>

  <div class="g4">
    <div class="card {'u' if (isinstance(sp_c, float) and sp_c > 0) else 'd'}">
      <div class="clbl">S&amp;P 500</div>
      <div class="cval" style="color:{color(sp_c)}">{sp_v:,}</div>
      <div class="cchg" style="color:{color(sp_c)}">{arrow(sp_c)} {sp_c}%</div>
    </div>
    <div class="card {'u' if (isinstance(nq_c, float) and nq_c > 0) else 'd'}">
      <div class="clbl">NASDAQ 100</div>
      <div class="cval" style="color:{color(nq_c)}">{nq_v:,}</div>
      <div class="cchg" style="color:{color(nq_c)}">{arrow(nq_c)} {nq_c}%</div>
    </div>
    <div class="card {'d' if (isinstance(vx_v, float) and vx_v > 20) else 'u'}">
      <div class="clbl">VIX Index</div>
      <div class="cval" style="color:{color(vx_c, invert=True)}">{vx_v}</div>
      <div class="cchg" style="color:{color(vx_c, invert=True)}">{arrow(vx_c)} {vx_c}%</div>
    </div>
    <div class="card {'u' if (isinstance(fx_c, float) and fx_c < 0) else 'd'}">
      <div class="clbl">USD / KRW</div>
      <div class="cval" style="color:{color(fx_c, invert=True)}">{fx_v:,}</div>
      <div class="cchg" style="color:{color(fx_c, invert=True)}">{arrow(fx_c)} {fx_c}%</div>
    </div>
  </div>

  <div class="cc" style="border-left:4px solid var(--btc)">
    <div style="display:flex;justify-content:space-between;align-items:center">
        <strong style="color:var(--btc)">BITCOIN (BTC)</strong>
        <span style="font-family:var(--mono);color:{color(btc.get('change_24h'))}">₩{btc.get('krw',0):,} ({arrow(btc.get('change_24h'))} {btc.get('change_24h') or 0}%)</span>
    </div>
    <div class="cc-meta">
        <div><div class="clbl">7일 고점</div><div style="font-family:var(--mono)">{fmt_krw(btc.get('high_7d'))}</div></div>
        <div><div class="clbl">도미넌스</div><div style="font-family:var(--mono)">{btc_dominance}%</div></div>
        <div><div class="clbl">ATH 대비</div><div style="font-family:var(--mono);color:var(--down)">{btc.get('ath_change') or 0}%</div></div>
    </div>
  </div>

  <div style="text-align:right;font-size:.7rem;color:var(--muted);font-family:var(--mono);border-top:1px solid var(--border);padding-top:10px">
    NEXT UPDATE: {next_hour} KST
  </div>
</div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 완료: index.html 생성 성공 ({len(html):,}자)")
