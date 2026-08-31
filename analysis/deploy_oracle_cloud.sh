#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD ALWAYS FREE TIER — 24/7 AUTOMATED DEPLOYMENT SCRIPT V2.0
# ==============================================================================
#   Run this single command on your Oracle Cloud VM (Ubuntu / Ampere A1):
#   chmod +x deploy_oracle_cloud.sh && ./deploy_oracle_cloud.sh
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ORACLE CLOUD 24/7 DEPLOYMENT — ANTIGRAVITY AI BRAIN V2.0"
echo "==========================================================================="

# 1. Update System Packages & Install Dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx systemd build-essential curl

# 2. Install Rust Toolchain for HFT Math Solvers
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env

# 3. Create Virtual Environment & Install Python Dependencies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install numpy pandas yfinance ccxt scipy reportlab matplotlib requests

# 4. Compile Native Rust LLVM Core Engine
cd rust_1000pct_engine && cargo build --release && cd ..
cd rust_delta_live_arb && cargo build --release && cd ..

# 5. Create Systemd Service for Autonomous AI LLM Trading Agent
sudo bash -c 'cat <<EOF > /etc/systemd/system/antigravity_ai_agent.service
[Unit]
Description=Antigravity AI Brain Autonomous Trading Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/universal-market-app
ExecStart=/home/ubuntu/universal-market-app/venv/bin/python analysis/autonomous_quant_llm_agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

# 6. Enable & Start Systemd Service
sudo systemctl daemon-reload
sudo systemctl enable antigravity_ai_agent
sudo systemctl restart antigravity_ai_agent

echo "==========================================================================="
echo "  🏆 ORACLE CLOUD 24/7 TRADING DEPLOYMENT COMPLETE!"
echo "==========================================================================="
