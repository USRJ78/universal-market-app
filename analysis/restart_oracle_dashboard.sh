#!/bin/bash
# ==============================================================================
#   ORACLE CLOUD — HARD RESTART & DASHBOARD ACTIVATION SCRIPT V7.0
# ==============================================================================

echo "==========================================================================="
echo "  🚀 ACTIVATING AUTONOMOUS QUANT DASHBOARD"
echo "==========================================================================="

# 1. Stop everything
echo "  [1] Stopping all services..."
sudo systemctl stop antigravity_dashboard 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true
sleep 2

# 2. Kill any leftover python processes and clear all ports
echo "  [2] Force-killing all python processes..."
sudo pkill -9 -f "python" 2>/dev/null || true
sudo fuser -k -9 8080/tcp 2>/dev/null || true
sudo fuser -k -9 8085/tcp 2>/dev/null || true
sudo fuser -k -9 8086/tcp 2>/dev/null || true
sudo fuser -k -9 9999/tcp 2>/dev/null || true
sleep 3

# 3. Verify all ports are free
echo "  [3] Verifying port 9999 is free..."
if sudo fuser 9999/tcp 2>/dev/null; then
    echo "  ERROR: Port 9999 still in use!"
    sudo fuser -k -9 9999/tcp 2>/dev/null
    sleep 2
fi
echo "  Port 9999 is free."

# 4. Dependencies
echo "  [4] Checking Python dependencies..."
cd /home/ubuntu/universal-market-app
source venv/bin/activate 2>/dev/null || (python3 -m venv venv && source venv/bin/activate)
pip install flask numpy pandas yfinance ccxt requests scikit-learn matplotlib --quiet

# 5. Test import
echo "  [5] Testing module import..."
python3 -c "import analysis.dashboard_server; print('  [OK] Import Passed!')"

# 6. Create Systemd service
echo "  [6] Writing Systemd service..."
sudo bash -c 'cat > /etc/systemd/system/antigravity_dashboard.service << SVCEOF
[Unit]
Description=Antigravity AI Brain Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/universal-market-app
Environment=PYTHONPATH=/home/ubuntu/universal-market-app
ExecStart=/home/ubuntu/universal-market-app/venv/bin/python analysis/dashboard_server.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF'

# 7. Open firewall for port 9999 and 80
echo "  [7] Opening firewall ports..."
sudo iptables -I INPUT 1 -p tcp --dport 9999 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo ufw allow 9999/tcp 2>/dev/null || true
sudo ufw allow 80/tcp 2>/dev/null || true

# 8. Configure Nginx → Port 9999
echo "  [8] Configuring Nginx → Port 9999..."
sudo bash -c 'cat > /etc/nginx/sites-available/default << NGXEOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:9999;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
}
NGXEOF'
sudo nginx -t && sudo systemctl restart nginx

# 9. Start dashboard
echo "  [9] Starting Dashboard Service..."
sudo systemctl daemon-reload
sudo systemctl enable antigravity_dashboard
sudo systemctl start antigravity_dashboard

# 10. Wait and verify
echo "  [10] Waiting 12 seconds for Flask to start..."
sleep 12

echo ""
echo "  📡 Port Check:"
sudo ss -tlnp | grep python || echo "  WARNING: No python process found on any port!"

echo ""
echo "  📡 Live HTTP Check on Port 9999:"
curl -s -o /dev/null -w "  Flask HTTP Status: %{http_code}\n" http://127.0.0.1:9999/ || echo "  Flask not responding on 9999"

echo ""
echo "  📡 Live HTTP Check through Nginx (Port 80):"
curl -s -o /dev/null -w "  Nginx HTTP Status: %{http_code}\n" http://127.0.0.1:80/ || echo "  Nginx not responding"

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "140.245.195.162")

echo ""
echo "==========================================================================="
echo "  🏆 DEPLOYMENT COMPLETE!"
echo "==========================================================================="
echo "  Main URL   : http://$PUBLIC_IP"
echo "  Direct Port: http://$PUBLIC_IP:9999"
echo "  Autonomous : http://$PUBLIC_IP/autonomous-intelligence"
echo "==========================================================================="

echo ""
echo "  📡 Service Status:"
sudo systemctl status antigravity_dashboard --no-pager | head -15
