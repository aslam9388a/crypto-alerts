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
            return opens, highs, lows, closes
    except Exception as e:
        pass
    return None, None, None, None

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

# --- RSI PATTERN DETECTION LOGIC ---
def detect_rsi_patterns(closes, highs, lows, rsi):
    if len(rsi) < 30:
        return None, None

    curr_rsi = rsi[-1]
    is_oversold = curr_rsi < 30 or np.min(rsi[-5:]) < 30
    is_overbought = curr_rsi > 70 or np.max(rsi[-5:]) > 70

    if not (is_oversold or is_overbought):
        return None, None

    bullish_pattern = None
    bearish_pattern = None

    # 1. Failure Swings
    if is_oversold and rsi[-3] < 30 and rsi[-2] > 30 and rsi[-1] > rsi[-2]:
        bullish_pattern = "Bullish Bottom Failure"
    if is_overbought and rsi[-3] > 70 and rsi[-2] < 70 and rsi[-1] < rsi[-2]:
        bearish_pattern = "Bearish Top Failure"

    # 2. Divergences
    if is_oversold:
        if closes[-1] < closes[-5] and rsi[-1] > rsi[-5]:
            bullish_pattern = "Regular Bullish Div"
        elif closes[-1] > closes[-5] and rsi[-1] < rsi[-5]:
            bullish_pattern = "Hidden Bullish Div"

    if is_overbought:
        if closes[-1] > closes[-5] and rsi[-1] < rsi[-5]:
            bearish_pattern = "Regular Bearish Div"
        elif closes[-1] < closes[-5] and rsi[-1] > rsi[-5]:
            bearish_pattern = "Hidden Bearish Div"

    # 3. Double Bottom / Top (W / M Shapes)
    if is_oversold and not bullish_pattern:
        if abs(rsi[-5] - rsi[-1]) < 3 and rsi[-3] > rsi[-5]:
            bullish_pattern = "Double Bottom (W-Shape)"

    if is_overbought and not bearish_pattern:
        if abs(rsi[-5] - rsi[-1]) < 3 and rsi[-3] < rsi[-5]:
            bearish_pattern = "Double Top (M-Shape)"

    # 4. Head & Shoulders
    if is_overbought and not bearish_pattern:
        if rsi[-5] < rsi[-3] and rsi[-1] < rsi[-3]:
            bearish_pattern = "Head & Shoulders"

    if is_oversold and not bullish_pattern:
        if rsi[-5] > rsi[-3] and rsi[-1] > rsi[-3]:
            bullish_pattern = "Inverse Head & Shoulders"

    return bullish_pattern, bearish_pattern

# --- PLOT REAL CHART IMAGE WITH CANDLES & RSI ---
def generate_chart_image(symbol, tf, closes, opens, highs, lows, rsi, file_path="chart.png"):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={'height_ratios': [2, 1]})
    
    # Draw Candlesticks on Price Panel
    x = np.arange(len(closes[-30:]))
    o = opens[-30:]
    c = closes[-30:]
    h = highs[-30:]
    l = lows[-30:]
    
    for idx, val in enumerate(x):
        color = '#26a69a' if c[idx] >= o[idx] else '#ef5350'
        ax1.plot([val, val], [l[idx], h[idx]], color=color, linewidth=1)
        ax1.bar(val, abs(c[idx] - o[idx]), bottom=min(o[idx], c[idx]), color=color, width=0.6)

    ax1.set_title(f"{symbol} ({tf}) - Real Candles & RSI Pattern", color='white', fontsize=12, fontweight='bold')
    ax1.set_facecolor('#131722')
    ax1.tick_params(colors='white')
    ax1.grid(True, color='#2a2e39', alpha=0.5)

    # Draw RSI Line Panel
    ax2.plot(x, rsi[-30:], color='#2962ff', linewidth=2, label="RSI(14)")
    ax2.axhline(70, color='#ef5350', linestyle='--', alpha=0.7)
    ax2.axhline(30, color='#26a69a', linestyle='--', alpha=0.7)
    ax2.fill_between(x, rsi[-30:], 70, where=(rsi[-30:] >= 70), color='#ef5350', alpha=0.2)
    ax2.fill_between(x, rsi[-30:], 30, where=(rsi[-30:] <= 30), color='#26a69a', alpha=0.2)
    
    ax2.set_facecolor('#131722')
    ax2.tick_params(colors='white')
    ax2.grid(True, color='#2a2e39', alpha=0.5)
    ax2.legend(loc="upper left", facecolor='#131722', labelcolor='white')

    fig.patch.set_facecolor('#131722')
    plt.tight_layout()
    plt.savefig(file_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
    plt.close()

# --- ALERT SENDERS ---
def send_discord_alert(symbol, alert_table_text, image_path):
    msg = f"🚨 **RSI PATTERN ALERT DETECTED** 🚨\nSymbol: `{symbol}` (MEXC Futures)\n\n```\n{alert_table_text}\n```"
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
            msg['Subject'] = f"🚨 MEXC Alert: RSI Pattern Detected on {symbol}"
            
            body = f"RSI PATTERN ALERT DETECTED\nSymbol: {symbol} (MEXC Futures)\n\n{alert_table_text}"
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"Gmail alert sent successfully for {symbol}!")
        except Exception as e:
            print(f"Gmail Alert Error (Check App Password): {e}")

# --- MAIN EXECUTION ---
def main():
    # Karachi Time (UTC+5)
    karachi_tz = timezone(timedelta(hours=5))
    now_karachi = datetime.now(karachi_tz)
    current_time_str = now_karachi.strftime("%H:%M")
    current_date_str = now_karachi.strftime("%d.%m.%y")

    symbols = get_mexc_futures_symbols()
    print(f"Scanning {len(symbols)} MEXC Futures Symbols...")

    for symbol in symbols:
        tf_results = {}
        has_any_pattern = False
        sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, sample_tf = None, None, None, None, None, None

        for tf in TIMEFRAMES:
            opens, highs, lows, closes = get_klines(symbol, tf)
            if closes is None or len(closes) < 30:
                tf_results[tf] = ("-", "-")
                continue

            rsi = calculate_rsi(closes)
            bull_pat, bear_pat = detect_rsi_patterns(closes, highs, lows, rsi)

            if bull_pat or bear_pat:
                has_any_pattern = True
                sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, sample_tf = closes, opens, highs, lows, rsi, tf

            tf_results[tf] = (bull_pat if bull_pat else "-", bear_pat if bear_pat else "-")

        if has_any_pattern:
            # Build Text Details Alert Table matching your exact layout
            table_lines = [
                "                                  Text Details Alert                                  ",
                "--------------------------------------------------------------------------------------",
                f"{'T.F':<7} {'Time':<8} {'Date':<11} {'Bulish Pattern Name':<28} {'Bearish Pattern name':<20}",
                "--------------------------------------------------------------------------------------"
            ]
            
            first_row = True
            for tf in TIMEFRAMES:
                bull, bear = tf_results[tf]
                if first_row and (bull != "-" or bear != "-"):
                    table_lines.append(f"{tf:<7} {current_time_str:<8} {current_date_str:<11} {bull:<28} {bear:<20}")
                    first_row = False
                else:
                    # Other timeframes show empty time/date if no active pattern trigger on this check, or keep clean
                    t_val = current_time_str if (bull != "-" or bear != "-") else ""
                    d_val = current_date_str if (bull != "-" or bear != "-") else ""
                    table_lines.append(f"{tf:<7} {t_val:<8} {d_val:<11} {bull:<28} {bear:<20}")
            
            table_lines.append("--------------------------------------------------------------------------------------")
            alert_text_table = "\n".join(table_lines)

            # Generate Real Chart Image with Candles and RSI
            chart_file = "alert_chart.png"
            generate_chart_image(symbol, sample_tf, sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, chart_file)

            # Send Alerts
            send_discord_alert(symbol, alert_text_table, chart_file)
            send_gmail_alert(symbol, alert_text_table)
            print(f"Alert Sent for {symbol}!")

if __name__ == "__main__":
    main()
