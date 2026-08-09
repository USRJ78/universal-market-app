"""
==============================================================================
  RUST EXECUTION DEMO & VERIFICATION SCRIPT
==============================================================================
"""

import os, subprocess, sys

def main():
    home = os.path.expanduser('~')
    cargo_exe = os.path.join(home, '.cargo', 'bin', 'cargo.exe')
    app_dir = r'c:\Users\USER\OneDrive\Documents\universal-market-app\rust_demo'

    os.makedirs(os.path.join(app_dir, 'src'), exist_ok=True)

    cargo_toml = """[package]
name = "rust_demo"
version = "0.1.0"
edition = "2021"

[dependencies]
"""

    main_rs = """fn main() {
    println!("=======================================================================");
    println!("  🚀 RUST QUANT ENGINE ACTIVE — HIGH FREQUENCY TRADING DEMO");
    println!("=======================================================================");
    let spot = 63850.0;
    let target = spot * 1.04;
    println!("  Bitcoin Spot Price : ${:.2}", spot);
    println!("  OTM Target Strike  : ${:.2}", target);
    println!("=======================================================================");
}
"""

    with open(os.path.join(app_dir, 'Cargo.toml'), 'w', encoding='utf-8') as f:
        f.write(cargo_toml)

    with open(os.path.join(app_dir, 'src', 'main.rs'), 'w', encoding='utf-8') as f:
        f.write(main_rs)

    print("=== EXECUTING RUST CODE VIA CARGO RUN ===")
    res = subprocess.run([cargo_exe, 'run'], cwd=app_dir, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("Build Log:\n", res.stderr)

if __name__ == "__main__":
    main()
