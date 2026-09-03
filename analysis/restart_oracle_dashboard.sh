#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD — HARD RESTART & V10 DASHBOARD ACTIVATION SCRIPT
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ACTIVATING ORDER BOOK V10.0 ULTRA & SWARM ON ORACLE CLOUD"
echo "==========================================================================="

# 1. Kill any stale old dashboard processes
echo "  [1/5] Stopping old dashboard server processes..."
sudo pkill -9 -f dashboard_server.py 2>/dev/null || true
sudo systemctl stop antigravity_dashboard 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

# 2. Ensure virtualenv has Flask and required dependencies
echo "  [2/5] Checking Python virtual environment dependencies..."
cd /home/ubuntu/universal-market-app
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install flask numpy pandas yfinance ccxt requests --quiet

# 3. Create & Enable Systemd Service for Port 8080
echo "  [3/5] Updating Systemd Service..."
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

# 4. Open IPTables Port 8080 and Port 80
echo "  [4/5] Opening Firewall Ports (8080 & 80)..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || true

# 5. Configure Nginx Reverse Proxy
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
    }
}
EOF'

# 6. Start Dashboard Service & Nginx
echo "  [5/5] Launching Master Web Dashboard V3.6..."
sudo systemctl daemon-reload
sudo systemctl enable antigravity_dashboard
sudo systemctl restart antigravity_dashboard
sudo systemctl restart nginx

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "140.245.195.162")

echo "==========================================================================="
echo "  🏆 SUCCESS! ORDER BOOK V10.0 ULTRA IS NOW LIVE 24/7 ON ORACLE CLOUD!"
echo "==========================================================================="
echo "  [PUBLIC ORACLE IP]           : http://$PUBLIC_IP"
echo "  [DIRECT DASHBOARD PORT 8080] : http://$PUBLIC_IP:8080"
echo "==========================================================================="
