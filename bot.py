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

# --- CONFIGURATION (Matched with your GitHub Secrets) ---
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SENDER_EMAIL = os.getenv("GMAIL_USER")       # GMAIL_USER mapped to SENDER_EMAIL
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASS") # GMAIL_APP_PASS mapped to SENDER_PASSWORD
RECEIVER_EMAIL = os.getenv("GMAIL_USER")      # Send to yourself or set receiver

TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

# --- CUSTOM SPECIFIC SYMBOLS LIST ---
def get_mexc_futures_symbols():
    symbols = [
        # 1. L1
        "BTC_USDT", "ETH_USDT", "BNB_USDT", "SOL_USDT", "TRX_USDT", "ZEC_USDT", "HYPE_USDT", "XMR_USDT", "ADA_USDT", "NEAR_USDT",
        "BCH_USDT", "LTC_USDT", "AVAX_USDT", "SUI_USDT", "GRAM_USDT", "HBAR_USDT", "TAO_USDT", "CRO_USDT", "ICP_USDT", "ETC_USDT",
        "KAS_USDT", "ALGO_USDT", "FIL_USDT", "INJ_USDT", "APT_USDT", "VET_USDT", "TIA_USDT", "SEI_USDT", "XPL_USDT", "XTZ_USDT",
        "GNO_USDT", "KITE_USDT", "CFX_USDT", "DCR_USDT", "KAIA_USDT", "AR_USDT", "IOTA_USDT", "THETA_USDT", "XEC_USDT", "KAVA_USDT",
        "DUSK_USDT", "ZIG_USDT", "DGB_USDT", "ARC_USDT", "VTHO_USDT", "ROSE_USDT", "S_USDT", "CHZ_USDT", "OG_USDT", "PLUME_USDT",
        "EGLD_USDT", "DYDX_USDT", "GALA_USDT", "ONE_USDT", "BERA_USDT", "ASTR_USDT", "ENJ_USDT", "POLYX_USDT", "SOMI_USDT", "FLOW_USDT",
        "XNO_USDT", "MOVE_USDT", "PARTI_USDT", "WAXP_USDT", "FOGO_USDT", "CHR_USDT", "G_USDT", "HIVE_USDT", "ONG_USDT", "MANTRA_USDT",
        "MOVR_USDT", "SAGA_USDT", "SCRT_USDT", "GLMR_USDT", "BB_USDT", "INIT_USDT", "VANA_USDT", "VANRY_USDT", "SYS_USDT", "SAHARA_USDT",
        "SKL_USDT", "GUN_USDT", "ACA_USDT",
        
        # 2. DeFi coins & Tokenized stocks/ETFs ending with B
        "LINK_USDT", "XLM_USDT", "UNI_USDT", "ENA_USDT", "QNT_USDT", "AAVE_USDT", "PUMP_USDT", "ASTER_USDT", "DOT_USDT", "WLD_USDT",
        "WLFI_USDT", "SKY_USDT", "JST_USDT", "MORPHO_USDT", "RENDER_USDT", "ATOM_USDT", "AERO_USDT", "ZRO_USDT", "CAKE_USDT", "ETHFI_USDT",
        "PYTH_USDT", "CRV_USDT", "RAY_USDT", "BTT_USDT", "STRK_USDT", "PENDLE_USDT", "LDO_USDT", "LUNC_USDT", "GRT_USDT", "CVX_USDT",
        "BAT_USDT", "KMNO_USDT", "COMP_USDT", "JTO_USDT", "FLOKI_USDT", "RUNE_USDT", "EIGEN_USDT", "TRAC_USDT", "MET_USDT", "A_USDT",
        "NEO_USDT", "DEXE_USDT", "1INCH_USDT", "AWE_USDT", "SUPER_USDT", "ORCA_USDT", "ZEN_USDT", "GENIUS_USDT", "RSR_USDT", "FUN_USDT",
        "GMX_USDT", "QTUM_USDT", "ZRX_USDT", "HUMA_USDT", "MINA_USDT", "RED_USDT", "W_USDT", "GAS_USDT", "YFI_USDT", "NMR_USDT",
        "COW_USDT", "SNX_USDT", "BABY_USDT", "TFUEL_USDT", "RE_USDT", "AXL_USDT", "SUSHI_USDT", "WIN_USDT", "SPK_USDT", "NXPC_USDT",
        "ONT_USDT", "TRB_USDT", "XVS_USDT", "RLC_USDT", "BARD_USDT", "ANKR_USDT", "ZIL_USDT", "REQ_USDT", "AVNT_USDT", "REZ_USDT",
        "BAND_USDT", "LISTA_USDT", "AT_USDT", "SYN_USDT", "IOTX_USDT", "WAVES_USDT", "RPL_USDT", "UMA_USDT", "ACX_USDT", "LAYER_USDT",
        "COTI_USDT", "BNT_USDT", "MMT_USDT", "ARKM_USDT", "HYPER_USDT", "CPOOL_USDT", "FLUX_USDT", "KNC_USDT", "EDEN_USDT", "STRAX_USDT",
        "AUCTION_USDT", "DODO_USDT", "IQ_USDT", "HOME_USDT", "API3_USDT", "ZBT_USDT", "CETUS_USDT", "USUAL_USDT", "OGN_USDT", "WOO_USDT",
        "CELR_USDT", "LQTY_USDT", "CGPT_USDT", "BANK_USDT", "EPIC_USDT", "CTK_USDT", "FIDA_USDT", "DIA_USDT", "XAI_USDT", "FIRO_USDT",
        "SPELL_USDT", "QI_USDT", "BICO_USDT", "F_USDT", "ARPA_USDT", "M87_USDT", "C98_USDT", "KERNEL_USDT", "KAT_USDT", "JOE_USDT",
        "ALICE_USDT", "YB_USDT", "POND_USDT", "PORTAL_USDT", "SXT_USDT", "ICX_USDT", "MAV_USDT", "ERA_USDT", "DOLO_USDT", "HAEDAL_USDT",
        "GNS_USDT", "HEI_USDT", "BEL_USDT", "ADX_USDT", "RESOLV_USDT", "BAL_USDT", "QUICK_USDT", "HFT_USDT", "FARM_USDT", "MLN_USDT",
        "PIVX_USDT", "NOM_USDT", "STO_USDT", "THE_USDT", "TREE_USDT", "ALCX_USDT", "ORAI_USDT", "HIGH_USDT", "MITO_USDT", "MBOX_USDT",
        "BBB_USDT", "PERP_USDT", "FIO_USDT",
        
        # Tokenized Stocks/ETFs
        "SNDKB_USDT", "SOXLB_USDT", "INTCB_USDT", "NVDAB_USDT", "GOOGLB_USDT", "BNCB_USDT", "SKHYB_USDT", "TSLAB_USDT", "MUB_USDT", "CRCLB_USDT",
        "SPCXB_USDT", "MSTRB_USDT", "QQQB_USDT", "DRAMB_USDT", "COINB_USDT", "AVGOB_USDT", "SPYB_USDT", "KORUB_USDT", "TQQQB_USDT", "NBISB_USDT",
        "AMDB_USDT", "EWYB_USDT", "BMNRB_USDT", "MUUB_USDT", "TSMB_USDT", "RKLBB_USDT", "AMATB_USDT", "BABAB_USDT", "COHRB_USDT", "MRVLB_USDT",
        "SNXXB_USDT", "HOODB_USDT", "AAPLB_USDT", "ORCLB_USDT", "LITEB_USDT", "MSFTB_USDT", "BEB_USDT", "NFLXB_USDT", "PDDB_USDT", "MRNAB_USDT",
        "CRWVB_USDT", "SOXSB_USDT", "ASTSB_USDT", "ARMB_USDT", "GLWB_USDT", "SMHB_USDT", "USARB_USDT", "DELLB_USDT", "ADBEB_USDT", "PYPLB_USDT",
        "IBMB_USDT", "GSB_USDT", "FLNCB_USDT", "CYPHB_USDT", "LLYB_USDT", "QNTB_USDT", "AMCB_USDT", "STXB_USDT", "ALABB_USDT", "CRDOB_USDT",
        "SHAZB_USDT", "FWDIB_USDT", "GPROB_USDT", "PENGB_USDT", "WENB_USDT", "VSTB_USDT", "TMFB_USDT", "ZMB_USDT", "MDBB_USDT", "BOTB_USDT",
        "JPMB_USDT", "DJTB_USDT", "ASMLB_USDT", "WDCB_USDT", "NOKB_USDT", "PLTRB_USDT", "QCOMB_USDT", "SMCIB_USDT", "GMEB_USDT", "METAB_USDT",
        "IRENB_USDT", "AMZNB_USDT", "CRWDB_USDT", "HIMSB_USDT", "SQQQB_USDT", "CRMB_USDT",

        # Additional Items
        "HOT_USDT", "BANANA_USDT", "LRC_USDT", "FET_USDT", "VIRTUAL_USDT", "SENT_USDT", "GLM_USDT", "CHIP_USDT", "IO_USDT", "KAITO_USDT",
        "TURBO_USDT", "AI_USDT", "HOLO_USDT", "NIL_USDT", "PHA_USDT", "C_USDT", "ALLO_USDT", "ARK_USDT", "OPEN_USDT", "LUNA_USDT",
        "MAGIC_USDT", "OPG_USDT", "BMT_USDT", "AIXBT_USDT", "MIRA_USDT", "NEWT_USDT", "SAPIEN_USDT", "ROBO_USDT", "SHELL_USDT", "SAGA_USDT",
        "ACT_USDT", "PAAL_USDT", "COOKIE_USDT", "LNQ_USDT", "HASHAI_USDT", "HOOK_USDT", "GPU_USDT", "STX_USDT", "AXS_USDT", "MANA_USDT",
        "SAND_USDT", "APE_USDT", "MEGA_USDT", "MASK_USDT", "AVA_USDT", "RIO_USDT", "ILV_USDT", "TLM_USDT", "REEF_USDT", "YGG_USDT",
        "GHST_USDT", "PYR_USDT", "D_USDT", "DOGE_USDT", "SHIB_USDT", "PEPE_USDT", "BONK_USDT", "PENGU_USDT", "TRUMP_USDT", "SPX_USDT",
        "TIBBIR_USDT", "USELESS_USDT", "WIF_USDT", "NPC_USDT", "MUBARAK_USDT", "BOME_USDT", "PNUT_USDT", "PEOPLE_USDT", "FARTCOIN_USDT",
        "MARSCOIN_USDT", "BANANAS31_USDT", "MOODENG_USDT", "NOT_USDT", "MEME_USDT", "GIGGLE_USDT", "NEIRO_USDT", "DOGS_USDT", "TUT_USDT",
        "TST_USDT", "CHILLGUY_USDT", "ONDO_USDT", "CFG_USDT", "ID_USDT", "LSK_USDT", "RVN_USDT", "LUMIA_USDT", "PROPC_USDT", "DASH_USDT",
        "XVG_USDT", "ZKP_USDT", "ANYONE_USDT"
    ]
    return list(dict.fromkeys(symbols))

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

def find_pivots(arr, order=3):
    peaks = []
    troughs = []
    for i in range(order, len(arr) - order):
        if arr[i] == np.max(arr[i - order:i + order + 1]):
            peaks.append((i, arr[i]))
        if arr[i] == np.min(arr[i - order:i + order + 1]):
            troughs.append((i, arr[i]))
    return peaks, troughs

def detect_patterns_with_time(closes, highs, lows, rsi, times):
    if len(rsi) < 35:
        return None, None, ("", ""), False

    karachi_tz = timezone(timedelta(hours=5))
    last_idx = len(closes) - 1

    is_oversold = rsi[-1] < 30 or np.any(rsi[-3:] < 30)
    is_overbought = rsi[-1] > 70 or np.any(rsi[-3:] > 70)

    if not (is_oversold or is_overbought):
        return None, None, ("", ""), False

    bullish_pattern = None
    bearish_pattern = None
    p_idx = None

    peaks, troughs = find_pivots(closes, order=3)
    if not peaks and not troughs:
        return None, None, ("", ""), False

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
                p_idx = troughs[-1][0]
                bearish_pattern = "Rising Wedge"

    if not bullish_pattern and not bearish_pattern:
        return None, None, ("", ""), False

    pattern_candle_idx = p_idx if p_idx is not None else last_idx
    
    pattern_ts = times[pattern_candle_idx]
    dt = datetime.fromtimestamp(pattern_ts, tz=timezone.utc).astimezone(karachi_tz)
    pattern_time_str = dt.strftime("%H:%M")
    pattern_date_str = dt.strftime("%d.%m.%y")

    is_fresh_signal = (last_idx - pattern_candle_idx) <= 2

    return bullish_pattern, bearish_pattern, (pattern_time_str, pattern_date_str), is_fresh_signal

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

    fig.text(0.05, 0.02, alert_table_text, family='monospace', fontsize=8, color='white', 
             bbox=dict(boxstyle='round', facecolor='#1e222d', edgecolor='#2a2e39'))

    fig.patch.set_facecolor('#131722')
    plt.tight_layout(rect=[0, 0.18, 1, 1])
    plt.savefig(file_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
    plt.close()

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

def main():
    # --- STEP 2: STARTUP TEST MESSAGE ---
    print("Sending Startup Test Notification...")
    test_table = (
        "                                  Text Details Alert                                  \n"
        "--------------------------------------------------------------------------------------\n"
        "T.F    Time     Date        Bulish Pattern Name          Bearish Pattern name    \n"
        "--------------------------------------------------------------------------------------\n"
        "5m     12:00    28.10.26    [BOT STARTUP TEST SUCCESS]   -                       \n"
        "--------------------------------------------------------------------------------------"
    )
    # Dummy chart file bna kar test alert bhejna
    fig, ax = plt.subplots(figsize=(6, 2))
    ax.text(0.5, 0.5, "Bot Startup Test Successful!", fontsize=12, ha='center', va='center', color='white')
    fig.patch.set_facecolor('#131722')
    ax.set_facecolor('#131722')
    plt.savefig("startup_test.png", facecolor=fig.get_facecolor())
    plt.close()
    
    send_discord_alert("TEST_BOT", "startup_test.png")
    send_gmail_alert("TEST_BOT", test_table)
    print("Startup Test Notifications Sent!")
    # -------------------------------------

    symbols = get_mexc_futures_symbols()
    print(f"Scanning {len(symbols)} selected MEXC Futures Symbols...")

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

            chart_file = "alert_chart.png"
            generate_chart_image(symbol, sample_tf, sample_closes, sample_opens, sample_highs, sample_lows, sample_rsi, alert_text_table, chart_file)

            send_discord_alert(symbol, chart_file)
            send_gmail_alert(symbol, alert_text_table)
            print(f"Alert Sent for {symbol}!")

if __name__ == "__main__":
    main()
