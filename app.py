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

if __name__ == '__main__':
    app.run(debug=True, port=5000)







#student details version 02

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
