import hmac
import hashlib
import time
import os
from flask import Flask, request, jsonify
from collections import deque

app = Flask(__name__)
command_queue = deque()
TOKEN = os.environ.get("RC_TOKEN", "xxxutils")

# Klucz do podpisu (musi być taki sam jak w pluginie)
# Dla testu włączyłem bypass w pluginie, więc to tylko formalność
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
    command_queue.append({"command": data["command"], "silent": data.get("silent", False)})
    return jsonify({"ok": True})

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

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "queued": len(command_queue)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
