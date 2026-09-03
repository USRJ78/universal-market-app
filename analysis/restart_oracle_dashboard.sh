#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD — HARD RESTART & V10 DASHBOARD ACTIVATION SCRIPT V4.0
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ACTIVATING AUTONOMOUS QUANT DASHBOARD ON ORACLE CLOUD"
echo "==========================================================================="

# 1. Kill any stale old dashboard processes
echo "  [1/6] Stopping old dashboard server processes..."
sudo pkill -9 -f dashboard_server.py 2>/dev/null || true
sudo systemctl stop antigravity_dashboard 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

# 2. Ensure virtualenv has Flask and required dependencies
echo "  [2/6] Checking Python virtual environment dependencies..."
cd /home/ubuntu/universal-market-app
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install flask numpy pandas yfinance ccxt requests scikit-learn matplotlib --quiet

# 3. Test Dashboard Server syntax and import
echo "  [3/6] Testing Dashboard Server Module Imports..."
python3 -c "import analysis.dashboard_server; print('  [✓] Dashboard Module Verification Passed!')"

# 4. Create & Enable Systemd Service for Port 8080
echo "  [4/6] Updating Systemd Service..."
sudo bash -c 'cat <<EOF > /etc/systemd/system/antigravity_dashboard.service
[Unit]
Description=Antigravity AI Brain Master Web Dashboard (Port 8080)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/universal-market-app
Environment=PYTHONPATH=/home/ubuntu/universal-market-app
ExecStart=/home/ubuntu/universal-market-app/venv/bin/python analysis/dashboard_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF'

# 5. Open IPTables & UFW Firewall Ports (8080 & 80)
echo "  [5/6] Opening Firewall Ports (8080 & 80)..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo ufw allow 8080/tcp 2>/dev/null || true
sudo ufw allow 80/tcp 2>/dev/null || true

# 6. Configure Nginx Reverse Proxy
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

# 7. Start Dashboard Service & Nginx
echo "  [6/6] Launching Master Web Dashboard V3.6..."
sudo systemctl daemon-reload
sudo systemctl enable antigravity_dashboard
sudo systemctl restart antigravity_dashboard
sudo systemctl restart nginx

sleep 2

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "140.245.195.162")

echo "==========================================================================="
echo "  🏆 SUCCESS! AUTONOMOUS QUANT DASHBOARD IS LIVE ON ORACLE CLOUD!"
echo "==========================================================================="
echo "  [PUBLIC MAIN URL]            : http://$PUBLIC_IP"
echo "  [DIRECT DASHBOARD PORT 8080] : http://$PUBLIC_IP:8080"
echo "  [AUTONOMOUS PAGE URL]        : http://$PUBLIC_IP/autonomous-intelligence"
echo "==========================================================================="

echo "\n  📡 Checking Service Journal Logs:"
sudo journalctl -u antigravity_dashboard -n 15 --no-pager
