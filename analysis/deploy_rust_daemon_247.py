"""
==============================================================================
  CONTINUOUS CLOUD DAEMON MANAGER: RUST QUANTUM TRADING ENGINES
==============================================================================
  Author: Uday Singh Rathore (@USRJ78) & @goforaditya
  Manages continuous 24/7 background deployment for:
  1. Kinetic Hyper-Surge Rust Engine V7.0 (+1000% CAGR Target Strategy)
  2. Live High-Frequency Rust Arbitrage Engine V2.0 (Delta Testnet / Demo)
==============================================================================
"""

import os, sys, time, datetime, subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUST_1000_DIR = os.path.join(ROOT_DIR, "rust_1000pct_engine")
RUST_ARB_DIR = os.path.join(ROOT_DIR, "rust_delta_live_arb")

def verify_binaries():
    print("=" * 80)
    print("  🚀 CONTINUOUS CLOUD DAEMON MANAGER -- RUST QUANTUM ENGINES")
    print("=" * 80)
    
    bin_1000 = os.path.join(RUST_1000_DIR, "target", "release", "rust_1000pct_engine.exe")
    bin_arb = os.path.join(RUST_ARB_DIR, "target", "release", "rust_delta_live_arb.exe")

    print(f"  [CHECK] Engine 1 Binary (+1000% CAGR Strategy) : {bin_1000}")
    print(f"          Exists: {os.path.exists(bin_1000)}")
    print(f"  [CHECK] Engine 2 Binary (Live Rust Arbitrage)   : {bin_arb}")
    print(f"          Exists: {os.path.exists(bin_arb)}")
    print("=" * 80)

    return bin_1000, bin_arb

def run_continuous_daemon():
    bin_1000, bin_arb = verify_binaries()

    print("\n  [DAEMON ACTIVE] Launching 24/7 Continuous Quant Monitoring Loop...\n")

    cycle = 0
    while True:
        cycle += 1
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"  [{now_str}] CLOUD DAEMON CYCLE #{cycle}")

        # 1. Run Live Rust Arbitrage Engine Cycle
        if os.path.exists(bin_arb):
            print("    ⚡ Executing Live Rust Arbitrage Engine V2.0...")
            try:
                res = subprocess.run([bin_arb], capture_output=True, text=True, timeout=60)
                output_lines = res.stdout.strip().split("\n")
                for line in output_lines[-5:]:
                    print(f"       | {line}")
            except Exception as e:
                print(f"       [NOTICE] Arbitrage Execution: {e}")

        # 2. Run Kinetic Hyper-Surge Engine Cycle
        if os.path.exists(bin_1000):
            print("    🚀 Executing Kinetic Hyper-Surge Engine V7.0...")
            try:
                res = subprocess.run([bin_1000], capture_output=True, text=True, timeout=60)
                output_lines = res.stdout.strip().split("\n")
                for line in output_lines[-5:]:
                    print(f"       | {line}")
            except Exception as e:
                print(f"       [NOTICE] Hyper-Surge Execution: {e}")

        print(f"  [{now_str}] CYCLE #{cycle} COMPLETE. Sleeping 30s before next tick...\n")
        time.sleep(30)

if __name__ == "__main__":
    run_continuous_daemon()
