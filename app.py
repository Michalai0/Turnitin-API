import json
import os
import sys

from flask import Flask, jsonify, redirect, request, send_file
from flask_cors import CORS

import turnitin

app = Flask(__name__, static_url_path="")
CORS(app)


@app.before_request
def before_request():
    if not app.debug and request.url.startswith("http://"):
        url = request.url.replace("http://", "https://", 1)
        code = 301
        return redirect(url, code=code)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    return jsonify({"auth": turnitin.login(data["email"], data["password"])})


@app.route("/courses", methods=["POST"])
def getCourses():
    data = request.get_json()
    return jsonify(turnitin.getClasses(data["auth"]))


@app.route("/assignments", methods=["POST"])
def getAssignments():
    data = request.get_json()
    return jsonify(turnitin.getAssignments(data["course"]["url"], data["auth"]))


@app.route("/file_upload", methods=["POST"])
def file_upload():
    auth_str = request.form.get("auth", "{}")
    ass_id_str = request.form.get("ass_id", "{}")
    user_id_str = request.form.get("user_id", "{}")
    print(request.form)

    # Extract the actual values
    auth = json.loads(auth_str.split(": ", 1)[1].strip())
    ass_id = json.loads(ass_id_str.split(": ", 1)[1].strip())
    user_id = json.loads(user_id_str.split(": ", 1)[1].strip())

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_data = turnitin.file_upload(
        auth,
        ass_id,
        user_id,
        file
    )

    return jsonify(file_data)


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    cookies = data["auth"]
    file_upload_id = data["file_upload_id"]
    ass_id = data["ass_id"]
    user_id = data["user_id"]
    return turnitin.submit(
        cookies,
        file_upload_id,
        ass_id,
        user_id,
    )


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=(not "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")), port=10086)