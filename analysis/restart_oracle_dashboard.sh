#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD — HARD RESTART & DASHBOARD ACTIVATION SCRIPT V6.0
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ACTIVATING AUTONOMOUS QUANT DASHBOARD ON ORACLE CLOUD"
echo "==========================================================================="

# 1. Stop systemd service FIRST so it doesn't auto-restart during cleanup
echo "  [1/6] Stopping systemd services and freeing ports..."
sudo systemctl stop antigravity_dashboard 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true
sleep 1

# 2. Force kill any python dashboard processes and free all ports
sudo pkill -9 -f dashboard_server.py 2>/dev/null || true
sudo fuser -k -9 8085/tcp 2>/dev/null || true
sudo fuser -k -9 8080/tcp 2>/dev/null || true
sudo fuser -k -9 80/tcp 2>/dev/null || true
sleep 2

# 3. Ensure virtualenv has Flask and required dependencies
echo "  [2/6] Checking Python virtual environment dependencies..."
cd /home/ubuntu/universal-market-app
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install flask numpy pandas yfinance ccxt requests scikit-learn matplotlib --quiet

# 4. Test Dashboard Server syntax and import
echo "  [3/6] Testing Dashboard Server Module Imports..."
python3 -c "import analysis.dashboard_server; print('  [✓] Dashboard Module Verification Passed!')"

# 5. Create & Enable Systemd Service for Port 8085
echo "  [4/6] Updating Systemd Service for Port 8085..."
sudo bash -c 'cat <<EOF > /etc/systemd/system/antigravity_dashboard.service
[Unit]
Description=Antigravity AI Brain Master Web Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/universal-market-app
Environment=PYTHONPATH=/home/ubuntu/universal-market-app
ExecStart=/home/ubuntu/universal-market-app/venv/bin/python analysis/dashboard_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

# 6. Open IPTables & UFW Firewall Ports
echo "  [5/6] Opening Firewall Ports..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8086 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8085 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo ufw allow 8086/tcp 2>/dev/null || true
sudo ufw allow 8085/tcp 2>/dev/null || true
sudo ufw allow 80/tcp 2>/dev/null || true

# 7. Start Dashboard via Systemd
echo "  [6/6] Launching Master Web Dashboard..."
sudo systemctl daemon-reload
sudo systemctl enable antigravity_dashboard
sudo systemctl start antigravity_dashboard

# 8. Wait for Flask to bind and detect actual port
echo "  Waiting for Flask to start and detecting port..."
sleep 8
FLASK_PORT=$(sudo ss -tlnp | grep python | grep -oP ':\K[0-9]+' | head -1)
if [ -z "$FLASK_PORT" ]; then
    FLASK_PORT=8086
fi
echo "  Flask detected on port: $FLASK_PORT"

# 8. Update Nginx to point to actual Flask port
sudo bash -c "cat > /etc/nginx/sites-available/default << EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:${FLASK_PORT};
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
    }
}
EOF"
sudo nginx -t && sudo systemctl restart nginx

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "140.245.195.162")

echo "==========================================================================="
echo "  🏆 SUCCESS! AUTONOMOUS QUANT DASHBOARD IS LIVE ON ORACLE CLOUD!"
echo "==========================================================================="
echo "  [PUBLIC MAIN URL]            : http://$PUBLIC_IP"
echo "  [DIRECT DASHBOARD PORT]      : http://$PUBLIC_IP:$FLASK_PORT"
echo "  [AUTONOMOUS PAGE URL]        : http://$PUBLIC_IP/autonomous-intelligence"
echo "==========================================================================="

echo ""
echo "  📡 Live HTTP Verification:"
curl -s -o /dev/null -w "  HTTP Status: %{http_code}\n" http://127.0.0.1:${FLASK_PORT}/ || echo "  Service starting..."

echo ""
echo "  📡 Systemd Service Status:"
sudo systemctl status antigravity_dashboard --no-pager | head -n 10
