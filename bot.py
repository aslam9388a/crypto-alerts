import os
import requests
import pandas as pd
import pandas_ta as ta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# GitHub Secrets se credentials load karna
DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS")

def send_discord_alert(message):
    if DISCORD_URL:
        payload = {"content": message}
        requests.post(DISCORD_URL, json=payload)

def send_email_alert(subject, body):
    if GMAIL_USER and GMAIL_PASS:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
            server.quit()
        except Exception as e:
            print(f"Email error: {e}")

def check_rsi():
    # MEXC Public API se BTC/USDT 5m K-line data
    api_url = "https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=100"
    try:
        response = requests.get(api_url)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['close'] = df['close'].astype(float)
            
            # RSI Indicator (Period: 14)
            df['rsi'] = ta.rsi(df['close'], length=14)
            latest_rsi = df['rsi'].iloc[-1]
            
            msg = f"📊 MEXC BTC/USDT Current RSI (5m): {latest_rsi:.2f}"
            print(msg)
            
            # RSI Condition Verification
            if latest_rsi < 30:
                alert_msg = f"🚨 OVERSOLD ALERT! BTC/USDT RSI is {latest_rsi:.2f} (Below 30)"
                send_discord_alert(alert_msg)
                send_email_alert("MEXC RSI Oversold Alert", alert_msg)
            elif latest_rsi > 70:
                alert_msg = f"🚨 OVERBOUGHT ALERT! BTC/USDT RSI is {latest_rsi:.2f} (Above 70)"
                send_discord_alert(alert_msg)
                send_email_alert("MEXC RSI Overbought Alert", alert_msg)
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    check_rsi()
