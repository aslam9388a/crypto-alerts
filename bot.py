def main():
    # --- QUICK GMAIL TEST ---
    print("Testing Gmail connection...")
    send_gmail_alert("TEST_SYMBOL", "This is a startup test email to verify Gmail configuration.")
    print("Test email sent!")
    # ------------------------

    symbols = get_mexc_futures_symbols()
    print(f"Scanning {len(symbols)} selected MEXC Futures Symbols...")
    
    # (Baaki poora code waise hi rahega)
