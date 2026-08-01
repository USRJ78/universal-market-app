"""
==============================================================================
  SWARM ALPHA V6.0 — MOBILE WEB SERVER & PWA LAUNCHER
==============================================================================
  Hosts the SwarmAlpha Web Dashboard on your local Wi-Fi network (Port 8080)
  so you can open it on iOS/Android smartphones and tap 'Add to Home Screen'.
==============================================================================
"""

import os, sys, socket, http.server, socketserver

# Unbuffered line output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def main():
    port = 8080
    local_ip = get_local_ip()
    web_app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_app")

    os.chdir(web_app_dir)

    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print("=" * 75)
        print("  SWARM ALPHA V6.0 MOBILE WEB SERVER ACTIVE")
        print("=" * 75)
        print(f"  [MOBILE WI-FI URL] : http://{local_ip}:{port}")
        print(f"  [LOCAL LAPTOP URL] : http://localhost:{port}")
        print("=" * 75)
        print("\n  HOW TO OPEN ON MOBILE (iPhone / Android):")
        print(f"  1. Connect your mobile phone to the same Wi-Fi network as this laptop.")
        print(f"  2. Open Safari (iOS) or Chrome (Android) and type:")
        print(f"     http://{local_ip}:{port}")
        print(f"  3. Tap 'Share' -> 'Add to Home Screen' to create a native app icon!\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[OK] Mobile Web Server stopped cleanly.")

if __name__ == "__main__":
    main()
