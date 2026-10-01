"""CampusBot leave-request backend.

A small Flask REST API that automates a manual leave-approval process.
watsonx Assistant calls it through a custom extension (see openapi.yaml).

Business rules (see assistant/process_definition.md):
  * 1-2 days  -> APPROVED automatically
  * 3-5 days  -> PENDING_HOD_APPROVAL
  * 6+ days   -> ESCALATED (HOD approval + supporting documents required)
"""
import os
import re
import sqlite3
from datetime import date, datetime, timezone

from flask import Flask, g, jsonify, request

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leave.db")
STUDENT_ID_RE = re.compile(r"^[A-Za-z0-9\-]{4,20}$")
REQUEST_ID_RE = re.compile(r"^LR-(\d{1,8})$", re.IGNORECASE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS leave_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT    NOT NULL,
    days        INTEGER NOT NULL,
    from_date   TEXT    NOT NULL,
    reason      TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    remarks     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
"""


def decide(days: int):
    """Apply the leave-approval business rules."""
    if days <= 2:
        return "APPROVED", "Auto-approved (2 days or fewer)."
    if days <= 5:
        return "PENDING_HOD_APPROVAL", "Sent to the HOD for approval."
    return "ESCALATED", "More than 5 days: HOD approval and supporting documents are required."


def validate(payload):
    """Return (clean_data, error_message)."""
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    student_id = str(payload.get("student_id", "")).strip()
    if not STUDENT_ID_RE.match(student_id):
        return None, "student_id must be 4-20 letters, digits or hyphens."

    try:
        days = int(payload.get("days"))
    except (TypeError, ValueError):
        return None, "days must be a whole number."
    if not 1 <= days <= 30:
        return None, "days must be between 1 and 30."

    from_date = str(payload.get("from_date", "")).strip()
    try:
        date.fromisoformat(from_date)
    except ValueError:
        return None, "from_date must be a valid date in YYYY-MM-DD format."

    reason = str(payload.get("reason", "")).strip()
    if not 3 <= len(reason) <= 200:
        return None, "reason must be between 3 and 200 characters."

    return {"student_id": student_id, "days": days, "from_date": from_date, "reason": reason}, None


def row_to_dict(row):
    return {
        "request_id": f"LR-{row['id']:04d}",
        "student_id": row["student_id"],
        "days": row["days"],
        "from_date": row["from_date"],
        "reason": row["reason"],
        "status": row["status"],
        "remarks": row["remarks"],
        "created_at": row["created_at"],
    }


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", DEFAULT_DB)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with sqlite3.connect(app.config["DB_PATH"]) as conn:
        conn.executescript(SCHEMA)

    @app.before_request
    def check_api_key():
        """If API_KEY is set, every endpoint except /health needs it."""
        expected = os.environ.get("API_KEY")
        if expected and request.endpoint != "health":
            if request.headers.get("X-API-Key") != expected:
                return jsonify(error="Invalid or missing API key."), 401

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/leave-requests")
    def create_leave_request():
        data, error = validate(request.get_json(silent=True))
        if error:
            return jsonify(error=error), 400

        status, remarks = decide(data["days"])
        db = get_db()
        cur = db.execute(
            "INSERT INTO leave_requests (student_id, days, from_date, reason, status, remarks, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data["student_id"], data["days"], data["from_date"], data["reason"], status, remarks,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        db.commit()
        row = db.execute("SELECT * FROM leave_requests WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/leave-requests/<request_id>")
    def get_leave_request(request_id):
        match = REQUEST_ID_RE.match(request_id.strip())
        if not match:
            return jsonify(error="request_id must look like LR-0001."), 400
        row = get_db().execute("SELECT * FROM leave_requests WHERE id = ?", (int(match.group(1)),)).fetchone()
        if row is None:
            return jsonify(error=f"No leave request found with id {request_id.upper()}."), 404
        return jsonify(row_to_dict(row))

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    create_app().run(host="0.0.0.0", port=port)
