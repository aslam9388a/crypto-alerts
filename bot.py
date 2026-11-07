import os
import time
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SENDER_EMAIL = os.getenv("GMAIL_USER")         
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASS") 
RECEIVER_EMAIL = os.getenv("GMAIL_USER")      

TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']

def get_filtered_mexc_futures_symbols():
    url = "https://contract.mexc.com/api/v1/contract/detail"
    try:
        res = requests.get(url, timeout=10).json()
        if not res.get("success") or "data" not in res:
            return ["XAU_USDT", "USOIL_USDT", "BTC_USDT", "ETH_USDT", "SOL_USDT"]

        symbol_volumes = []
        for item in res["data"]:
            symbol = item.get("symbol")
            if not symbol or not symbol.endswith("_USDT"):
                continue
            volume = float(item.get("volume24", 0) or item.get("amount24", 0) or 0)
            symbol_volumes.append({"symbol": symbol, "volume": volume})

        if not symbol_volumes:
            return ["XAU_USDT", "USOIL_USDT", "BTC_USDT"]

        symbol_volumes.sort(key=lambda x: x["volume"], reverse=True)
        permanent_symbols = ["XAU_USDT", "USOIL_USDT", "BTC_USDT"]
        other_symbols = [s["symbol"] for s in symbol_volumes if s["symbol"] not in permanent_symbols]
        
        # Updated to Top 50 High-Volume Symbols
        top_50_symbols = other_symbols[:50]

        final_symbols = list(dict.fromkeys(permanent_symbols + top_50_symbols))
        print(f"Selected Permanent + Top 50 High-Volume Symbols. Total: {len(final_symbols)}")
        return final_symbols

    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return ["XAU_USDT", "USOIL_USDT", "BTC_USDT", "ETH_USDT", "SOL_USDT"]

def get_klines(symbol, interval, limit=100):
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}"
    tf_map = {
        '1m': 'Min1', '3m': 'Min3', '5m': 'Min5', 
        '15m': 'Min15', '30m': 'Min30', '1h': 'Min60', 
        '4h': 'Hour4', '1d': 'Day1'
    }
    params = {'interval': tf_map.get(interval, 'Min5')}
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("success") and "data" in res:
            data = res["data"]
            closes = np.array(data["close"], dtype=float)
            highs = np.array(data["high"], dtype=float)
            lows = np.array(data["low"], dtype=float)
            opens = np.array(data["open"], dtype=float)
            times = np.array(data["time"], dtype=int)
            return opens, highs, lows, closes, times
    except Exception as e:
        pass
    return None, None, None, None, None

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return np.zeros_like(closes)
    deltas = np.diff(closes)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(closes)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(closes)):
        delta = deltas[i - 1]
        upval = delta if delta > 0 else 0.
        downval = -delta if delta < 0 else 0.

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)

    return rsi

def find_pivots(arr, order=3):
    peaks = []
    troughs = []
    for i in range(order, len(arr) - order):
        if arr[i] == np.max(arr[i - order:i + order + 1]):
            peaks.append((i, arr[i]))
        if arr[i] == np.min(arr[i - order:i + order + 1]):
            troughs.append((i, arr[i]))
    return peaks, troughs

def detect_shape_patterns(arr, times):
    if len(arr) < 35:
        return None, None, ("-", "-"), False

    last_idx = len(arr) - 1
    bullish_pattern = None
    bearish_pattern = None
    p_idx = None

    peaks, troughs = find_pivots(arr, order=3)
    if not peaks and not troughs:
        return None, None, ("-", "-"), False

    if troughs:
        if len(troughs) >= 2:
            t1, t2 = troughs[-2][1], troughs[-1][1]
            if abs(t1 - t2) / (t1 if t1 != 0 else 1) < 0.05:
                p_idx = troughs[-1][0]
                if len(troughs) >= 3 and abs(troughs[-3][1] - t1) / (t1 if t1 != 0 else 1) < 0.05:
                    bullish_pattern = "Triple Bottom"
                else:
                    bullish_pattern = "Double Bottom"

        if not bullish_pattern and len(troughs) >= 3:
            left_t, head_t, right_t = troughs[-3][1], troughs[-2][1], troughs[-1][1]
            if head_t < left_t and head_t < right_t:
                p_idx = troughs[-1][0]
                bullish_pattern = "Inv H&S"

    if peaks:
        if len(peaks) >= 2:
            p1, p2 = peaks[-2][1], peaks[-1][1]
            if abs(p1 - p2) / (p1 if p1 != 0 else 1) < 0.05:
                p_idx = peaks[-1][0]
                if len(peaks) >= 3 and abs(peaks[-3][1] - p1) / (p1 if p1 != 0 else 1) < 0.05:
                    bearish_pattern = "Triple Top"
                else:
                    bearish_pattern = "Double Top"

        if not bearish_pattern and len(peaks) >= 3:
            left_h, head, right_h = peaks[-3][1], peaks[-2][1], peaks[-1][1]
            if head > left_h and head > right_h:
                p_idx = peaks[-1][0]
                bearish_pattern = "H&S"

    if not bullish_pattern and not bearish_pattern:
        return None, None, ("-", "-"), False

    pattern_candle_idx = p_idx if p_idx is not None else last_idx
    karachi_tz = timezone(timedelta(hours=5))
    pattern_ts = times[pattern_candle_idx]
    dt = datetime.fromtimestamp(pattern_ts, tz=timezone.utc).astimezone(karachi_tz)
    
    pattern_time_str = dt.strftime("%I:%M %p")
    pattern_date_str = dt.strftime("%d.%m.%y")
    is_fresh_signal = (last_idx - pattern_candle_idx) <= 3

    return bullish_pattern, bearish_pattern, (pattern_time_str, pattern_date_str), is_fresh_signal

def generate_chart_image(symbol, tf, closes, opens, highs, lows, rsi, alert_table_text, file_path="chart.png"):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 12), gridspec_kw={'height_ratios': [2, 1]})
    
    x = np.arange(len(closes[-30:]))
    o = opens[-30:]
    c = closes[-30:]
    h = highs[-30:]
    l = lows[-30:]
    
    for idx, val in enumerate(x):
        color = '#26a69a' if c[idx] >= o[idx] else '#ef5350'
        ax1.plot([val, val], [l[idx], h[idx]], color=color, linewidth=1)
        ax1.bar(val, abs(c[idx] - o[idx]), bottom=min(o[idx], c[idx]), color=color, width=0.6)

    ax1.set_title(f"MEXC Futures | {symbol} ({tf})", color='white', fontsize=12, fontweight='bold', loc='left')
    ax1.set_facecolor('#131722')
    ax1.tick_params(colors='white')
    ax1.grid(True, color='#2a2e39', alpha=0.5)

    # Yellow RSI Line (No extra EMA)
    ax2.plot(x, rsi[-30:], color='#ffd700', linewidth=2, label="RSI (14)")
    ax2.axhline(70, color='#ef5350', linestyle='--', alpha=0.7)
    ax2.axhline(30, color='#26a69a', linestyle='--', alpha=0.7)
    ax2.fill_between(x, rsi[-30:], 70, where=(rsi[-30:] >= 70), color='#ef5350', alpha=0.15)
    ax2.fill_between(x, rsi[-30:], 30, where=(rsi[-30:] <= 30), color='#26a69a', alpha=0.15)
    
    ax2.set_facecolor('#131722')
    ax2.tick_params(colors='white')
    ax2.grid(True, color='#2a2e39', alpha=0.5)
    ax2.legend(loc="upper left", facecolor='#131722', labelcolor='white')

    # Detailed Table Overlay at bottom with separate RSI Shape columns
    fig.text(0.03, 0.01, alert_table_text, family='monospace', fontsize=7.5, color='white', 
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#131722', edgecolor='#2a2e39', linewidth=1.5))

    fig.patch.set_facecolor('#131722')
    plt.tight_layout(rect=[0, 0.25, 1, 1])
    plt.savefig(file_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
    plt.close()

def send_discord_alert(image_path):
    if DISCORD_WEBHOOK_URL:
        try:
            with open(image_path, 'rb') as f:
                requests.post(DISCORD_WEBHOOK_URL, files={"file": f})
        except Exception as e:
            print(f"Discord Alert Error: {e}")

def send_gmail_alert(image_path="alert_chart.png"):
    if SENDER_EMAIL and SENDER_PASSWORD and RECEIVER_EMAIL:
        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECEIVER_EMAIL
            msg['Subject'] = f"🚨 MEXC Futures Pattern & RSI Alert"
            
            msg.attach(MIMEText("", 'plain'))

            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                img = MIMEImage(img_data, name=os.path.basename(image_path))
                msg.attach(img)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            print("Gmail alert sent successfully with chart image only!")
        except Exception as e:
            print(f"Gmail Alert Error: {e}")

def main():
    symbols = get_filtered_mexc_futures_symbols()
    print(f"Scanning total {len(symbols)} selected MEXC Futures Symbols...")

    for symbol in symbols:
        tf_results = {}
        has_fresh_trigger = False
        sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, sample_tf = None, None, None, None, None, None

        for tf in TIMEFRAMES:
            opens, highs, lows, closes, times = get_klines(symbol, tf)
            if closes is None or len(closes) < 35:
                tf_results[tf] = {"time": "-", "date": "-", "bull_rsi": "-", "bull_pat": "-", "bear_rsi": "-", "bear_pat": "-", "status": "Passive"}
                continue

            rsi = calculate_rsi(closes)
            
            # 1. Check Chart Pattern (Price)
            res_p = detect_shape_patterns(closes, times)
            p_bull, p_bear, (p_time, p_date), p_fresh = res_p if res_p else (None, None, ("-", "-"), False)
            
            # 2. Check RSI Shape Pattern
            res_r = detect_shape_patterns(rsi, times)
            r_bull, r_bear, _, r_fresh = res_r if res_r else (None, None, ("-", "-"), False)

            bull_rsi_str = r_bull if r_bull else "-"
            bull_pat_str = p_bull if p_bull else "-"
            bear_rsi_str = r_bear if r_bear else "-"
            bear_pat_str = p_bear if p_bear else "-"

            is_any_pattern = (p_bull or p_bear or r_bull or r_bear)
            is_any_fresh = (p_fresh or r_fresh)

            status_str = "Passive"
            if is_any_pattern:
                status_str = "Triggered" if is_any_fresh else "Active"
                tf_results[tf] = {
                    "time": p_time if p_time != "-" else (r_time if 'r_time' in locals() and r_time != "-" else "12:00 PM"),
                    "date": p_date if p_date != "-" else "31.10.26",
                    "bull_rsi": bull_rsi_str,
                    "bull_pat": bull_pat_str,
                    "bear_rsi": bear_rsi_str,
                    "bear_pat": bear_pat_str,
                    "status": status_str
                }
                if is_any_fresh:
                    has_fresh_trigger = True
                    sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, sample_tf = closes, opens, highs, lows, rsi, tf
            else:
                tf_results[tf] = {"time": "-", "date": "-", "bull_rsi": "-", "bull_pat": "-", "bear_rsi": "-", "bear_pat": "-", "status": "Scanning" if is_any_fresh else "Passive"}

            time.sleep(0.05)

        if has_fresh_trigger:
            table_lines = [
                "TEXT DETAILS ALERT",
                "--------------------------------------------------------------------------------------------------------------------------------------------------------",
                f"{'T.F.':<6} | {'Time':<10} | {'Date':<10} | {'Bull. RSI Shape':<18} | {'Bullish Pattern Name':<22} | {'Bear. RSI Shape':<18} | {'Bearish Pattern Name':<22} | {'Status'}",
                "--------------------------------------------------------------------------------------------------------------------------------------------------------"
            ]
            
            for tf in TIMEFRAMES:
                res = tf_results[tf]
                table_lines.append(f"{tf:<6} | {res['time']:<10} | {res['date']:<10} | {res['bull_rsi']:<18} | {res['bull_pat']:<22} | {res['bear_rsi']:<18} | {res['bear_pat']:<22} | {res['status']}")
            
            table_lines.append("--------------------------------------------------------------------------------------------------------------------------------------------------------")
            alert_text_table = "\n".join(table_lines)

            chart_file = "alert_chart.png"
            generate_chart_image(symbol, sample_tf, sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, alert_text_table, chart_file)

            send_discord_alert(chart_file)
            send_gmail_alert(chart_file)
            print(f"Picture-only Alert Sent for {symbol} with Top 50 symbols!")

        time.sleep(0.2)

if __name__ == "__main__":
    main()
