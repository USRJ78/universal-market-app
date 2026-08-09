import os
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

CSV_PATH = r"C:\Users\USER\OneDrive\Documents\universal-market-app\data\EQUITY_L.csv"
OUTPUT_DIR = r"C:\Users\USER\OneDrive\Documents\universal-market-app\data\nse_historical"

def download_ticker(symbol):
    yf_symbol = f"{symbol}.NS"
    output_file = os.path.join(OUTPUT_DIR, f"{yf_symbol}.parquet")
    
    # Skip if already downloaded
    if os.path.exists(output_file):
        return symbol, "Skipped"
        
    try:
        # Fetch max history
        df = yf.download(yf_symbol, period="max", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if not df.empty:
            df.to_parquet(output_file)
            return symbol, f"Success ({len(df)} rows)"
        else:
            return symbol, "No data"
    except Exception as e:
        return symbol, f"Error: {e}"

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"Reading tickers from {CSV_PATH}...")
    df_equity = pd.read_csv(CSV_PATH)
    
    symbols = df_equity['SYMBOL'].dropna().unique().tolist()
    print(f"Found {len(symbols)} unique symbols. Starting bulk download (period='max')...")
    
    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(download_ticker, sym): sym for sym in symbols}
        
        for i, future in enumerate(as_completed(futures), 1):
            sym = futures[future]
            try:
                result_sym, status = future.result()
                if "Success" in status:
                    success_count += 1
                if i % 100 == 0:
                    print(f"[{i}/{len(symbols)}] Processed {sym}: {status}")
            except Exception as exc:
                print(f"{sym} generated an exception: {exc}")
                
    print(f"\nDownload complete! Successfully downloaded data for {success_count} tickers.")

if __name__ == "__main__":
    main()
