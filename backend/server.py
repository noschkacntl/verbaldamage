"""Small, dependency-free HTTP API for Verbal Damage."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

DB_PATH = os.environ.get("DATABASE_PATH", "/data/verbal-damage.sqlite3")
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGIN", "http://kackhost.lan").rstrip("/")
USERS = [
    {"id": "user1", "name": os.environ.get("USER_ONE", "User 1")[:60]},
    {"id": "user2", "name": os.environ.get("USER_TWO", "User 2")[:60]},
]
LIMIT = 1


def connect():
    db = sqlite3.connect(DB_PATH, timeout=5)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS insults (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL CHECK(sender IN ('user1','user2')),
            recipient TEXT NOT NULL CHECK(recipient IN ('user1','user2')),
            message TEXT NOT NULL CHECK(length(message) BETWEEN 1 AND 500),
            created_at TEXT NOT NULL,
            month TEXT NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS insults_month_sender ON insults(month, sender)")


def current_month():
    return datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m")


class Handler(BaseHTTPRequestHandler):
    server_version = "VerbalDamage/1.0"

    def log_message(self, _format, *_args):
        pass

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def send_cors(self):
        if self.headers.get("Origin", "").rstrip("/") == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {"ok": True})
        elif path == "/api/state":
            month = current_month()
            with connect() as db:
                rows = db.execute("SELECT sender, COUNT(*) AS used FROM insults WHERE month = ? GROUP BY sender", (month,)).fetchall()
                used = {row["sender"]: row["used"] for row in rows}
                insults = db.execute("SELECT id, sender, recipient, message, created_at, month FROM insults ORDER BY id DESC").fetchall()
            self.send_json(200, {
                "month": month,
                "limit": LIMIT,
                "users": [{**u, "used": used.get(u["id"], 0), "remaining": max(0, LIMIT - used.get(u["id"], 0))} for u in USERS],
                "insults": [dict(row) for row in insults],
            })
        else:
            self.send_json(404, {"error": "Nicht gefunden."})

    def do_POST(self):
        if urlparse(self.path).path != "/api/insults":
            self.send_json(404, {"error": "Nicht gefunden."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 8192:
                raise ValueError
            payload = json.loads(self.rfile.read(length))
            sender = payload.get("sender")
            message = payload.get("message", "")
            if sender not in ("user1", "user2") or not isinstance(message, str):
                raise ValueError
            message = message.strip()
            if not message or len(message) > 500:
                self.send_json(400, {"error": "Bitte eine Notiz mit 1 bis 500 Zeichen eingeben."})
                return
        except (ValueError, json.JSONDecodeError, AttributeError):
            self.send_json(400, {"error": "Ungültige Anfrage."})
            return

        recipient = "user2" if sender == "user1" else "user1"
        month = current_month()
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with connect() as db:
                db.execute("BEGIN IMMEDIATE")
                count = db.execute("SELECT COUNT(*) FROM insults WHERE sender = ? AND month = ?", (sender, month)).fetchone()[0]
                if count >= LIMIT:
                    db.rollback()
                    self.send_json(409, {"error": "Für diesen Monat ist dein Kontingent bereits aufgebraucht."})
                    return
                db.execute("INSERT INTO insults(sender, recipient, message, created_at, month) VALUES(?,?,?,?,?)", (sender, recipient, message, created_at, month))
                db.commit()
        except sqlite3.Error:
            self.send_json(500, {"error": "Der Eintrag konnte nicht gespeichert werden."})
            return
        self.send_json(201, {"ok": True})


if __name__ == "__main__":
    initialize()
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
