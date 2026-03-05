from flask import Flask, request, jsonify
from collections import deque
import os

app = Flask(__name__)

command_queue = deque()
TOKEN = os.environ.get("RC_TOKEN", "changeme123")

# Lista plików wysłana przez plugin
plugin_files = []


def check_token(req):
    return req.headers.get("X-Token") == TOKEN


# ── Klient Python wysyła komendę ──────────────────────────────────────────────
@app.route("/send", methods=["POST"])
def send_command():
    if not check_token(request):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or "command" not in data:
        return jsonify({"error": "Missing 'command' field"}), 400
    command_queue.append({
        "command": data["command"],
        "silent":  data.get("silent", False)
    })
    return jsonify({"ok": True, "queued": len(command_queue)})


# ── Plugin odpytuje co 2 sekundy ──────────────────────────────────────────────
@app.route("/poll", methods=["GET"])
def poll():
    if not check_token(request):
        return jsonify({"error": "Unauthorized"}), 401
    if command_queue:
        item = command_queue.popleft()
        return jsonify({"command": item["command"], "silent": item["silent"]})
    return jsonify({"command": None})


# ── Plugin wysyła listę plików ────────────────────────────────────────────────
@app.route("/files", methods=["POST"])
def upload_files():
    if not check_token(request):
        return jsonify({"error": "Unauthorized"}), 401
    global plugin_files
    data = request.get_json()
    if data and "files" in data:
        plugin_files = data["files"]
    return jsonify({"ok": True})


# ── GUI pobiera listę plików ──────────────────────────────────────────────────
@app.route("/files", methods=["GET"])
def get_files():
    if not check_token(request):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"files": plugin_files})


# ── Status ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "queued": len(command_queue)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
