"""SAMS web front-end (Flask) - reuses the same core modules as the CLI."""
from __future__ import annotations

import os
import json
import datetime as dt

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_from_directory, jsonify, abort, session)
from werkzeug.utils import secure_filename

import config
from core.pipeline import AttendancePipeline
from core.database import Database
from core.xml_parser import InfoXmlParser
from core.signature_verify import SignatureVerifier
from core.auth import (current_user, login_required, role_required,
                       hash_password, verify_password, ROLES)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
ALLOWED = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def db_or_none():
    db = Database()
    return db if db.ping() else None


@app.context_processor
def inject_globals():
    return {"db_online": db_or_none() is not None,
            "year": dt.date.today().year,
            "user": current_user()}


# ==========================================================================
# M1 — Login + Dashboard
# ==========================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        db = db_or_none()
        if not db:
            flash("MySQL is offline - start it in XAMPP.", "error")
            return redirect(url_for("login"))
        u = db.get_user_by_username(request.form.get("username", "").strip())
        if u and verify_password(request.form.get("password", ""),
                                 u["password_hash"]):
            session["user_id"] = u["user_id"]
            session["username"] = u["username"]
            session["role"] = u["role"]
            session["full_name"] = u["full_name"] or u["username"]
            flash(f"Welcome back, {session['full_name']}.", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    db = db_or_none()
    students, sessions_, summary = [], [], []
    if db:
        students = db.get_students()
        sessions_ = db.get_sessions()
        summary = db.get_class_summary()
    total_marks = sum(r["total"] for r in summary)
    total_present = sum(r["present"] for r in summary)
    rate = (total_present / total_marks * 100) if total_marks else 0
    return render_template("index.html", students=students,
                           sessions=sessions_, summary=summary, rate=rate,
                           n_students=len(students), n_sessions=len(sessions_))


# ==========================================================================
# M2 — Process sheet
# ==========================================================================
@app.route("/process", methods=["GET", "POST"])
@login_required
def process():
    if request.method == "GET":
        return render_template("process.html")

    file = request.files.get("sheet")
    if not file or not file.filename:
        flash("Choose a signing-sheet image first.", "error")
        return redirect(url_for("process"))
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED:
        flash(f"Unsupported file type '{ext}'.", "error")
        return redirect(url_for("process"))

    img_path = os.path.join(config.UPLOAD_DIR, secure_filename(file.filename))
    file.save(img_path)

    xml_path = config.DEFAULT_XML
    xml_file = request.files.get("info")
    if xml_file and xml_file.filename:
        xml_path = os.path.join(config.UPLOAD_DIR,
                                secure_filename(xml_file.filename))
        xml_file.save(xml_path)

    logs = []
    try:
        pipeline = AttendancePipeline(
            logger=lambda *a: logs.append(" ".join(map(str, a))))
        result, info, _ = pipeline.process(img_path, xml_path)
    except Exception as exc:                                # noqa: BLE001
        flash(f"Processing failed: {exc}", "error")
        return redirect(url_for("process"))

    return render_template("result.html", r=result, logs=logs)


# ==========================================================================
# M3 — Result
# ==========================================================================
@app.route("/process/<job>/save", methods=["POST"])
@login_required
def save_job(job):
    path = os.path.join(config.OUTPUT_DIR, job, "result.json")
    if not os.path.exists(path):
        abort(404)
    with open(path, encoding="utf-8") as fh:
        result = json.load(fh)

    records = [(rec["student_no"],
                request.form.get(f"status_{rec['student_no']}", rec["status"]))
               for rec in result["records"]]
    try:
        info = InfoXmlParser().parse(result.get("xml_path",
                                                config.DEFAULT_XML))
        sid = AttendancePipeline(logger=None).persist(result, info, records)
        flash(f"Attendance saved (session #{sid}).", "success")
    except Exception as exc:                                # noqa: BLE001
        flash(f"Could not save: {exc}", "error")
    return redirect(url_for("sessions"))


@app.route("/output/<job>/<path:filename>")
@login_required
def output_file(job, filename):
    return send_from_directory(os.path.join(config.OUTPUT_DIR, job), filename)


# ==========================================================================
# M4 — Sessions
# ==========================================================================
@app.route("/sessions")
@login_required
def sessions():
    db = db_or_none()
    return render_template("sessions.html",
                           sessions=db.get_sessions() if db else [])


# ==========================================================================
# M5 — Students
# ==========================================================================
@app.route("/students")
@login_required
def students():
    db = db_or_none()
    return render_template("students.html",
                           summary=db.get_class_summary() if db else [])


# ==========================================================================
# M6 — Student detail
# ==========================================================================
@app.route("/students/<student_no>")
@login_required
def student(student_no):
    db = db_or_none()
    if not db:
        flash("MySQL is offline.", "error")
        return redirect(url_for("dashboard"))
    s = db.get_student(student_no)
    if not s:
        abort(404)
    return render_template("student.html", s=s,
                           rows=db.get_student_attendance(student_no))


@app.route("/api/student/<student_no>")
@login_required
def api_student(student_no):
    db = db_or_none()
    rows = db.get_student_attendance(student_no) if db else []
    return jsonify({
        "labels": [r["session_date"].strftime("%d %b") for r in rows],
        "values": [1 if r["status"] == "present" else 0 for r in rows],
    })


@app.route("/api/overview")
@login_required
def api_overview():
    db = db_or_none()
    rows = db.get_class_summary() if db else []
    return jsonify({
        "labels": [str(r["student_no"]) for r in rows],
        "values": [round(float(r["present"]) / r["total"] * 100, 1)
                   if r["total"] else 0.0 for r in rows],
    })


# ==========================================================================
# M7 — Investigate
# ==========================================================================
@app.route("/investigate/<student_no>")
@login_required
def investigate(student_no):
    db = db_or_none()
    s = (db.get_student(student_no) if db else None) or \
        {"student_no": student_no, "title": "", "name": ""}
    res = SignatureVerifier().investigate(student_no)
    samples = [{"label": smp.label,
                "url": url_for("signature_file", student_no=student_no,
                               filename=os.path.basename(smp.path))}
               for smp in res["samples"]]
    return render_template("investigate.html", s=s, res=res, samples=samples)


@app.route("/signatures/<student_no>/<path:filename>")
@login_required
def signature_file(student_no, filename):
    return send_from_directory(os.path.join(config.SIGN_DIR, student_no),
                               filename)


# ==========================================================================
# M8 — Accounts (admin only)
# ==========================================================================
@app.route("/users")
@role_required("admin")
def users():
    db = db_or_none()
    return render_template("users.html",
                           accounts=db.list_users() if db else [])


@app.route("/users/add", methods=["POST"])
@role_required("admin")
def users_add():
    db = db_or_none()
    if not db:
        flash("MySQL is offline.", "error")
        return redirect(url_for("users"))
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "staff")
    if not username or not password:
        flash("Username and password are required.", "error")
    elif role not in ROLES:
        flash("Invalid role.", "error")
    elif db.get_user_by_username(username):
        flash(f"'{username}' already exists.", "error")
    else:
        db.create_user(username, hash_password(password), role,
                       request.form.get("full_name", "").strip())
        flash(f"Created {role} account '{username}'.", "success")
    return redirect(url_for("users"))


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def users_delete(user_id):
    if user_id == current_user()["id"]:
        flash("You can't delete the account you are logged in with.", "error")
    else:
        db = db_or_none()
        if db:
            db.delete_user(user_id)
            flash("Account deleted.", "success")
    return redirect(url_for("users"))


# ==========================================================================
if __name__ == "__main__":
    d = Database()
    if not d.ping():
        try:
            d.bootstrap()
        except Exception:                                   # noqa: BLE001
            pass
    if d.ping() and d.user_count() == 0:
        d.create_user("admin", hash_password("admin123"), "admin",
                      "Default Admin")
        print("No accounts found - created 'admin' / 'admin123'. "
              "CHANGE THIS PASSWORD.")
    app.run(debug=True, port=5000)