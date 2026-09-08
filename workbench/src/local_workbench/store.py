import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from .identities import REVIEWERS, canonical_name
from .messages import english_message


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS actors(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, actor_id TEXT REFERENCES actors(id));
                CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, actor_id TEXT, actor TEXT,
                    body TEXT, digest TEXT, status TEXT, message TEXT, created REAL, updated REAL);
                CREATE TABLE IF NOT EXISTS drafts(actor_id TEXT, task_id TEXT, body TEXT,
                    PRIMARY KEY(actor_id,task_id));
            """)
            db.execute("UPDATE requests SET status='queued',message='Reconciling after restart' WHERE status='running'")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def session(self, token):
        with self.connect() as db:
            row = db.execute("SELECT s.token,a.id,a.name FROM sessions s LEFT JOIN actors a ON a.id=s.actor_id WHERE s.token=?", (token,)).fetchone()
            if row:
                return dict(row)
            token = secrets.token_urlsafe(32)
            db.execute("INSERT INTO sessions(token) VALUES(?)", (token,))
            return {"token": token, "id": None, "name": None}

    def select_actor(self, token, name):
        name = canonical_name(name)
        if name not in REVIEWERS:
            raise ValueError("Please choose a reviewer from the list.")
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO actors VALUES(?,?)", (str(uuid.uuid4()), name))
            actor = db.execute("SELECT * FROM actors WHERE name=?", (name,)).fetchone()
            db.execute("UPDATE sessions SET actor_id=? WHERE token=?", (actor["id"], token))
        return self.session(token)

    def actors(self):
        with self.connect() as db:
            existing = {r["name"]: dict(r) for r in db.execute("SELECT * FROM actors")}
            return [existing.get(name, {"id": None, "name": name}) for name in REVIEWERS]

    def enqueue(self, actor, body):
        if not actor.get("id") or actor.get("name") not in REVIEWERS:
            raise ValueError("Please select a reviewer first.")
        request_id = str(uuid.UUID(body["request_id"]))
        body = dict(body, request_id=request_id, actor=actor["name"])
        encoded = json.dumps(body, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
        with self.connect() as db:
            previous = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if previous:
                if previous["digest"] != fingerprint or previous["actor_id"] != actor["id"]:
                    raise ValueError("A request ID cannot be reused for a different decision.")
                return dict(previous)
            now = time.time()
            db.execute("INSERT INTO requests VALUES(?,?,?,?,?,?,?,?,?)",
                       (request_id, actor["id"], actor["name"], encoded, fingerprint, "queued", "Submitted", now, now))
        return {"id": request_id, "status": "queued", "message": "Submitted"}

    def requests(self):
        with self.connect() as db:
            rows = list(db.execute("SELECT * FROM requests ORDER BY created DESC"))
            return [{"id": r["id"], "actor": canonical_name(r["actor"]), "status": r["status"], "message": english_message(r["message"]),
                     "created": r["created"], "updated": r["updated"],
                     "action": json.loads(r["body"]).get("action"),
                     "task_id": json.loads(r["body"]).get("task_id"),
                     "note": json.loads(r["body"]).get("note", "")} for r in rows]

    def next_request(self):
        with self.connect() as db:
            row = db.execute("SELECT * FROM requests WHERE status='queued' OR (status='waiting' AND updated < ?) ORDER BY created LIMIT 1", (time.time()-5,)).fetchone()
            if row:
                db.execute("UPDATE requests SET status='running',updated=? WHERE id=?", (time.time(), row["id"]))
                return dict(row)

    def finish(self, request_id, status, message):
        with self.connect() as db:
            db.execute("UPDATE requests SET status=?,message=?,updated=? WHERE id=?", (status, message, time.time(), request_id))

    def draft(self, actor_id, task_id, body=None):
        with self.connect() as db:
            if body is not None:
                db.execute("INSERT OR REPLACE INTO drafts VALUES(?,?,?)", (actor_id,task_id,json.dumps(body,ensure_ascii=False)))
            row = db.execute("SELECT body FROM drafts WHERE actor_id=? AND task_id=?", (actor_id,task_id)).fetchone()
            return json.loads(row["body"]) if row else {}
