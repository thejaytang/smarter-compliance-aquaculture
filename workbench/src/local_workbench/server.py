from __future__ import annotations
import hashlib
import json
import mimetypes
import os
import re
import secrets
import threading
import time
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, quote, unquote
from .adapter import System1
from .store import Store
from .evidence import registered_pdf, pdf_range
from .dashboard import build_dashboard


class Application:
    def __init__(self, root, system_root=None, config=None):
        self.root = Path(root).resolve()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.runtime / "workbench.sqlite")
        self.adapter = System1(system_root or self.root.parent / "system1", config)
        self.csrf = secrets.token_urlsafe(32)
        self.instance = secrets.token_urlsafe(24)
        self.stop = threading.Event()
        self.snapshot_lock = threading.Lock()
        self.snapshot_cache = None
        self.snapshot_time = 0
        self.qa_next_check = 0
        self.qa_status = {}
        self.worker = threading.Thread(target=self.work, daemon=True)
        self.worker.start()

    def snapshot(self):
        with self.snapshot_lock:
            if self.snapshot_cache is None or time.time() - self.snapshot_time > 3:
                self.snapshot_cache = self.adapter.call("read")
                self.snapshot_time = time.time()
            return self.snapshot_cache

    def work(self):
        while not self.stop.wait(.4):
            req = self.store.next_request()
            if not req:
                if time.time() >= self.qa_next_check:
                    self.qa_next_check = time.time() + 60
                    try:
                        self.qa_status = self.adapter.call("random_qa")
                        if self.qa_status.get("generated_count"):
                            self.snapshot_time = 0
                    except Exception as exc:
                        self.qa_status = {"status": "WAITING", "message": str(exc)}
                    path = self.runtime / "qa-schedule-status.json"
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text(json.dumps({"checked_at": time.time(), **self.qa_status}))
                    tmp.replace(path)
                continue
            try:
                result = self.adapter.call("apply", request=json.loads(req["body"]))
                status, message = result["status"], result["message"]
            except Exception as exc:
                message = str(exc)
                if "STALE:" in message:
                    status = "stale"
                elif any(t in message.lower() for t in ("workbook is open", "save and close", "already running")):
                    status, message = "waiting", "Waiting for Excel to close or the current system task to finish. Processing will resume automatically."
                else:
                    status = "blocked"
            self.store.finish(req["id"], status, message)
            self.snapshot_time = 0

    def close(self):
        self.stop.set()
        self.worker.join(timeout=190)


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalWorkbench"
    protocol_version = "HTTP/1.1"

    @property
    def app(self):
        return self.server.app

    def log_message(self, *args):
        pass

    def send(self, status, data, content_type="application/json; charset=utf-8", headers=None):
        if content_type.startswith("application/json"):
            data = json.dumps(data, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        headers = dict(headers or {})
        policy = headers.pop("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Content-Security-Policy", policy)
        for k,v in (headers or {}).items():
            self.send_header(k,v)
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def current_session(self):
        try:
            cookie=SimpleCookie(self.headers.get("Cookie",""))
            key = f"wb_session_{self.server.server_port}"
            # Cookies are host-scoped, not port-scoped. Separate workbench instances
            # must not replace one another's reviewer session on 127.0.0.1.
            token = cookie[key].value if key in cookie else (cookie["wb_session"].value if "wb_session" in cookie else "")
        except Exception:
            token=""
        return self.app.store.session(token)

    def do_GET(self):
        if not self.valid_host():
            return self.send(403,{"error":"Host not allowed."})
        parsed=urlsplit(self.path)
        try:
            if parsed.path=="/health":
                return self.send(200,{"service":"aquaculture-workbench","root":str(self.app.root),"instance":self.app.instance})
            if parsed.path=="/api/state":
                session=self.current_session()
                data=self.app.snapshot()
                # Machine payloads stay in System1; public projection contains reviewed fields only.
                def project_task(task):
                    result={k:v for k,v in task.items() if k!="payload_json"}
                    try:payload=json.loads(task.get("payload_json") or "{}")
                    except (ValueError,TypeError):payload={}
                    result["application_request_id"]=payload.get("workbench_applied")
                    review=payload.get("external_review")
                    if isinstance(review,dict):
                        result["external_review"]={k:review.get(k) for k in
                            ("artifact_sha256","row","reviewer","verdict","review_date")}
                    return result
                public={**data,"tasks":[project_task(t) for t in data["tasks"]],
                        "history":[project_task(t) for t in data["history"]],
                        "dashboard":build_dashboard(data,getattr(self.app,"snapshot_time",time.time())),
                        "qa_schedule":getattr(self.app,"qa_status",{})}
                return self.send(200,{**public,"actor":{"id":session["id"],"name":session["name"]},
                    "actors":self.app.store.actors(),"requests":self.app.store.requests(),"csrf":self.app.csrf},
                    headers={"Set-Cookie":f"wb_session_{self.server.server_port}={session['token']}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000"})
            if parsed.path=="/api/draft":
                session=self.current_session()
                task=parse_qs(parsed.query).get("task",[""])[0]
                return self.send(200,self.app.store.draft(session["id"],task) if session["id"] else {})
            if parsed.path.startswith("/api/original/"):
                source_id=parsed.path.rsplit("/",1)[-1]
                artifact=self.app.adapter.call("artifact",source_id=source_id)
                path=Path(artifact["path"])
                # Originals are download-only. Active source HTML never runs on our origin.
                return self.send(200,path.read_bytes(),"application/octet-stream",
                    {"Content-Disposition":"attachment; filename*=UTF-8''"+quote(path.name)})
            pdf_match = re.fullmatch(r"/api/pdf/([A-Za-z0-9_-]+)/([0-9a-f]{64})/([^/]+)", parsed.path)
            if pdf_match and not parsed.query:
                source_id, expected_hash, filename = pdf_match.groups()
                artifact = self.app.adapter.call("artifact", source_id=source_id)
                if unquote(filename) != Path(artifact["path"]).name:
                    raise ValueError("The original filename does not match the registry. Reopen the document.")
                data, fingerprint = registered_pdf(artifact, expected_hash)
                status, body, range_headers = pdf_range(data, self.headers.get("Range"))
                return self.send(status, body, "application/pdf", {
                    "Content-Disposition": "inline; filename*=UTF-8''" + quote(Path(artifact["path"]).name),
                    "Content-Security-Policy": "default-src 'none'; object-src 'self'; frame-ancestors 'self'",
                    "Accept-Ranges": "bytes", "ETag": '"' + fingerprint + '"', **range_headers,
                })
            if parsed.path.startswith("/api/preview/"):
                source_id=parsed.path.rsplit("/",1)[-1]
                artifact=self.app.adapter.call("artifact",source_id=source_id)
                path=Path(artifact["path"])
                if path.suffix.lower() == ".pdf":
                    _, fingerprint = registered_pdf(artifact)
                    return self.send(200, {"kind":"pdf", "filename":path.name,
                        "url":"/api/pdf/"+quote(source_id)+"/"+fingerprint+"/"+quote(path.name),
                        "label":"The registered full local PDF, with page, zoom and search controls."})
                if path.suffix.lower() not in {".html",".htm",".txt"}:
                    return self.send(200,{"kind":"download","message":"Download and open the original to review it."})
                import html
                from html.parser import HTMLParser
                class TextOnly(HTMLParser):
                    def __init__(self):
                        super().__init__();self.parts=[];self.skip=0
                    def handle_starttag(self,tag,attrs):
                        if tag in {"script","style"}:self.skip+=1
                        if tag in {"p","br","tr","h1","h2","li","section"}:self.parts.append("\n")
                    def handle_endtag(self,tag):
                        if tag in {"script","style"}:self.skip=max(0,self.skip-1)
                    def handle_data(self,data):
                        if not self.skip:self.parts.append(data)
                parser=TextOnly();parser.feed(path.read_text(errors="replace"))
                return self.send(200,{"kind":"text","text":"".join(parser.parts),"label":"Text preview of the local snapshot. Open the original for its published layout."})
            static={"/":"index.html","/app.js":"app.js","/style.css":"style.css",
                    "/evidence-viewer.js":"evidence-viewer.js","/review-state.js":"review-state.js",
                    "/dashboard.js":"dashboard.js", "/qa-chart.js":"qa-chart.js",
                    "/system2-review.js":"system2-review.js", "/system2-review.css":"system2-review.css",
                    "/system2-review-state.js":"system2-review-state.js",
                    "/system2-demo-data.js":"system2-demo-data.js",
                    "/demo-assets/cs005-page-20.webp":"demo-assets/cs005-page-20.webp",
                    "/demo-assets/cs005-page-21.webp":"demo-assets/cs005-page-21.webp"}
            if parsed.path not in static:
                return self.send(404,{"error":"Page not found."})
            path=self.app.root/"ui"/static[parsed.path]
            return self.send(200,path.read_bytes(),mimetypes.guess_type(path)[0]+"; charset=utf-8")
        except Exception as exc:
            self.send(400,{"error":str(exc)})

    def do_POST(self):
        if (not self.valid_host() or self.headers.get("Origin")!=f"http://127.0.0.1:{self.server.server_port}"
                or self.headers.get("X-CSRF-Token")!=self.app.csrf):
            return self.send(403,{"error":"Invalid request origin. Submit from the local workbench."})
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length<1 or length>55_000_000:
                return self.send(413,{"error":"The file is empty or exceeds 50 MB."})
            session=self.current_session()
            if self.path=="/api/upload":
                if not session["id"]:
                    raise ValueError("Please select a reviewer first.")
                suffix=self.headers.get("X-File-Extension","").lower()
                if suffix not in {".pdf",".html",".htm",".xlsx"}:
                    raise ValueError("Choose a PDF, HTML or XLSX original.")
                data=self.rfile.read(length)
                valid = data.startswith(b"%PDF-") if suffix==".pdf" else (data.startswith(b"PK") if suffix==".xlsx" else b"<" in data[:1000])
                if not valid:
                    raise ValueError("The file content does not match its extension.")
                upload_id=str(uuid.uuid4())
                root=self.app.runtime/"uploads";root.mkdir(exist_ok=True)
                file=root/(upload_id+suffix);file.write_bytes(data)
                metadata={"actor_id":session["id"],"path":str(file),"hash":hashlib.sha256(data).hexdigest()}
                (root/(upload_id+".json")).write_text(json.dumps(metadata))
                return self.send(200,{"upload_id":upload_id,"hash":metadata["hash"],"size":length,
                    "message":"File staged and format check passed. Verify its identity, completeness and permissions before submitting."})
            if not self.headers.get("Content-Type","").startswith("application/json"):
                raise ValueError("Invalid request format.")
            body=json.loads(self.rfile.read(length))
            if self.path=="/api/actor":
                actor=self.app.store.select_actor(session["token"],body.get("name",""))
                return self.send(200,{"id":actor["id"],"name":actor["name"]})
            if not session["id"]:
                raise ValueError("Please select a reviewer first.")
            if self.path=="/api/draft":
                self.app.store.draft(session["id"],body["task_id"],body["draft"])
                return self.send(200,{"saved":True})
            if self.path=="/api/decisions":
                # Never accept process paths or operator identity from the browser.
                allowed={"request_id","task_id","revision","source_revision","action","note","scores",
                         "updates","issue_verified","verdict","upload_id","identity_verified","permission_verified"}
                if set(body)-allowed:
                    raise ValueError("The request contains fields that are not allowed.")
                if body.get("action")=="manual":
                    upload_id=str(uuid.UUID(body["upload_id"]))
                    upload_root=self.app.runtime/"uploads"
                    metadata=json.loads((upload_root/(upload_id+".json")).read_text())
                    if metadata["actor_id"]!=session["id"]:
                        raise ValueError("Use a file staged by the current reviewer.")
                    body.update(upload_path=metadata["path"],upload_hash=metadata["hash"],upload_root=str(upload_root))
                result=self.app.store.enqueue(session,body)
                return self.send(202,{"id":result["id"],"status":result["status"],"message":result["message"]})
            if self.path=="/api/stop":
                if any(r["status"] in {"queued","running","waiting"} for r in self.app.store.requests()):
                    raise ValueError("Submitted tasks are still processing. Wait for them to finish before exiting.")
                self.send(200,{"message":"Workbench stopped."})
                threading.Thread(target=self.server.shutdown,daemon=True).start()
                return
            return self.send(404,{"error":"Action not found."})
        except Exception as exc:
            self.send(400,{"error":str(exc)})


def bind_local_server(runtime):
    """Retain the browser origin across restarts; this is device-local runtime state."""
    preferred = 0
    for path in (runtime / "listen-port.json", runtime / "server.json"):
        try:
            port = json.loads(path.read_text())["port"]
            if isinstance(port, int) and not isinstance(port, bool) and 1024 <= port <= 65535:
                preferred = port
                break
        except (OSError, ValueError, KeyError, TypeError):
            pass
    try:
        server = ThreadingHTTPServer(("127.0.0.1", preferred), Handler)
    except OSError:
        if not preferred:
            raise
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    path = runtime / "listen-port.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"port": server.server_port}))
    tmp.replace(path)
    return server


def serve(root, system_root=None, config=None):
    app=Application(root,system_root,config)
    server=bind_local_server(app.runtime)
    server.app=app
    state={"pid":os.getpid(),"port":server.server_port,"instance":app.instance,"root":str(app.root)}
    target=app.runtime/"server.json"
    tmp=target.with_suffix(".tmp");tmp.write_text(json.dumps(state));tmp.replace(target)
    try:
        server.serve_forever(poll_interval=.3)
    finally:
        server.server_close();app.close()
        if target.exists() and json.loads(target.read_text()).get("instance")==app.instance:target.unlink()
