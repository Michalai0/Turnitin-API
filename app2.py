import json
import os
import io
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


@app.route("/turnitin_workflow", methods=["POST"])
def turnitin_workflow():
    data = request.json
    auth = {
              "auth": {
                "legacy-session-id": "5f732217ef634942af09d1a081cb0db0",
                "session-id": "5f732217ef634942af09d1a081cb0db0"
              }
            }
    # Step 1: Login
    #auth = turnitin.login(data["email"], data["password"])

    # Step 2: Get Courses
    courses = turnitin.getClasses(auth["auth"])
    print(courses)

    # Step 3: Get Assignments
    all_assignments = []
    for course in courses:
        assignments = turnitin.getAssignments(course["url"], auth["auth"])
        all_assignments.extend(assignments)
    print(all_assignments)

    test_assignment = all_assignments[2]
    print(test_assignment)

    # Step 4: File Upload
    file_url = data['file_url']

    file_data = turnitin.file_upload(auth["auth"], test_assignment["ass_id"], test_assignment["user_id"], file_url)
    print(file_data)

    # Step 5: Submit
    submission_result = turnitin.submit(
        auth["auth"],
        file_data["id"],
        test_assignment["ass_id"],
        test_assignment["user_id"]
    )
    print(submission_result)

    return jsonify({
        "file_upload": file_data,
        "submission": submission_result
    })

@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=(not "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")), port=10086)
