#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD ALWAYS FREE TIER — 24/7 AUTOMATED DEPLOYMENT SCRIPT V3.6 (FAST)
# ==============================================================================
#   Run this single command on your Oracle Cloud VM (Ubuntu / Ampere A1):
#   chmod +x deploy_oracle_cloud.sh && ./deploy_oracle_cloud.sh
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ORACLE CLOUD 24/7 DEPLOYMENT — ANTIGRAVITY AI BRAIN DASHBOARD V3.6"
echo "==========================================================================="

# 1. Update System Packages & Install Dependencies
sudo apt update -y && sudo apt install -y python3 python3-pip python3-venv git nginx systemd build-essential curl ufw iptables-persistent

# 2. Install/Check Rust Toolchain Fast Path
if ! command -v cargo &> /dev/null; then
    echo "  [+] Installing Rust Toolchain..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
    source $HOME/.cargo/env
else
    echo "  [✓] Rust Toolchain already active!"
    source $HOME/.cargo/env 2>/dev/null || true
fi

# 3. Create Virtual Environment & Install Python Dependencies Fast Path
cd ..
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip --quiet
pip install numpy pandas yfinance ccxt scipy reportlab matplotlib requests flask --quiet

# 4. Fast Compile Native Rust LLVM Core Engine
if [ -d "rust_1000pct_engine" ]; then
    cd rust_1000pct_engine && cargo build --release --quiet && cd ..
fi
if [ -d "rust_orderbook_pattern_miner" ]; then
    cd rust_orderbook_pattern_miner && cargo build --release --quiet && cd ..
fi

# 5. Create Systemd Service for Antigravity AI Brain Master Production Web Dashboard
sudo bash -c 'cat <<EOF > /etc/systemd/system/antigravity_dashboard.service
[Unit]
Description=Antigravity AI Brain Master Web Dashboard (Port 8080)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/universal-market-app
ExecStart=/home/ubuntu/universal-market-app/venv/bin/python analysis/dashboard_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF'

# 6. Create Systemd Service for Autonomous AI Trading Agent
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

# 7. Enable & Start Systemd Services
sudo systemctl daemon-reload
sudo systemctl enable antigravity_dashboard
sudo systemctl restart antigravity_dashboard

# 8. Open Oracle Cloud IPTables Ports (8080 & 80)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || true

# 9. Configure Nginx Reverse Proxy for Port 80 & 8080
sudo bash -c 'cat <<EOF > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF'

sudo nginx -t && sudo systemctl restart nginx

PUBLIC_IP=$(curl -s ifconfig.me)

echo "==========================================================================="
echo "  🏆 ORACLE CLOUD 24/7 ANTIGRAVITY DASHBOARD DEPLOYMENT COMPLETE!"
echo "==========================================================================="
echo "  [PUBLIC ORACLE IP]           : http://$PUBLIC_IP"
echo "  [DIRECT DASHBOARD PORT 8080] : http://$PUBLIC_IP:8080"
echo "==========================================================================="
echo "  Your Antigravity AI Brain Master Web Dashboard is live 24/7 on Oracle Cloud!"
