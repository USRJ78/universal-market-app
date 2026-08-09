import time
import requests
import json
from datetime import datetime

# Token Addresses on Solana
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL_MINT = "So11111111111111111111111111111111111111112"
BONK_MINT = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
WIF_MINT = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

# Jupiter V6 API
JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"

# Simulation Settings
INITIAL_USDC = 100.0  # Starting with $100
USDC_DECIMALS = 6
SOL_DECIMALS = 9

def log_msg(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", flush=True)

def get_quote(input_mint, output_mint, amount_lamports):
    """Fetch the best route from Jupiter Aggregator."""
    url = f"{JUPITER_QUOTE_API}?inputMint={input_mint}&outputMint={output_mint}&amount={int(amount_lamports)}&slippageBps=50"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        log_msg(f"API Error: {e}")
    return None

def check_arbitrage_cycle(intermediate_token, token_name):
    """
    Simulates a cyclical arbitrage: USDC -> Intermediate -> USDC
    """
    initial_lamports = INITIAL_USDC * (10 ** USDC_DECIMALS)
    
    # Leg 1: USDC -> Intermediate Token
    quote_1 = get_quote(USDC_MINT, intermediate_token, initial_lamports)
    if not quote_1: return
    
    intermediate_amount = int(quote_1['outAmount'])
    
    # Leg 2: Intermediate Token -> USDC
    quote_2 = get_quote(intermediate_token, USDC_MINT, intermediate_amount)
    if not quote_2: return
    
    final_lamports = int(quote_2['outAmount'])
    final_usdc = final_lamports / (10 ** USDC_DECIMALS)
    
    # Calculate Profitability
    profit_usdc = final_usdc - INITIAL_USDC
    # Note: A real bot must account for gas fees (~$0.005) and priority fees (~$0.05).
    # For simulation, we check if raw profit is positive.
    
    route_1 = quote_1['routePlan'][0]['swapInfo']['label']
    route_2 = quote_2['routePlan'][0]['swapInfo']['label']
    
    if profit_usdc > 0.10: # Minimum $0.10 profit to cover simulated fees
        log_msg("==================================================")
        log_msg(f"🚨 ARBITRAGE OPPORTUNITY FOUND via {token_name}!")
        log_msg(f"Route: USDC -> [{route_1}] -> {token_name} -> [{route_2}] -> USDC")
        log_msg(f"Input: ${INITIAL_USDC:.2f} | Output: ${final_usdc:.2f}")
        log_msg(f"Net Profit: +${profit_usdc:.4f}")
        log_msg("==================================================")
    else:
        # Just print a quiet status update
        log_msg(f"Scanning {token_name}... PnL: ${profit_usdc:.4f}")

def run_simulation():
    log_msg("Initializing Flash-Arb Engine (Simulation Mode)...")
    log_msg(f"Starting Capital: ${INITIAL_USDC:.2f} USDC")
    log_msg("Scanning Jupiter Liquidity Pools for Cyclical Arbitrage...\n")
    
    scan_count = 0
    try:
        while True:
            scan_count += 1
            if scan_count % 10 == 0:
                log_msg(f"--- Completed {scan_count} Scans ---")
                
            # Scan high-volatility meme coins and majors for price disjoints
            check_arbitrage_cycle(SOL_MINT, "SOL")
            check_arbitrage_cycle(BONK_MINT, "BONK")
            check_arbitrage_cycle(WIF_MINT, "WIF")
            
            # Sleep briefly to avoid brutal rate limiting from public API
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        log_msg("\nSimulation Stopped by User.")

if __name__ == "__main__":
    run_simulation()
