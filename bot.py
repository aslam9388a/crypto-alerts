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

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

# --- MEXC FUTURES DATA FETCHING ---
def get_mexc_futures_symbols():
    url = "https://contract.mexc.com/api/v1/contract/detail"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("success") and "data" in res:
            return [item["symbol"] for item in res["data"] if item["symbol"].endswith("_USDT")]
    except Exception as e:
        print(f"Error fetching symbols: {e}")
    return ["BTC_USDT", "ETH_USDT", "SOL_USDT"]

def get_klines(symbol, interval, limit=100):
    url = f"https://contract.mexc.com/api/v1/contract/kline/{symbol}"
    tf_map = {'1m': 'Min1', '5m': 'Min5', '15m': 'Min15', '30m': 'Min30', '1h': 'Min60', '4h': 'Hour4', '1d': 'Day1'}
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

# --- RSI CALCULATION ---
def calculate_rsi(closes, period=14):
    deltas = np.diff(closes)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    rs = up/down if down != 0 else 0
    rsi = np.zeros_like(closes)
    rsi[:period] = 100. - 100./(1. + rs)

    for i in range(period, len(closes)):
        delta = deltas[i - 1]
        upval = delta if delta > 0 else 0.
        downval = -delta if delta < 0 else 0.

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1. + rs)

    return rsi

# --- PIVOT FINDER ---
def find_pivots(arr, order=3):
    peaks = []
    troughs = []
    for i in range(order, len(arr) - order):
        if arr[i] == np.max(arr[i - order:i + order + 1]):
            peaks.append((i, arr[i]))
        if arr[i] == np.min(arr[i - order:i + order + 1]):
            troughs.append((i, arr[i]))
    return peaks, troughs

# --- STRICT REAL PATTERN DETECTION ---
def detect_patterns_with_time(closes, highs, lows, rsi, times):
    if len(rsi) < 35:
        return None, None, None, False

    karachi_tz = timezone(timedelta(hours=5))
    last_idx = len(closes) - 1

    is_oversold = rsi[-1] < 30 or np.any(rsi[-3:] < 30)
    is_overbought = rsi[-1] > 70 or np.any(rsi[-3:] > 70)

    if not (is_oversold or is_overbought):
        return None, None, "", False

    bullish_pattern = None
    bearish_pattern = None
    p_idx = None

    peaks, troughs = find_pivots(closes, order=3)
    if not peaks and not troughs:
        return None, None, "", False

    if is_oversold and troughs:
        if len(troughs) >= 2:
            t1, t2 = troughs[-2][1], troughs[-1][1]
            if abs(t1 - t2) / t1 < 0.02:
                p_idx = troughs[-1][0]
                if len(troughs) >= 3 and abs(troughs[-3][1] - t1) / t1 < 0.02:
                    bullish_pattern = "Triple Bottom"
                else:
                    bullish_pattern = "Double Bottom (W-Shape)"

        if not bullish_pattern and len(troughs) >= 3:
            left_t, head_t, right_t = troughs[-3][1], troughs[-2][1], troughs[-1][1]
            if head_t < left_t and head_t < right_t and abs(left_t - right_t) / left_t < 0.03:
                p_idx = troughs[-1][0]
                bullish_pattern = "Inverse Head & Shoulders"

        if not bullish_pattern and len(peaks) >= 2 and len(troughs) >= 2:
            p_slope = peaks[-1][1] - peaks[-2][1]
            t_slope = troughs[-1][1] - troughs[-2][1]
            if p_slope < 0 and t_slope < 0 and abs(p_slope) > abs(t_slope):
                p_idx = troughs[-1][0]
                bullish_pattern = "Falling Wedge"

    if is_overbought and peaks:
        if len(peaks) >= 2:
            p1, p2 = peaks[-2][1], peaks[-1][1]
            if abs(p1 - p2) / p1 < 0.02:
                p_idx = peaks[-1][0]
                if len(peaks) >= 3 and abs(peaks[-3][1] - p1) / p1 < 0.02:
                    bearish_pattern = "Triple Top"
                else:
                    bearish_pattern = "Double Top (M-Shape)"

        if not bearish_pattern and len(peaks) >= 3:
            left_h, head, right_h = peaks[-3][1], peaks[-2][1], peaks[-1][1]
            if head > left_h and head > right_h and abs(left_h - right_h) / left_h < 0.03:
                p_idx = peaks[-1][0]
                bearish_pattern = "Head & Shoulders"

        if not bearish_pattern and len(peaks) >= 2 and len(troughs) >= 2:
            p_slope = peaks[-1][1] - peaks[-2][1]
            t_slope = troughs[-1][1] - troughs[-2][1]
            if p_slope > 0 and t_slope > 0 and t_slope > p_slope:
                p_idx = peaks[-1][0]
                bearish_pattern = "Rising Wedge"

    if not bullish_pattern and not bearish_pattern:
        return None, None, "", False

    pattern_candle_idx = p_idx if p_idx is not None else last_idx
    
    pattern_ts = times[pattern_candle_idx]
    dt = datetime.fromtimestamp(pattern_ts, tz=timezone.utc).astimezone(karachi_tz)
    pattern_time_str = dt.strftime("%H:%M")
    pattern_date_str = dt.strftime("%d.%m.%y")

    is_fresh_signal = (last_idx - pattern_candle_idx) <= 2

    return bullish_pattern, bearish_pattern, (pattern_time_str, pattern_date_str), is_fresh_signal

# --- PLOT CHART IMAGE WITH EMBEDDED TABLE AT THE BOTTOM ---
def generate_chart_image(symbol, tf, closes, opens, highs, lows, rsi, alert_table_text, file_path="chart.png"):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), gridspec_kw={'height_ratios': [2, 1]})
    
    x = np.arange(len(closes[-30:]))
    o = opens[-30:]
    c = closes[-30:]
    h = highs[-30:]
    l = lows[-30:]
    
    for idx, val in enumerate(x):
        color = '#26a69a' if c[idx] >= o[idx] else '#ef5350'
        ax1.plot([val, val], [l[idx], h[idx]], color=color, linewidth=1)
        ax1.bar(val, abs(c[idx] - o[idx]), bottom=min(o[idx], c[idx]), color=color, width=0.6)

    ax1.set_title(f"{symbol} ({tf}) - Real Current Signal Chart", color='white', fontsize=12, fontweight='bold')
    ax1.set_facecolor('#131722')
    ax1.tick_params(colors='white')
    ax1.grid(True, color='#2a2e39', alpha=0.5)

    ax2.plot(x, rsi[-30:], color='#2962ff', linewidth=2, label="RSI(14)")
    ax2.axhline(70, color='#ef5350', linestyle='--', alpha=0.7)
    ax2.axhline(30, color='#26a69a', linestyle='--', alpha=0.7)
    ax2.fill_between(x, rsi[-30:], 70, where=(rsi[-30:] >= 70), color='#ef5350', alpha=0.2)
    ax2.fill_between(x, rsi[-30:], 30, where=(rsi[-30:] <= 30), color='#26a69a', alpha=0.2)
    
    ax2.set_facecolor('#131722')
    ax2.tick_params(colors='white')
    ax2.grid(True, color='#2a2e39', alpha=0.5)
    ax2.legend(loc="upper left", facecolor='#131722', labelcolor='white')

    # Embed Text Details Alert Table directly at the bottom of the chart image
    fig.text(0.05, 0.02, alert_text_text, family='monospace', fontsize=8, color='white', 
             bbox=dict(boxstyle='round', facecolor='#1e222d', edgecolor='#2a2e39'))

    fig.patch.set_facecolor('#131722')
    plt.tight_layout(rect=[0, 0.18, 1, 1])
    plt.savefig(file_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
    plt.close()

# --- ALERT SENDERS ---
def send_discord_alert(symbol, image_path):
    msg = f"🚨 **MEXC FUTURES SIGNAL ALERT** 🚨\nSymbol: `{symbol}`"
    if DISCORD_WEBHOOK_URL:
        try:
            with open(image_path, 'rb') as f:
                requests.post(DISCORD_WEBHOOK_URL, data={"content": msg}, files={"file": f})
        except Exception as e:
            print(f"Discord Alert Error: {e}")

def send_gmail_alert(symbol, alert_table_text):
    if SENDER_EMAIL and SENDER_PASSWORD and RECEIVER_EMAIL:
        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECEIVER_EMAIL
            msg['Subject'] = f"🚨 MEXC Alert: Pattern Detected on {symbol}"
            
            body = f"TEXT DETAILS ALERT\nSymbol: {symbol} (MEXC Futures)\n\n{alert_table_text}"
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"Gmail alert sent successfully for {symbol}!")
        except Exception as e:
            print(f"Gmail Alert Error: {e}")

# --- MAIN EXECUTION ---
def main():
    symbols = get_mexc_futures_symbols()
    print(f"Scanning {len(symbols)} MEXC Futures Symbols...")

    for symbol in symbols:
        tf_results = {}
        has_fresh_trigger = False
        sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, sample_tf = None, None, None, None, None, None

        for tf in TIMEFRAMES:
            opens, highs, lows, closes, times = get_klines(symbol, tf)
            if closes is None or len(closes) < 35:
                tf_results[tf] = {"time": "", "date": "", "bull": "-", "bear": "-"}
                continue

            rsi = calculate_rsi(closes)
            bull_pat, bear_pat, (p_time, p_date), is_fresh = detect_patterns_with_time(closes, highs, lows, rsi, times)

            if bull_pat or bear_pat:
                tf_results[tf] = {
                    "time": p_time,
                    "date": p_date,
                    "bull": bull_pat if bull_pat else "-",
                    "bear": bear_pat if bear_pat else "-"
                }
                if is_fresh:
                    has_fresh_trigger = True
                    sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, sample_tf = closes, opens, highs, lows, rsi, tf
            else:
                tf_results[tf] = {"time": "", "date": "", "bull": "-", "bear": "-"}

        if has_fresh_trigger:
            table_lines = [
                "                                  Text Details Alert                                  ",
                "--------------------------------------------------------------------------------------",
                f"{'T.F':<7} {'Time':<8} {'Date':<11} {'Bulish Pattern Name':<28} {'Bearish Pattern name':<20}",
                "--------------------------------------------------------------------------------------"
            ]
            
            for tf in TIMEFRAMES:
                res = tf_results[tf]
                table_lines.append(f"{tf:<7} {res['time']:<8} {res['date']:<11} {res['bull']:<28} {res['bear']:<20}")
            
            table_lines.append("--------------------------------------------------------------------------------------")
            alert_text_table = "\n".join(table_lines)

            # Generate Chart Image with embedded table at the bottom
            chart_file = "alert_chart.png"
            generate_chart_image(symbol, sample_tf, sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, alert_text_table, chart_file)

            # Send Alerts (Discord gets image with table inside, Gmail gets text table)
            send_discord_alert(symbol, chart_file)
            send_gmail_alert(symbol, alert_text_table)
            print(f"Alert Sent for {symbol}!")

if __name__ == "__main__":
    main()
