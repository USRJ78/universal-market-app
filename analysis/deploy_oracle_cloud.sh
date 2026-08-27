#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD ALWAYS FREE TIER — 24/7 AUTOMATED DEPLOYMENT SCRIPT V3.0
# ==============================================================================
#   Deploys both Antigravity Trading Agent & ChronoPulse Time Tracker Web App
#   Run this single command on your Oracle Cloud VM (Ubuntu / Ampere A1):
#   chmod +x deploy_oracle_cloud.sh && ./deploy_oracle_cloud.sh
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ORACLE CLOUD 24/7 DEPLOYMENT — CHRONOPULSE & ANTIGRAVITY AI BRAIN"
echo "==========================================================================="

# 1. Update System Packages & Install Dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx systemd build-essential curl ufw iptables-persistent

# 2. Install Rust Toolchain for HFT Math Solvers
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env

# 3. Create Virtual Environment & Install Python Dependencies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install numpy pandas yfinance ccxt scipy reportlab matplotlib requests

# 4. Create Systemd Service for ChronoPulse Time Tracker Web App
sudo bash -c 'cat <<EOF > /etc/systemd/system/chronopulse_time_tracker.service
[Unit]
Description=ChronoPulse Time and Activity Tracker Web App Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/universal-market-app
ExecStart=/home/ubuntu/universal-market-app/venv/bin/python analysis/time_tracker_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

# 5. Create Systemd Service for Autonomous AI Trading Agent
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

# 6. Reload & Enable Services
sudo systemctl daemon-reload
sudo systemctl enable chronopulse_time_tracker
sudo systemctl restart chronopulse_time_tracker
sudo systemctl enable antigravity_ai_agent
sudo systemctl restart antigravity_ai_agent

# 7. Configure Oracle Firewall & IPTables Port 8050
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8050 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save

# 8. Configure Nginx Web Server
sudo bash -c 'cat <<EOF > /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF'

sudo nginx -t && sudo systemctl restart nginx

PUBLIC_IP=$(curl -s ifconfig.me)

echo "==========================================================================="
echo "  🏆 ORACLE CLOUD 24/7 DEPLOYMENT COMPLETE!"
echo "==========================================================================="
echo "  [PUBLIC ORACLE IP]           : http://$PUBLIC_IP"
echo "  [DIRECT TIME TRACKER PORT]   : http://$PUBLIC_IP:8050"
echo "==========================================================================="
echo "  Your ChronoPulse Time Tracker is now running 24/7 on Oracle Cloud!"
