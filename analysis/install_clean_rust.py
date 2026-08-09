"""
==============================================================================
  RUSTUP AUTOMATED CLEAN INSTALLER & METADATA REPAIR
==============================================================================
"""

import os, shutil, subprocess, sys

# Unbuffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

def main():
    print("=" * 75)
    print("  REPAIRING RUSTUP METADATA & FINISHING RUST INSTALLATION")
    print("=" * 75)

    home = os.path.expanduser('~')
    rustup_dir = os.path.join(home, '.rustup')
    cargo_bin = os.path.join(home, '.cargo', 'bin')
    rustup_exe = os.path.join(cargo_bin, 'rustup.exe')

    # Remove corrupted toolchains folder if present
    toolchains_dir = os.path.join(rustup_dir, 'toolchains')
    if os.path.exists(toolchains_dir):
        print(f"  [1] Clearing corrupted toolchains directory: {toolchains_dir}")
        try:
            shutil.rmtree(toolchains_dir)
        except Exception as e:
            print(f"      Note: {e}")

    # Run rustup toolchain install stable --force
    print("  [2] Installing stable Rust toolchain...")
    cmd1 = [rustup_exe, 'toolchain', 'install', 'stable', '--force']
    res1 = subprocess.run(cmd1, capture_output=True, text=True)
    print(res1.stdout or res1.stderr)

    # Run rustup default stable
    print("  [3] Setting stable as default toolchain...")
    cmd2 = [rustup_exe, 'default', 'stable']
    res2 = subprocess.run(cmd2, capture_output=True, text=True)
    print(res2.stdout or res2.stderr)

    # Verify rustc and cargo
    print("  [4] Verifying rustc and cargo installation...")
    rustc_exe = os.path.join(cargo_bin, 'rustc.exe')
    cargo_exe = os.path.join(cargo_bin, 'cargo.exe')

    r1 = subprocess.run([rustc_exe, '--version'], capture_output=True, text=True)
    r2 = subprocess.run([cargo_exe, '--version'], capture_output=True, text=True)

    print(f"  👉 RUSTC VERSION : {r1.stdout.strip() or r1.stderr.strip()}")
    print(f"  👉 CARGO VERSION : {r2.stdout.strip() or r2.stderr.strip()}")
    print("=" * 75)

if __name__ == "__main__":
    main()
