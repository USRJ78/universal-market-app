#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD ALWAYS FREE TIER — 24/7 AUTO-DEPLOYMENT SCRIPT
# ==============================================================================
#   Run this single command on your Oracle Cloud VM (Ubuntu / Ampere A1):
#   chmod +x deploy_oracle_cloud.sh && ./deploy_oracle_cloud.sh
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ORACLE CLOUD ALWAYS FREE TIER — SWARM ALPHA V6.0 AUTOMATED DEPLOYMENT"
echo "==========================================================================="

# 1. Update Packages & Install System Dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx systemd

# 2. Set Up Virtual Environment
python3 -m venv venv
source venv/bin/venv/activate
pip install --upgrade pip
pip install numpy pandas yfinance ccxt scipy reportlab matplotlib

# 3. Create Systemd Service for 24/7 Swarm Daemon
sudo bash -c 'cat <<EOF > /etc/systemd/system/swarm_daemon.service
[Unit]
Description=SwarmAlpha V6.0 Autonomous Quant Daemon
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/universal-market-app
ExecStart=/home/ubuntu/universal-market-app/venv/bin/python analysis/run_ouroboros_v6_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

# 4. Enable & Start Systemd Service
sudo systemctl daemon-reload
sudo systemctl enable swarm_daemon
sudo systemctl restart swarm_daemon

# 5. Configure Nginx Web Server for Mobile iPhone Access (Port 80)
sudo bash -c 'cat <<EOF > /etc/nginx/sites-available/swarm_app
server {
    listen 80;
    server_name _;

    location / {
        root /home/ubuntu/universal-market-app/web_app;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
}
EOF'

sudo ln -sf /etc/nginx/sites-available/swarm_app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# 6. Open Firewall Ports 80 & 443
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

echo "==========================================================================="
echo "  ✅ ORACLE CLOUD 24/7 DEPLOYMENT COMPLETE!"
echo "==========================================================================="
echo "  1. Swarm Daemon Service Status : sudo systemctl status swarm_daemon"
echo "  2. iPhone Web App URL          : http://<YOUR_ORACLE_PUBLIC_IP>"
echo "  3. Laptop status requirement   : LAPTOP CAN NOW BE SAFELY SHUT DOWN 24/7!"
echo "==========================================================================="
