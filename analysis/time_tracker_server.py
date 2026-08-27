"""
==============================================================================
  CHRONOPULSE — TIME & ACTIVITY TRACKER REST API & WEB SERVER
==============================================================================
  Port: 8050
  Serves: web_app/time_tracker/
  API Endpoints:
    GET  /api/logs     -> Returns all logged time entries & current active timer
    POST /api/logs     -> Saves new time log or updates active timer
    DELETE /api/logs/* -> Deletes log entry by ID
    GET  /api/stats    -> Returns category summary & productivity metrics
==============================================================================
"""

import os, sys, json, time, socket, http.server, socketserver
from urllib.parse import parse_qs, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

PORT = 8050
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DIR  = os.path.join(BASE_DIR, "web_app", "time_tracker")
DB_FILE  = os.path.join(DATA_DIR, "time_tracker_db.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(WEB_DIR, exist_ok=True)

def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            "active_timer": None,
            "logs": []
        }
        save_db(data)
        return data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"active_timer": None, "logs": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

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

class TimeTrackerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/logs":
            db = load_db()
            self._send_json(200, db)
        elif path == "/api/stats":
            db = load_db()
            logs = db.get("logs", [])
            categories = {}
            total_duration = 0
            for log in logs:
                cat = log.get("category", "General")
                dur = log.get("duration_seconds", 0)
                categories[cat] = categories.get(cat, 0) + dur
                total_duration += dur

            self._send_json(200, {
                "total_duration_seconds": total_duration,
                "category_breakdown": categories,
                "log_count": len(logs)
            })
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        db = load_db()

        if path == "/api/timer/start":
            db["active_timer"] = {
                "activity": payload.get("activity", "Task"),
                "category": payload.get("category", "Work"),
                "start_time": time.time(),
                "notes": payload.get("notes", "")
            }
            save_db(db)
            self._send_json(200, {"status": "started", "active_timer": db["active_timer"]})

        elif path == "/api/timer/stop":
            active = db.get("active_timer")
            if active:
                now = time.time()
                dur = int(now - active["start_time"])
                log_entry = {
                    "id": int(now * 1000),
                    "activity": active.get("activity", "Task"),
                    "category": active.get("category", "Work"),
                    "start_time": active["start_time"],
                    "end_time": now,
                    "duration_seconds": dur,
                    "notes": payload.get("notes", active.get("notes", ""))
                }
                db["logs"].insert(0, log_entry)
                db["active_timer"] = None
                save_db(db)
                self._send_json(200, {"status": "stopped", "entry": log_entry})
            else:
                self._send_json(400, {"error": "No active timer running"})

        elif path == "/api/logs/manual":
            now = time.time()
            dur = int(payload.get("duration_minutes", 0)) * 60
            log_entry = {
                "id": int(now * 1000),
                "activity": payload.get("activity", "Manual Entry"),
                "category": payload.get("category", "Work"),
                "start_time": now - dur,
                "end_time": now,
                "duration_seconds": dur,
                "notes": payload.get("notes", "")
            }
            db["logs"].insert(0, log_entry)
            save_db(db)
            self._send_json(200, {"status": "created", "entry": log_entry})

        elif path == "/api/logs/clear":
            db["logs"] = []
            db["active_timer"] = None
            save_db(db)
            self._send_json(200, {"status": "cleared"})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/logs/"):
            log_id = path.replace("/api/logs/", "")
            db = load_db()
            db["logs"] = [l for l in db["logs"] if str(l.get("id")) != log_id]
            save_db(db)
            self._send_json(200, {"status": "deleted", "id": log_id})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

def run_server():
    local_ip = get_local_ip()
    with socketserver.TCPServer(("", PORT), TimeTrackerHandler) as httpd:
        print("=" * 75)
        print("  CHRONOPULSE TIME & ACTIVITY TRACKER SERVER IS ACTIVE")
        print("=" * 75)
        print(f"  [LOCAL WEB URL]  : http://localhost:{PORT}")
        print(f"  [MOBILE WI-FI]   : http://{local_ip}:{PORT}")
        print(f"  [DATA FILE]      : {DB_FILE}")
        print("=" * 75)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  [SERVER STOPPED]")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("[TEST MODE] Validating DB initialization...")
        db = load_db()
        print(f"DB initialized. Log count: {len(db['logs'])}")
    else:
        run_server()
