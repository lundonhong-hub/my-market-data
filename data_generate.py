import os
import json
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
today = now.strftime("%Y-%m-%d")
update_time = now.strftime("%Y-%m-%d %H:%M:%S")
next_hour = (now + timedelta(hours=1)).strftime("%H:00")

print(f"🚀 데이터 수집 시작: {update_time} KST")

# ── 1. yfinance 수집 ──────────────────────────────────
print("📊 yfinance 시장 데이터 수집 중...")
import yfinance as yf
import time

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

sp500  = get_yf("SP500",   "^GSPC")
nasdaq = get_yf("NASDAQ",  "^NDX")
vix    = get_yf("VIX",     "^VIX")
gold   = get_yf("GOLD",    "GC=F")
wti    = get_yf("WTI",     "CL=F")
kospi  = get_yf("KOSPI",   "^KS11")
usdkrw = get_yf("USDKRW",  "KRW=X")
tnx    = get_yf("TNX",     "^TNX")

# ── 2. CoinGecko BTC + SOL ────────────────────────────
print("₿ CoinGecko 크립토 데이터 수집 중...")
btc = {}
sol = {}
btc_dominance = "N/A"
try:
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency": "krw", "ids": "bitcoin,solana",
                "price_change_percentage": "24h,7d,30d"},
        timeout=10
    )
    for coin in r.json():
        data = {
            "krw":        coin["current_price"],
            "usd":        round(coin["current_price"] / (usdkrw.get("close") or 1400), 0),
            "change_24h": round(coin.get("price_change_percentage_24h") or 0, 2),
            "change_7d":  round(coin.get("price_change_percentage_7d_in_currency") or 0, 2),
            "change_30d": round(coin.get("price_change_percentage_30d_in_currency") or 0, 2),
            "high_24h":   coin.get("high_24h", 0),
            "low_24h":    coin.get("low_24h", 0),
            "ath_krw":    coin.get("ath", 0),
            "ath_change": round(coin.get("ath_change_percentage") or 0, 1),
        }
        if coin["id"] == "bitcoin":
            btc = data
            print(f"  ✅ BTC: ₩{btc['krw']:,} ({btc['change_24h']:+.2f}%)")
        elif coin["id"] == "solana":
            sol = data
            print(f"  ✅ SOL: ₩{sol['krw']:,} ({sol['change_24h']:+.2f}%)")
except Exception as e:
    print(f"  ⚠️ CoinGecko 오류: {e}")

# BTC 7일 고점
try:
    r2 = requests.get(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
        params={"vs_currency": "krw", "days": "7", "interval": "daily"},
        timeout=10
    )
    prices_7d = [p[1] for p in r2.json().get("prices", [])]
    btc["high_7d"] = int(max(prices_7d)) if prices_7d else btc.get("krw", 0)
except:
    btc["high_7d"] = btc.get("krw", 0)

# BTC 도미넌스
try:
    r3 = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
    btc_dominance = round(r3.json()["data"]["market_cap_percentage"]["btc"], 1)
    print(f"  ✅ BTC 도미넌스: {btc_dominance}%")
except:
    pass

# SOL 7일 고점
try:
    r4 = requests.get(
        "https://api.coingecko.com/api/v3/coins/solana/market_chart",
        params={"vs_currency": "krw", "days": "7", "interval": "daily"},
        timeout=10
    )
    prices_sol_7d = [p[1] for p in r4.json().get("prices", [])]
    sol["high_7d"] = int(max(prices_sol_7d)) if prices_sol_7d else sol.get("krw", 0)
except:
    sol["high_7d"] = sol.get("krw", 0)

# ── 3. 공포탐욕지수 ───────────────────────────────────
print("😨 공포탐욕지수 수집 중...")
fg_crypto_value = "N/A"
fg_crypto_label = ""
fg_crypto_prev  = "N/A"
try:
    r = requests.get("https://api.alternative.me/fng/?limit=2", timeout=10)
    data = r.json()["data"]
    fg_crypto_value = int(data[0]["value"])
    fg_crypto_label = data[0]["value_classification"]
    fg_crypto_prev  = int(data[1]["value"]) if len(data) > 1 else fg_crypto_value
    print(f"  ✅ 크립토 F&G: {fg_crypto_value} ({fg_crypto_label})")
except Exception as e:
    print(f"  ⚠️ F&G 오류: {e}")

# ── 4. 헬퍼 함수 ──────────────────────────────────────
def fmt_krw(v):
    if not v: return "N/A"
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
        return "▲" if float(v) > 0 else "▼" if float(v) < 0 else "—"
    except: return "—"

def fg_color(v):
    try:
        v = int(v)
        if v <= 25: return "#ff3d57"
        if v <= 45: return "#ffb300"
        if v <= 55: return "#e2eaf4"
        if v <= 75: return "#00b4d8"
        return "#00e676"
    except: return "#7a8a9a"

def vix_pct(v):
    try: return min(max(float(v) / 50 * 100, 5), 95)
    except: return 50

# ── 5. HTML 생성 ──────────────────────────────────────
print("🖥️ HTML 생성 중...")

sp_v   = sp500.get("close",      "N/A")
sp_c   = sp500.get("change_pct", "N/A")
nq_v   = nasdaq.get("close",     "N/A")
nq_c   = nasdaq.get("change_pct","N/A")
vx_v   = vix.get("close",        "N/A")
vx_c   = vix.get("change_pct",   "N/A")
ks_v   = kospi.get("close",      "N/A")
ks_c   = kospi.get("change_pct", "N/A")
gd_v   = gold.get("close",       "N/A")
gd_c   = gold.get("change_pct",  "N/A")
wt_v   = wti.get("close",        "N/A")
wt_c   = wti.get("change_pct",   "N/A")
fx_v   = usdkrw.get("close",     "N/A")
fx_c   = usdkrw.get("change_pct","N/A")
tn_v   = tnx.get("close",        "N/A")
tn_c   = tnx.get("change_pct",   "N/A")

btc_v  = btc.get("krw",      "N/A")
btc_u  = btc.get("usd",      "N/A")
btc_c  = btc.get("change_24h","N/A")
btc_h  = btc.get("high_24h", "N/A")
btc_l  = btc.get("low_24h",  "N/A")
btc_7  = btc.get("high_7d",  "N/A")
btc_a  = btc.get("ath_change","N/A")
btc_30 = btc.get("change_30d","N/A")
btc_7c = btc.get("change_7d", "N/A")

sol_v  = sol.get("krw",      "N/A")
sol_u  = sol.get("usd",      "N/A")
sol_c  = sol.get("change_24h","N/A")
sol_h  = sol.get("high_24h", "N/A")
sol_l  = sol.get("low_24h",  "N/A")
sol_7  = sol.get("high_7d",  "N/A")
sol_a  = sol.get("ath_change","N/A")
sol_30 = sol.get("change_30d","N/A")
sol_7c = sol.get("change_7d", "N/A")

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="3600">
<title>Market Data · {update_time}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600&display=swap');
  :root {{
    --bg:#080c10; --card:#111720; --border:#1e2836;
    --up:#00e676; --down:#ff3d57; --warn:#ffb300;
    --accent:#00b4d8; --btc:#f7931a; --sol:#9945ff;
    --text:#e2eaf4; --muted:#7a8a9a;
    --mono:'IBM Plex Mono',monospace; --sans:'IBM Plex Sans KR',sans-serif;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:var(--sans);padding:16px}}
  body::before{{content:'';position:fixed;inset:0;
    background-image:linear-gradient(rgba(0,180,216,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,180,216,.025) 1px,transparent 1px);
    background-size:40px 40px;pointer-events:none;z-index:0}}
  .wrap{{position:relative;z-index:1;max-width:920px;margin:0 auto}}
  .header{{display:flex;justify-content:space-between;align-items:center;padding:12px 0 18px;border-bottom:1px solid var(--border);margin-bottom:20px}}
  .header-left{{display:flex;align-items:center;gap:10px}}
  .dot{{width:8px;height:8px;border-radius:50%;background:var(--up);box-shadow:0 0 8px var(--up);animation:pulse 2s infinite}}
  @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
  .htitle{{font-family:var(--mono);font-size:.85rem;color:var(--accent);letter-spacing:2px;text-transform:uppercase}}
  .htime{{font-family:var(--mono);font-size:.78rem;color:var(--muted)}}
  .slabel{{font-family:var(--mono);font-size:.75rem;color:var(--accent);letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;display:flex;align-items:center;gap:10px}}
  .slabel::after{{content:'';flex:1;height:1px;background:var(--border)}}
  .fg-box{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:18px 20px;margin-bottom:20px;display:grid;grid-template-columns:repeat(3,1fr)}}
  .fg-item{{text-align:center;padding:6px 12px;position:relative}}
  .fg-item:not(:last-child)::after{{content:'';position:absolute;right:0;top:8%;bottom:8%;width:1px;background:var(--border)}}
  .fg-lbl{{font-family:var(--mono);font-size:.73rem;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;font-weight:500}}
  .fg-val{{font-family:var(--mono);font-size:2.2rem;font-weight:600;line-height:1;margin-bottom:5px}}
  .fg-txt{{font-size:.75rem;font-weight:500}}
  .g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:10px}}
  .g3{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px}}
  .g2{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:20px}}
  @media(max-width:700px){{.g4,.g3{{grid-template-columns:repeat(2,1fr)}}.g2,.fg-box{{grid-template-columns:1fr}}}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px;position:relative;overflow:hidden;animation:fi .4s ease forwards;opacity:0}}
  .card::after{{content:'';position:absolute;top:0;left:0;right:0;height:2px}}
  .card.u::after{{background:var(--up)}}.card.d::after{{background:var(--down)}}.card.w::after{{background:var(--warn)}}
  .clbl{{font-family:var(--mono);font-size:.75rem;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;font-weight:500}}
  .cval{{font-family:var(--mono);font-size:1.4rem;font-weight:600;line-height:1;margin-bottom:6px}}
  .cchg{{font-family:var(--mono);font-size:.78rem;font-weight:500}}
  .csub{{font-family:var(--mono);font-size:.7rem;color:var(--muted);margin-top:5px}}
  .vix-bar{{margin-top:8px;height:4px;border-radius:2px;background:linear-gradient(to right,var(--up),var(--warn),var(--down));position:relative}}
  .vix-mk{{position:absolute;top:-4px;width:12px;height:12px;background:white;border-radius:50%;transform:translateX(-50%);box-shadow:0 0 5px rgba(255,255,255,.6)}}
  .vix-lbl{{display:flex;justify-content:space-between;margin-top:5px;font-family:var(--mono);font-size:.65rem}}
  .cc{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:18px;position:relative;overflow:hidden;animation:fi .4s ease forwards;opacity:0}}
  .cc::after{{content:'';position:absolute;top:0;left:0;right:0;height:2px}}
  .cc.btc::after{{background:var(--btc)}}.cc.sol::after{{background:var(--sol)}}
  .cc-hd{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}
  .cc-nm{{font-family:var(--mono);font-size:.78rem;color:var(--muted);letter-spacing:2px;text-transform:uppercase;font-weight:500}}
  .badge{{font-family:var(--mono);font-size:.68rem;padding:3px 10px;border-radius:3px;font-weight:600;letter-spacing:1px}}
  .btc-b{{background:rgba(247,147,26,.15);color:var(--btc);border:1px solid rgba(247,147,26,.3)}}
  .sol-b{{background:rgba(153,69,255,.15);color:var(--sol);border:1px solid rgba(153,69,255,.3)}}
  .cc-price{{font-family:var(--mono);font-size:1.65rem;font-weight:600;margin-bottom:5px}}
  .cc-usd{{font-family:var(--mono);font-size:.82rem;color:var(--muted);margin-bottom:14px}}
  .cc-meta{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;border-top:1px solid var(--border);padding-top:12px}}
  .ml{{font-family:var(--mono);font-size:.67rem;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;font-weight:500}}
  .mv{{font-family:var(--mono);font-size:.85rem;font-weight:600}}
  .ubar{{display:flex;justify-content:space-between;align-items:center;padding:12px 0 4px;border-top:1px solid var(--border);margin-top:4px}}
  .utxt{{font-family:var(--mono);font-size:.68rem;color:var(--muted)}}
  .unxt{{font-family:var(--mono);font-size:.68rem;color:var(--accent)}}
  @keyframes fi{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
  .fg-box{{animation:fi .3s ease forwards;opacity:0;animation-delay:.05s}}
  .d1{{animation-delay:.10s}}.d2{{animation-delay:.15s}}.d3{{animation-delay:.20s}}.d4{{animation-delay:.25s}}
  .d5{{animation-delay:.30s}}.d6{{animation-delay:.35s}}.d7{{animation-delay:.40s}}
  .d8{{animation-delay:.45s}}.d9{{animation-delay:.50s}}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <div class="header-left"><div class="dot"></div><div class="htitle">Market Data</div></div>
    <div class="htime">{today} · {now.strftime("%H:%M")} KST</div>
  </div>

  <!-- 공포탐욕 -->
  <div class="slabel">Fear &amp; Greed</div>
  <div class="fg-box">
    <div class="fg-item">
      <div class="fg-lbl">CNN Fear &amp; Greed</div>
      <div class="fg-val" style="color:#7a8a9a">N/A</div>
      <div class="fg-txt" style="color:#7a8a9a">웹검색 필요</div>
    </div>
    <div class="fg-item">
      <div class="fg-lbl">Crypto Fear &amp; Greed</div>
      <div class="fg-val" style="color:{fg_color(fg_crypto_value)}">{fg_crypto_value}</div>
      <div class="fg-txt" style="color:{fg_color(fg_crypto_value)}">{fg_crypto_label}</div>
    </div>
    <div class="fg-item">
      <div class="fg-lbl">전일 Crypto F&amp;G</div>
      <div class="fg-val" style="color:{fg_color(fg_crypto_prev)}">{fg_crypto_prev}</div>
      <div class="fg-txt" style="color:{fg_color(fg_crypto_prev)}">전일</div>
    </div>
  </div>

  <!-- 글로벌 지수 -->
  <div class="slabel">Global Indices</div>
  <div class="g4" style="margin-bottom:20px">
    <div class="card {'u' if (sp_c or 0) > 0 else 'd'} d1">
      <div class="clbl">S&amp;P 500</div>
      <div class="cval" style="color:{color(sp_c)}">{sp_v:,}</div>
      <div class="cchg" style="color:{color(sp_c)}">{arrow(sp_c)} {sp_c}%</div>
      <div class="csub">전일 {sp500.get('prev_close','N/A'):,}</div>
    </div>
    <div class="card {'u' if (nq_c or 0) > 0 else 'd'} d2">
      <div class="clbl">NASDAQ 100</div>
      <div class="cval" style="color:{color(nq_c)}">{nq_v:,}</div>
      <div class="cchg" style="color:{color(nq_c)}">{arrow(nq_c)} {nq_c}%</div>
      <div class="csub">전일 {nasdaq.get('prev_close','N/A'):,}</div>
    </div>
    <div class="card w d3">
      <div class="clbl">VIX</div>
      <div class="cval" style="color:{'#ff3d57' if (vx_v or 0)>25 else '#ffb300' if (vx_v or 0)>20 else '#00e676'}">{vx_v}</div>
      <div class="cchg" style="color:{color(vx_c, invert=True)}">{arrow(vx_c)} {vx_c}%</div>
      <div class="vix-bar"><div class="vix-mk" style="left:{vix_pct(vx_v)}%"></div></div>
      <div class="vix-lbl"><span style="color:var(--up)">안정</span><span style="color:var(--warn)">경계</span><span style="color:var(--down)">위험</span></div>
    </div>
    <div class="card {'u' if (ks_c or 0) > 0 else 'd'} d4">
      <div class="clbl">KOSPI</div>
      <div class="cval" style="color:{color(ks_c)}">{ks_v:,}</div>
      <div class="cchg" style="color:{color(ks_c)}">{arrow(ks_c)} {ks_c}%</div>
      <div class="csub">전일 {kospi.get('prev_close','N/A'):,}</div>
    </div>
  </div>

  <!-- 매크로 -->
  <div class="slabel">Macro</div>
  <div class="g4" style="margin-bottom:20px">
    <div class="card {'u' if (gd_c or 0) > 0 else 'd'} d5">
      <div class="clbl">Gold</div>
      <div class="cval" style="color:{color(gd_c)}">${gd_v:,}</div>
      <div class="cchg" style="color:{color(gd_c)}">{arrow(gd_c)} {gd_c}%</div>
      <div class="csub">전일 ${gold.get('prev_close','N/A'):,}</div>
    </div>
    <div class="card {'u' if (wt_c or 0) > 0 else 'd'} d6">
      <div class="clbl">WTI Crude</div>
      <div class="cval" style="color:{color(wt_c)}">${wt_v}</div>
      <div class="cchg" style="color:{color(wt_c)}">{arrow(wt_c)} {wt_c}%</div>
      <div class="csub">전일 ${wti.get('prev_close','N/A')}</div>
    </div>
    <div class="card {'u' if (fx_c or 0) > 0 else 'd'} d7">
      <div class="clbl">USD / KRW</div>
      <div class="cval" style="color:{color(fx_c, invert=True)}">{fx_v:,}</div>
      <div class="cchg" style="color:{color(fx_c, invert=True)}">{arrow(fx_c)} {fx_c}%</div>
      <div class="csub">전일 {usdkrw.get('prev_close','N/A'):,}</div>
    </div>
    <div class="card {'u' if (tn_c or 0) < 0 else 'd'} d8">
      <div class="clbl">10Y Treasury</div>
      <div class="cval" style="color:{color(tn_c, invert=True)}">{tn_v}%</div>
      <div class="cchg" style="color:{color(tn_c, invert=True)}">{arrow(tn_c)} {tn_c}%</div>
      <div class="csub">전일 {tnx.get('prev_close','N/A')}%</div>
    </div>
  </div>

  <!-- 크립토 -->
  <div class="slabel">Crypto</div>
  <div class="g2">
    <div class="cc btc d8">
      <div class="cc-hd">
        <div class="cc-nm">Bitcoin</div>
        <div class="badge btc-b">BTC</div>
      </div>
      <div class="cc-price" style="color:var(--btc)">₩{btc_v:,}</div>
      <div class="cc-usd">≈ ${btc_u:,} &nbsp;·&nbsp; <span style="color:{color(btc_c)}">{arrow(btc_c)} {btc_c}%</span></div>
      <div class="cc-meta">
        <div><div class="ml">24h 고점</div><div class="mv" style="color:var(--up)">{fmt_krw(btc_h)}</div></div>
        <div><div class="ml">24h 저점</div><div class="mv" style="color:var(--down)">{fmt_krw(btc_l)}</div></div>
        <div><div class="ml">ATH 대비</div><div class="mv" style="color:var(--down)">{btc_a}%</div></div>
        <div><div class="ml">7일 고점</div><div class="mv" style="color:var(--btc)">{fmt_krw(btc_7)}</div></div>
        <div><div class="ml">전월比</div><div class="mv" style="color:{color(btc_30)}">{arrow(btc_30)} {btc_30}%</div></div>
        <div><div class="ml">도미넌스</div><div class="mv" style="color:var(--btc)">{btc_dominance}%</div></div>
      </div>
    </div>
    <div class="cc sol d9">
      <div class="cc-hd">
        <div class="cc-nm">Solana</div>
        <div class="badge sol-b">SOL</div>
      </div>
      <div class="cc-price" style="color:var(--sol)">₩{sol_v:,}</div>
      <div class="cc-usd">≈ ${sol_u:,} &nbsp;·&nbsp; <span style="color:{color(sol_c)}">{arrow(sol_c)} {sol_c}%</span></div>
      <div class="cc-meta">
        <div><div class="ml">24h 고점</div><div class="mv" style="color:var(--up)">{fmt_krw(sol_h)}</div></div>
        <div><div class="ml">24h 저점</div><div class="mv" style="color:var(--down)">{fmt_krw(sol_l)}</div></div>
        <div><div class="ml">ATH 대비</div><div class="mv" style="color:var(--down)">{sol_a}%</div></div>
        <div><div class="ml">7일 고점</div><div class="mv" style="color:var(--sol)">{fmt_krw(sol_7)}</div></div>
        <div><div class="ml">전월比</div><div class="mv" style="color:{color(sol_30)}">{arrow(sol_30)} {sol_30}%</div></div>
        <div><div class="ml">7일比</div><div class="mv" style="color:{color(sol_7c)}">{arrow(sol_7c)} {sol_7c}%</div></div>
      </div>
    </div>
  </div>

  <div class="ubar">
    <div class="utxt">⏱ 최종 업데이트: {update_time} KST</div>
    <div class="unxt">다음 업데이트 → {next_hour}</div>
  </div>

</div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 완료: index.html ({len(html):,}자)")
