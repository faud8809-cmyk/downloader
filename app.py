import os, json, secrets, socket, ipaddress, re
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import requests

APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "api_settings.json"
MAX_BYTES = 100 * 1024 * 1024
ALLOWED_EXT = {".mp4", ".webm", ".mov", ".ogg", ".m4v"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

def read_config():
    if not CONFIG_FILE.exists():
        return {"providers": []}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("providers"), list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"providers": []}

def save_config(data):
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(24)
    return session["_csrf"]

@app.context_processor
def inject_csrf():
    return {"csrf_token": csrf_token}

def csrf_ok():
    return secrets.compare_digest(
        str(request.form.get("_csrf", "")), str(session.get("_csrf", ""))
    )

def is_admin():
    return session.get("admin") is True

def require_admin():
    if not is_admin():
        return redirect(url_for("admin_login"))
    return None

def validate_public_http_url(raw):
    try:
        parsed = urlparse(raw.strip())
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        host = parsed.hostname.lower()
        if host == "localhost" or host.endswith(".local"):
            return None
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for info in infos:
            addr = ipaddress.ip_address(info[4][0])
            if not addr.is_global:
                return None
        return parsed
    except Exception:
        return None

@app.get("/")
def home():
    providers = read_config()["providers"]
    active_names = [p.get("platform", "Custom") for p in providers if p.get("enabled")]
    return render_template("index.html", active_names=active_names)

@app.post("/download")
def download_direct():
    raw = request.form.get("url", "").strip()
    parsed = validate_public_http_url(raw)
    if not parsed:
        return render_template("index.html", error="Please enter a valid public HTTP/HTTPS URL.")

    extension = "." + parsed.path.rsplit(".", 1)[-1].lower() if "." in parsed.path else ""
    if extension not in ALLOWED_EXT:
        return render_template(
            "index.html",
            error="This starter version downloads direct video-file URLs only. Social-media page extraction requires a provider API adapter."
        )

    upstream = None
    try:
        upstream = requests.get(raw, stream=True, timeout=20, allow_redirects=False)
        if upstream.status_code != 200:
            upstream.close()
            return render_template("index.html", error=f"Source returned HTTP {upstream.status_code}.")
        content_type = upstream.headers.get("Content-Type", "").lower()
        if content_type and not (content_type.startswith("video/") or content_type == "application/octet-stream"):
            upstream.close()
            return render_template("index.html", error="The source does not appear to be a video file.")
        length = upstream.headers.get("Content-Length")
        if length and int(length) > MAX_BYTES:
            upstream.close()
            return render_template("index.html", error="File exceeds the demo's 100 MB limit.")

        filename = re.sub(r"[^A-Za-z0-9._-]", "_", parsed.path.rsplit("/", 1)[-1]) or "video" + extension

        def stream():
            count = 0
            try:
                for chunk in upstream.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    count += len(chunk)
                    if count > MAX_BYTES:
                        break
                    yield chunk
            finally:
                upstream.close()

        return Response(stream(), mimetype=content_type or "application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except requests.RequestException:
        if upstream:
            upstream.close()
        return render_template("index.html", error="Unable to retrieve this source. Try another direct video URL.")

@app.get("/admin")
def admin_login():
    if is_admin():
        return redirect(url_for("admin_dashboard"))
    return render_template("login.html")

@app.post("/admin/login")
def admin_login_post():
    if not csrf_ok():
        return render_template("login.html", error="Security token expired. Refresh and try again.")
    expected = os.environ.get("ADMIN_PASSWORD", "change-this-password")
    password = request.form.get("password", "")
    if secrets.compare_digest(password, expected):
        session.clear()
        session["admin"] = True
        session["_csrf"] = secrets.token_urlsafe(24)
        return redirect(url_for("admin_dashboard"))
    return render_template("login.html", error="Incorrect password.")

@app.get("/admin/dashboard")
def admin_dashboard():
    gate = require_admin()
    if gate:
        return gate
    return render_template("admin.html", providers=read_config()["providers"])

@app.post("/admin/provider/save")
def provider_save():
    gate = require_admin()
    if gate:
        return gate
    if not csrf_ok():
        flash("Security token expired. Refresh and retry.", "error")
        return redirect(url_for("admin_dashboard"))

    data = read_config()
    providers = data["providers"]
    provider_id = request.form.get("provider_id", "").strip()
    name = request.form.get("name", "").strip()[:80]
    platform = request.form.get("platform", "Custom").strip()[:40]
    api_url = request.form.get("api_url", "").strip()[:500]
    api_key = request.form.get("api_key", "").strip()[:500]
    enabled = request.form.get("enabled") == "on"

    if not name:
        flash("API name is required.", "error")
        return redirect(url_for("admin_dashboard"))

    if api_url and not validate_public_http_url(api_url):
        flash("API URL must be a public HTTP/HTTPS address.", "error")
        return redirect(url_for("admin_dashboard"))

    existing = next((p for p in providers if p.get("id") == provider_id), None)
    if existing:
        existing.update({"name": name, "platform": platform, "api_url": api_url,
                         "enabled": enabled, "api_key": api_key or existing.get("api_key", "")})
    else:
        providers.append({"id": secrets.token_hex(8), "name": name, "platform": platform,
                         "api_url": api_url, "api_key": api_key, "enabled": enabled})
    save_config(data)
    flash("API settings saved. A provider adapter is still needed before this API can process downloads.", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/provider/delete")
def provider_delete():
    gate = require_admin()
    if gate:
        return gate
    if not csrf_ok():
        flash("Security token expired.", "error")
        return redirect(url_for("admin_dashboard"))
    provider_id = request.form.get("provider_id", "")
    data = read_config()
    data["providers"] = [p for p in data["providers"] if p.get("id") != provider_id]
    save_config(data)
    flash("API entry removed.", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/logout")
def admin_logout():
    if not csrf_ok():
        return redirect(url_for("admin_dashboard"))
    session.clear()
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
