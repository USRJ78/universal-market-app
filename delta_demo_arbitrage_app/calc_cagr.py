import numpy as np

# CAGR = (Ending / Beginning) ** (1 / n) - 1

def calc_cagr(tot_ret_pct, years):
    end_val = 1.0 + (tot_ret_pct / 100.0)
    cagr = (end_val ** (1.0 / years)) - 1.0
    return cagr * 100

print("Time Warp 7d/21d ATM:")
print(f"  NIFTY (14 years): {calc_cagr(1399.2, 14):.2f}%")
print(f"  BTC (9 years):    {calc_cagr(1501.5, 9):.2f}%")
print(f"  GOLD (9 years):   {calc_cagr(932.2, 9):.2f}%")

print("\nJulia Set 6.18% Escape:")
print(f"  NIFTY (14 years): {calc_cagr(1232.2, 14):.2f}%")
print(f"  BTC (9 years):    {calc_cagr(1755.5, 9):.2f}%")
print(f"  GOLD (9 years):   {calc_cagr(976.4, 9):.2f}%")
