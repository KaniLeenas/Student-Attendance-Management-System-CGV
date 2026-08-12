# SAMS — Code for 8 Members
### CS402.3 Computer Graphics and Visualization · NSBM Green University Town, School of Computing

`sams_db.sql` is a **separate file** — import it into phpMyAdmin/XAMPP first, before touching any of this code.

Each member owns one UI page plus the backend that powers it. The section marked **Shared** below is common infrastructure everyone needs locally — copy it once, then add your own section on top of it.

---

## Ownership at a glance

| Member | Page | Branch | Files owned |
|---|---|---|---|
| **M1** | Login + Dashboard | `feat/login-dashboard` | `core/auth.py`, `templates/base.html`, `base_public.html`, `login.html`, `index.html`, `static/css/style.css` |
| **M2** | Process sheet | `feat/process-page` | `core/utils.py`, `core/preprocess.py`, `templates/process.html` |
| **M3** | Result | `feat/result-page` | `core/table_detector.py`, `core/signature_detector.py`, `core/pipeline.py`, `templates/result.html` |
| **M4** | Sessions | `feat/sessions-page` | `core/xml_parser.py`, `info.xml`, `sams.py`, `templates/sessions.html` |
| **M5** | Students | `feat/students-page` | `templates/students.html` |
| **M6** | Student detail | `feat/student-detail` | `core/visualization.py`, `infovis.py`, `static/js/app.js`, `templates/student.html` |
| **M7** | Investigate | `feat/investigate-page` | `core/signature_verify.py`, `investigate.py`, `templates/investigate.html` |
| **M8** | Accounts | `feat/accounts-page` | `manage_users.py`, `templates/users.html` |

**Git workflow:**
```bash
git clone https://github.com/<team>/SAMS.git
cd SAMS
git checkout -b feat/<your-branch>
git add <only your own files>
git commit -m "feat(process): add drag-and-drop upload and preprocessing pipeline"
git push -u origin feat/<your-branch>
# open a Pull Request -> Member 1 reviews and merges into main
```

---
---

# SHARED — set up once before starting your page

## `requirements.txt`

```text
opencv-python>=4.8.0
numpy>=1.24.0
matplotlib>=3.7.0
Flask>=3.0.0
Werkzeug>=3.0.0
mysql-connector-python>=8.2.0
Pillow>=10.0.0
```

## `config.py`

```python
"""Central configuration for SAMS (CS402.3)."""
import os

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
SHEETS_DIR  = os.path.join(DATA_DIR, "sheets")
OUTPUT_DIR  = os.path.join(DATA_DIR, "output")
SIGN_DIR    = os.path.join(DATA_DIR, "signatures")
UPLOAD_DIR  = os.path.join(DATA_DIR, "uploads")
SQL_FILE    = os.path.join(BASE_DIR, "sams_db.sql")
DEFAULT_XML = os.path.join(BASE_DIR, "info.xml")

for _d in (DATA_DIR, SHEETS_DIR, OUTPUT_DIR, SIGN_DIR, UPLOAD_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------- database
DB = {
    "host":     os.getenv("SAMS_DB_HOST", "127.0.0.1"),
    "port":     int(os.getenv("SAMS_DB_PORT", 3306)),
    "user":     os.getenv("SAMS_DB_USER", "root"),
    "password": os.getenv("SAMS_DB_PASS", ""),       # XAMPP default = empty
    "database": os.getenv("SAMS_DB_NAME", "sams_db"),
}

# ------------------------------------------------------------------ web
SECRET_KEY = os.getenv("SAMS_SECRET", "cs402.3-sams-change-me")

# ------------------------------------------------------- image pre-process
PIPELINE = {
    "target_width": 1600,
    "bilateral":    {"d": 7, "sigmaColor": 60, "sigmaSpace": 60},
    "adaptive":     {"blockSize": 41, "C": 12},
    "deskew_max_angle": 15.0,
}

# ------------------------------------------------------- table / grid step
TABLE = {
    "h_kernel_div": 30,        # horizontal line kernel = width  / 30
    "v_kernel_div": 60,        # vertical   line kernel = height / 60
    "line_vote":    0.55,      # fraction of the ROI a peak must cover
    # static layout fallback (measured from the NSBM signing sheet)
    "column_ratios": [0.000, 0.127, 0.307, 0.408, 0.794, 1.000],
}

# ------------------------------------------------- signature ink detection
SIGNATURE = {
    "cell_margin_x": 0.05,     # trim grid lines before measuring ink
    "cell_margin_y": 0.14,
    "dark_threshold": 190,     # after illumination flattening (paper ~255)
    "sat_min": 55,             # colour pens -> high saturation
    "val_min": 25,
    "val_max": 235,
    "min_component_area": 40,  # removes dust / JPEG speckle
    "ink_ratio_threshold": 0.015,
    "strong_ratio": 0.050,     # ratio mapped to 100 % confidence
}

# --------------------------------------------------- signature comparison
# NOTE: real-world testing (5 signing sheets, 6 students) showed that even a
# genuine same-person signature scores only ~45-65% similarity across
# different photographs (natural handwriting variation + photo-to-photo
# crop/lighting differences dominate the raw pixel/shape comparison). A
# FIXED absolute threshold therefore false-flagged every student. Verdicts
# are now relative: a sample is flagged only if it is a statistical outlier
# against that same student's OTHER samples, not against a global number.
VERIFY = {
    "canvas": (240, 120),        # w, h of the normalised signature canvas
    "weights": {"shape": 0.35, "profile": 0.35, "overlap": 0.20, "orb": 0.10},
    "outlier_z": 1.0,            # flag if mean sim is > 1.0 std below the group
    "min_absolute_floor": 25.0,  # below this, always flag regardless of z-score
    "overlap_dilate_iter": 4,    # tolerance for natural stroke-position drift
}
```

## `core/__init__.py`

```python
"""SAMS core package - image processing, database and verification modules."""
```

## `core/database.py`

```python
"""Data access layer for sams_db (MySQL / XAMPP)."""
from __future__ import annotations

import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error

import config


class Database:
    def __init__(self, cfg=None):
        self.cfg = dict(cfg or config.DB)

    # ------------------------------------------------------- connection
    @contextmanager
    def cursor(self, dictionary=True, commit=False):
        conn = mysql.connector.connect(**self.cfg)
        cur = conn.cursor(dictionary=dictionary)
        try:
            yield cur
            if commit:
                conn.commit()
        except Error:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def ping(self):
        try:
            with self.cursor() as c:
                c.execute("SELECT 1")
                c.fetchall()
            return True
        except Error:
            return False

    def bootstrap(self, sql_path=None):
        """Create the database + tables from sams_db.sql if missing."""
        sql_path = sql_path or config.SQL_FILE
        if not os.path.exists(sql_path):
            return False
        cfg = dict(self.cfg)
        cfg.pop("database", None)
        conn = mysql.connector.connect(**cfg)
        cur = conn.cursor()
        with open(sql_path, "r", encoding="utf-8") as fh:
            for stmt in fh.read().split(";"):
                if stmt.strip():
                    cur.execute(stmt)
        conn.commit()
        cur.close()
        conn.close()
        return True

    # ---------------------------------------------------------- writers
    def upsert_subject(self, code, title):
        with self.cursor(commit=True) as c:
            c.execute("""INSERT INTO subjects (subject_code, subject_title)
                         VALUES (%s, %s)
                         ON DUPLICATE KEY UPDATE
                           subject_title = VALUES(subject_title)""",
                      (code, title))

    def upsert_students(self, students, subject_code):
        with self.cursor(commit=True) as c:
            c.executemany("""INSERT INTO students
                               (student_no, title, name, subject_code)
                             VALUES (%s, %s, %s, %s)
                             ON DUPLICATE KEY UPDATE
                               title = VALUES(title),
                               name  = VALUES(name),
                               subject_code = VALUES(subject_code)""",
                          [(s.index, s.title, s.name, subject_code)
                           for s in students])

    def upsert_session(self, subject_code, date, start, end,
                       lecturer, hall, image):
        with self.cursor(commit=True) as c:
            c.execute("""INSERT INTO sessions
                           (subject_code, session_date, start_time, end_time,
                            lecturer, hall, source_image)
                         VALUES (%s, %s, %s, %s, %s, %s, %s)
                         ON DUPLICATE KEY UPDATE
                           end_time = VALUES(end_time),
                           lecturer = VALUES(lecturer),
                           hall     = VALUES(hall),
                           source_image = VALUES(source_image),
                           session_id = LAST_INSERT_ID(session_id)""",
                      (subject_code, date, start, end, lecturer, hall, image))
            return c.lastrowid

    def save_attendance(self, session_id, records):
        """records = [(student_no, 'present'|'absent'), ...]"""
        with self.cursor(commit=True) as c:
            c.executemany("""INSERT INTO attendance
                               (session_id, student_no, status)
                             VALUES (%s, %s, %s)
                             ON DUPLICATE KEY UPDATE status = VALUES(status)""",
                          [(session_id, no, st) for no, st in records])

    # ---------------------------------------------------------- readers
    def get_student(self, student_no):
        with self.cursor() as c:
            c.execute("SELECT * FROM students WHERE student_no = %s",
                      (student_no,))
            return c.fetchone()

    def get_students(self):
        with self.cursor() as c:
            c.execute("SELECT * FROM students ORDER BY student_no")
            return c.fetchall()

    def get_sessions(self):
        with self.cursor() as c:
            c.execute("""SELECT s.*,
                           COALESCE(SUM(a.status='present'),0) AS present,
                           COALESCE(COUNT(a.attendance_id),0)  AS total
                         FROM sessions s
                         LEFT JOIN attendance a ON a.session_id = s.session_id
                         GROUP BY s.session_id
                         ORDER BY s.session_date""")
            return c.fetchall()

    def get_student_attendance(self, student_no):
        with self.cursor() as c:
            c.execute("""SELECT s.session_id, s.session_date, s.start_time,
                                s.hall, s.lecturer, a.status
                         FROM attendance a
                         JOIN sessions s ON s.session_id = a.session_id
                         WHERE a.student_no = %s
                         ORDER BY s.session_date, s.start_time""",
                      (student_no,))
            return c.fetchall()

    def get_class_summary(self):
        with self.cursor() as c:
            c.execute("""SELECT st.student_no, st.title, st.name,
                           COALESCE(SUM(a.status='present'),0) AS present,
                           COALESCE(COUNT(a.attendance_id),0)  AS total
                         FROM students st
                         LEFT JOIN attendance a
                                ON a.student_no = st.student_no
                         GROUP BY st.student_no, st.title, st.name
                         ORDER BY st.student_no""")
            rows = c.fetchall()
        for r in rows:                      # MySQL returns Decimal for SUM
            r["present"] = int(r["present"])
            r["total"] = int(r["total"])
        return rows

    # ------------------------------------------------------------ users
    def create_user(self, username, password_hash, role, full_name=""):
        with self.cursor(commit=True) as c:
            c.execute("""INSERT INTO users
                           (username, password_hash, role, full_name)
                         VALUES (%s, %s, %s, %s)""",
                      (username, password_hash, role, full_name))
            return c.lastrowid

    def get_user_by_username(self, username):
        with self.cursor() as c:
            c.execute("SELECT * FROM users WHERE username = %s", (username,))
            return c.fetchone()

    def list_users(self):
        with self.cursor() as c:
            c.execute("""SELECT user_id, username, role, full_name, created_at
                         FROM users ORDER BY user_id""")
            return c.fetchall()

    def delete_user(self, user_id):
        with self.cursor(commit=True) as c:
            c.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

    def user_count(self):
        with self.cursor() as c:
            c.execute("SELECT COUNT(*) AS n FROM users")
            return int(c.fetchone()["n"])
```

## `app.py`

One Flask file, one route group per member. Each member edits only their own marked block.

```python
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
```

---
---

# M1 — Login + Dashboard
**Branch:** `feat/login-dashboard`
**Files:** `core/auth.py` · `templates/base.html` · `templates/base_public.html` · `templates/login.html` · `templates/index.html` · `static/css/style.css`

### `core/auth.py`

```python
"""Session based authentication with two roles: admin and staff."""
from __future__ import annotations

from functools import wraps

from flask import session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash

ROLES = ("admin", "staff")


def hash_password(raw):
    return generate_password_hash(raw)


def verify_password(raw, hashed):
    return check_password_hash(hashed, raw)


def current_user():
    if "user_id" in session:
        return {"id": session["user_id"],
                "username": session["username"],
                "role": session["role"],
                "full_name": session.get("full_name", session["username"])}
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not current_user():
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*a, **k)
    return wrapped


def role_required(*roles):
    def deco(view):
        @wraps(view)
        def wrapped(*a, **k):
            u = current_user()
            if not u:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login", next=request.path))
            if u["role"] not in roles:
                flash("You don't have permission to open that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*a, **k)
        return wrapped
    return deco
```

### `templates/base_public.html`

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}SAMS{% endblock %} &middot; CS402.3</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body class="public">
  <main class="public-main">
    {% with msgs = get_flashed_messages(with_categories=true) %}
      {% for cat, m in msgs %}<div class="flash {{ cat }}">{{ m }}</div>{% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
    <p class="pubfoot">NSBM Green University Town &middot; School of Computing</p>
  </main>
</body>
</html>
```

### `templates/login.html`

```html
{% extends "base_public.html" %}
{% block title %}Log in{% endblock %}
{% block content %}
<form class="card auth" method="post">
  <div class="brand center">
    <div class="logo">S</div>
    <div>
      <h1>SAMS</h1>
      <span>Attendance Vision</span>
    </div>
  </div>

  <label class="field"><span>Username</span>
    <input type="text" name="username" autocomplete="username" autofocus required>
  </label>
  <label class="field"><span>Password</span>
    <input type="password" name="password" autocomplete="current-password" required>
  </label>

  <button class="btn primary lg" type="submit">Log in</button>

  <p class="hint">Ask your team lead for an account, or create one with
    <code>python manage_users.py add &lt;user&gt; &lt;pass&gt; staff</code></p>
</form>
{% endblock %}
```

### `templates/base.html`

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}SAMS{% endblock %} &middot; CS402.3</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
<div class="shell">

  <aside class="sidebar">
    <div class="brand">
      <div class="logo">S</div>
      <div><h1>SAMS</h1><span>Attendance Vision</span></div>
    </div>

    <nav>
      <a href="{{ url_for('dashboard') }}" class="{{ 'on' if request.endpoint=='dashboard' }}">Dashboard</a>
      <a href="{{ url_for('process') }}"   class="{{ 'on' if request.endpoint=='process' }}">Process sheet</a>
      <a href="{{ url_for('sessions') }}"  class="{{ 'on' if request.endpoint=='sessions' }}">Sessions</a>
      <a href="{{ url_for('students') }}"  class="{{ 'on' if request.endpoint in ['students','student','investigate'] }}">Students</a>
      {% if user and user.role == 'admin' %}
      <a href="{{ url_for('users') }}"     class="{{ 'on' if request.endpoint=='users' }}">User accounts</a>
      {% endif %}
    </nav>

    <div class="sidefoot">
      <div class="pill {{ 'ok' if db_online else 'bad' }}">
        <i></i>{{ 'MySQL connected' if db_online else 'MySQL offline' }}
      </div>
      {% if user %}
      <div class="who">
        <div class="avatar sm">{{ user.full_name[:1]|upper }}</div>
        <div><b>{{ user.full_name }}</b><span>{{ user.role|upper }}</span></div>
      </div>
      <a class="lnk" href="{{ url_for('logout') }}">Log out</a>
      {% endif %}
      <p>CS402.3 &mdash; Computer Graphics &amp; Visualization</p>
    </div>
  </aside>

  <main>
    <header class="topbar">
      <div>
        <h2>{% block heading %}{% endblock %}</h2>
        <p>{% block sub %}{% endblock %}</p>
      </div>
      <a class="btn primary" href="{{ url_for('process') }}">+ New sheet</a>
    </header>

    {% with msgs = get_flashed_messages(with_categories=true) %}
      {% for cat, m in msgs %}<div class="flash {{ cat }}">{{ m }}</div>{% endfor %}
    {% endwith %}

    {% block content %}{% endblock %}

    <footer>NSBM Green University Town &middot; School of Computing &middot; {{ year }}</footer>
  </main>
</div>
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
{% block scripts %}{% endblock %}
</body>
</html>
```

### `templates/index.html`

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block heading %}Dashboard{% endblock %}
{% block sub %}Attendance extracted from signing-sheet photographs{% endblock %}

{% block content %}
<section class="stats">
  <div class="card stat"><span>Students</span><strong>{{ n_students }}</strong><em>enrolled in CS402.3</em></div>
  <div class="card stat"><span>Sessions</span><strong>{{ n_sessions }}</strong><em>sheets processed</em></div>
  <div class="card stat"><span>Attendance</span><strong>{{ '%.1f'|format(rate) }}%</strong><em>overall rate</em></div>
  <div class="card stat"><span>Pipeline</span><strong>12</strong><em>processing stages</em></div>
</section>

<section class="grid-2">
  <div class="card">
    <h3>Attendance per student</h3>
    <canvas id="overviewChart" height="150"></canvas>
  </div>

  <div class="card">
    <h3>Recent sessions</h3>
    <table class="tbl">
      <thead><tr><th>Date</th><th>Hall</th><th>Present</th></tr></thead>
      <tbody>
      {% for s in sessions[-6:]|reverse %}
        <tr>
          <td>{{ s.session_date }}</td>
          <td>{{ s.hall or '-' }}</td>
          <td><span class="tag ok">{{ s.present or 0 }}/{{ s.total or 0 }}</span></td>
        </tr>
      {% else %}
        <tr><td colspan="3" class="empty">No sessions yet &mdash; process a signing sheet.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</section>

<section class="card">
  <h3>Class register</h3>
  <table class="tbl">
    <thead><tr><th>Index</th><th>Student</th><th>Present</th><th>Rate</th><th></th></tr></thead>
    <tbody>
    {% for r in summary %}
      <tr>
        <td class="mono">{{ r.student_no }}</td>
        <td>{{ r.title }} {{ r.name }}</td>
        <td>{{ r.present }}/{{ r.total }}</td>
        <td>
          {% set p = (r.present / r.total * 100) if r.total else 0 %}
          <div class="bar"><i style="width:{{ p }}%"></i></div>
          <small>{{ '%.0f'|format(p) }}%</small>
        </td>
        <td class="r">
          <a class="btn ghost sm" href="{{ url_for('student', student_no=r.student_no) }}">Chart</a>
          <a class="btn ghost sm" href="{{ url_for('investigate', student_no=r.student_no) }}">Verify</a>
        </td>
      </tr>
    {% else %}
      <tr><td colspan="5" class="empty">Import sams_db.sql and process a sheet.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}

{% block scripts %}<script>SAMS.overviewChart('overviewChart');</script>{% endblock %}
```

### `static/css/style.css`

```css
:root{
  --bg:#0b1120; --bg2:#0f172a; --card:#111c33; --line:#1e2b45;
  --txt:#e2e8f0; --dim:#94a3b8; --accent:#22c55e; --accent2:#38bdf8;
  --bad:#ef4444; --warn:#f59e0b; --r:14px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:15px/1.55 Inter,system-ui,sans-serif;
     -webkit-font-smoothing:antialiased}
.mono{font-family:'JetBrains Mono',monospace;font-size:13px}
.dim{color:var(--dim)} .g{color:var(--accent)} .rd{color:var(--bad)}
.r{text-align:right}
code{font-family:'JetBrains Mono',monospace;background:#0d1930;padding:2px 6px;
     border-radius:6px;color:var(--accent2);font-size:12.5px}
a{color:inherit;text-decoration:none}

.shell{display:grid;grid-template-columns:252px 1fr;min-height:100vh}

/* ---------- sidebar ---------- */
.sidebar{background:linear-gradient(180deg,#0d1626,#0b1120);
  border-right:1px solid var(--line);padding:26px 20px;display:flex;
  flex-direction:column;gap:28px;position:sticky;top:0;height:100vh}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;
  background:linear-gradient(135deg,var(--accent),#0ea5e9);font-weight:800;
  font-size:20px;color:#04140a}
.brand h1{font-size:19px;letter-spacing:.4px}
.brand span{font-size:11px;color:var(--dim);letter-spacing:1.6px;text-transform:uppercase}
nav{display:flex;flex-direction:column;gap:4px}
nav a{padding:10px 13px;border-radius:10px;color:var(--dim);font-weight:500;
  font-size:14px;border:1px solid transparent;transition:.15s}
nav a:hover{background:#132038;color:var(--txt)}
nav a.on{background:rgba(34,197,94,.12);color:var(--accent);border-color:rgba(34,197,94,.3)}
.sidefoot{margin-top:auto;font-size:11.5px;color:var(--dim)}
.pill{display:inline-flex;align-items:center;gap:8px;padding:6px 11px;
  border-radius:99px;font-size:12px;margin-bottom:12px;border:1px solid var(--line);
  background:#0d1930}
.pill i{width:8px;height:8px;border-radius:99px;background:var(--bad)}
.pill.ok i{background:var(--accent);box-shadow:0 0 8px var(--accent)}
.who{display:flex;align-items:center;gap:8px;margin:10px 0}
.who b{font-size:12.5px;color:var(--txt)}
.who span{display:block;font-size:10.5px;color:var(--dim);letter-spacing:1px}

/* ---------- layout ---------- */
main{padding:26px 34px 50px;max-width:1400px}
.topbar{display:flex;justify-content:space-between;align-items:flex-end;
  padding-bottom:20px;border-bottom:1px solid var(--line);margin-bottom:24px}
.topbar h2{font-size:25px;font-weight:700;letter-spacing:-.4px}
.topbar p{color:var(--dim);font-size:13.5px;margin-top:4px}
footer{margin-top:44px;color:var(--dim);font-size:12px;text-align:center}

.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  padding:20px 22px;margin-bottom:20px}
.card h3{font-size:15px;margin-bottom:16px;font-weight:600}
.card h3 small{color:var(--dim);font-weight:400}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:4px}
.stat span{font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:var(--dim)}
.stat strong{display:block;font-size:31px;font-weight:800;margin:6px 0 2px;letter-spacing:-1px}
.stat em{font-style:normal;font-size:12px;color:var(--dim)}

/* ---------- table ---------- */
.tbl{width:100%;border-collapse:collapse;font-size:13.5px}
.tbl th{text-align:left;font-size:11px;letter-spacing:1.1px;text-transform:uppercase;
  color:var(--dim);padding:9px 10px;border-bottom:1px solid var(--line)}
.tbl td{padding:11px 10px;border-bottom:1px solid #16233c}
.tbl tr:hover td{background:#132038}
.empty{color:var(--dim);text-align:center;padding:26px!important}
.tag{padding:3px 10px;border-radius:99px;font-size:11px;font-weight:600;
  background:rgba(34,197,94,.14);color:var(--accent)}
.tag.bad{background:rgba(239,68,68,.14);color:var(--bad)}
.tag.neutral{background:rgba(148,163,184,.14);color:var(--dim)}
.bar{height:6px;border-radius:99px;background:#1b2942;overflow:hidden;max-width:150px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.bar.sm{max-width:110px}

/* ---------- buttons ---------- */
.btn{display:inline-block;padding:9px 16px;border-radius:10px;font-size:13px;
  font-weight:600;border:1px solid var(--line);background:#152340;color:var(--txt);
  cursor:pointer;transition:.15s}
.btn:hover{border-color:var(--accent)}
.btn.primary{background:linear-gradient(135deg,var(--accent),#16a34a);
  color:#04140a;border:none}
.btn.primary:disabled{opacity:.45;cursor:not-allowed}
.btn.ghost{background:transparent}
.btn.sm{padding:6px 11px;font-size:12px}
.btn.lg{padding:13px 24px;font-size:14px;width:100%;margin-top:16px}
.lnk{color:var(--accent2);font-size:12.5px}

/* ---------- upload (M2) ---------- */
.drop{display:block;border:2px dashed #2a3d5f;border-radius:var(--r);padding:44px;
  text-align:center;cursor:pointer;transition:.2s;background:#0d1930}
.drop:hover,.drop.hot{border-color:var(--accent);background:rgba(34,197,94,.06)}
.drop .ico{font-size:34px;color:var(--accent);margin-bottom:10px}
.drop b{display:block;margin-bottom:5px}
.drop span{color:var(--dim);font-size:13px}
.field{display:block;margin-top:16px;font-size:13px;color:var(--dim)}
.field input,.field select{margin-top:7px;display:block;width:100%;padding:10px;
  border-radius:10px;border:1px solid var(--line);background:#0d1930;color:var(--txt)}
.hint{margin-top:16px;font-size:12.5px;color:var(--dim);background:#0d1930;
  padding:12px 14px;border-radius:10px;border-left:3px solid var(--accent2)}

/* ---------- steps gallery (M3) ---------- */
.steps{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.step img{width:100%;border-radius:10px;border:1px solid var(--line);display:block;background:#000}
.step figcaption{margin-top:8px;font-size:11.5px}
.step figcaption b{display:block;color:var(--accent2);margin-bottom:3px}
.step figcaption span{color:var(--dim);line-height:1.4}
.sel{background:#0d1930;color:var(--accent);border:1px solid var(--line);
  padding:6px 10px;border-radius:8px;font-size:12px;font-weight:600}
.sel.absent{color:var(--bad)}
.log{background:#080f1d;padding:14px;border-radius:10px;
  font-family:'JetBrains Mono',monospace;font-size:12px;color:#9fb3cd;
  overflow:auto;max-height:340px;white-space:pre-wrap}
summary{cursor:pointer;font-weight:600;font-size:14px}
.warn{color:var(--warn);font-size:12.5px;margin-top:8px}
.flash{padding:12px 16px;border-radius:10px;margin-bottom:16px;font-size:13.5px}
.flash.success{background:rgba(34,197,94,.12);color:var(--accent)}
.flash.error{background:rgba(239,68,68,.12);color:var(--bad)}

/* ---------- people & signatures (M5, M7) ---------- */
.person{text-align:center}
.avatar{width:52px;height:52px;border-radius:99px;margin:0 auto 10px;display:grid;
  place-items:center;font-size:21px;font-weight:700;
  background:linear-gradient(135deg,#1e3a8a,#0ea5e9);color:#fff}
.avatar.sm{width:30px;height:30px;font-size:13px;margin:0}
.person .bar{margin:10px auto 6px}
.person small{color:var(--dim);font-size:12px}
.person .row{display:flex;gap:8px;justify-content:center;margin-top:12px}
.sigs{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
.sig{background:#fff;border-radius:10px;padding:8px;border:2px solid var(--accent)}
.sig.bad{border-color:var(--bad)}
.sig img{width:100%;display:block}
.sig figcaption{background:var(--card);margin:8px -8px -8px;padding:9px;
  border-radius:0 0 8px 8px;font-size:11.5px}
.sig figcaption span{display:block;color:var(--dim);margin:3px 0}
.sig figcaption em{font-style:normal;font-weight:700;color:var(--accent)}
.sig.bad figcaption em{color:var(--bad)}
.matrix th{color:var(--accent2)}
.cellscore{text-align:center;font-family:'JetBrains Mono',monospace;
  background:rgba(34,197,94,calc(var(--v)/220))}

/* ---------- login page ---------- */
.public{display:grid;place-items:center;min-height:100vh}
.public-main{width:100%;max-width:390px;padding:20px}
.pubfoot{text-align:center;color:var(--dim);font-size:11.5px;margin-top:18px}
.auth{padding:32px 28px;margin-bottom:0}
.brand.center{flex-direction:column;text-align:center;margin-bottom:22px}
.brand.center .logo{margin:0 auto 10px}

@media(max-width:1050px){
  .shell{grid-template-columns:1fr}
  .sidebar{position:static;height:auto}
  .stats,.grid-2,.grid-3{grid-template-columns:1fr 1fr}
  main{padding:20px}
}
```

---
---

# M2 — Process sheet
**Branch:** `feat/process-page`
**Files:** `core/utils.py` · `core/preprocess.py` · `templates/process.html`

### `core/utils.py`

```python
"""Shared helpers: EXIF-safe loading, step recording, overlays, montages."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageOps


@dataclass
class Step:
    """One recorded stage of the image-processing pipeline."""
    key: str
    title: str
    description: str
    image: np.ndarray = field(repr=False, default=None)
    path: str = ""

    def as_dict(self):
        return {"key": self.key, "title": self.title,
                "description": self.description, "path": self.path}


class StepRecorder:
    """Collects every intermediate image so the report can screenshot them."""

    def __init__(self):
        self.steps: list[Step] = []

    def add(self, key, title, description, image):
        self.steps.append(Step(key, title, description, image.copy()))
        return image

    def save(self, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        for i, s in enumerate(self.steps, 1):
            fname = f"{i:02d}_{s.key}.png"
            cv2.imwrite(os.path.join(out_dir, fname), s.image)
            s.path = fname
        return [s.as_dict() for s in self.steps]


def imread_exif(path):
    """cv2.imread that honours the phone camera's EXIF rotation flag."""
    pil = ImageOps.exif_transpose(Image.open(path).convert("RGB"))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def resize_to_width(img, width):
    h, w = img.shape[:2]
    if w == width:
        return img, 1.0
    scale = width / float(w)
    return cv2.resize(img, (width, int(round(h * scale))),
                      interpolation=cv2.INTER_AREA), scale


def to_bgr(img):
    """Promote a single-channel mask to 3 channels for display."""
    return img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def filter_components(mask, min_area):
    """Drop connected components smaller than min_area."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = np.zeros_like(mask)
    kept, largest = 0, 0
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area >= min_area:
            out[labels == i] = 255
            kept += 1
            largest = max(largest, area)
    return out, kept, largest


def label_box(img, text, org, colour=(0, 200, 0)):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 4)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 1)
    return img


def montage(rows, row_height=70, pad=6, bg=(24, 24, 28), pane_width=300):
    """rows = [(label, [img, img, ...]), ...] -> one tall BGR montage."""
    tiles = []
    for label, imgs in rows:
        parts = []
        for im in imgs:
            im = to_bgr(im)
            h, w = im.shape[:2]
            scale = row_height / float(h)
            parts.append(cv2.resize(im, (max(1, int(w * scale)), row_height)))
        strip = parts[0]
        for p in parts[1:]:
            sep = np.full((row_height, pad, 3), 90, np.uint8)
            strip = np.hstack([strip, sep, p])
        pane = np.full((row_height, pane_width, 3), bg, np.uint8)
        label_box(pane, label, (8, row_height // 2 + 5), (120, 220, 255))
        tiles.append(np.hstack([pane, strip]))

    width = max(t.shape[1] for t in tiles)
    canvas = []
    for t in tiles:
        if t.shape[1] < width:
            t = np.hstack([t, np.full((t.shape[0], width - t.shape[1], 3),
                                      bg, np.uint8)])
        canvas.append(t)
        canvas.append(np.full((pad, width, 3), bg, np.uint8))
    return np.vstack(canvas)
```

### `core/preprocess.py`

```python
"""Stage 1 - grayscale, denoise, deskew, illumination flattening, binarisation."""
from __future__ import annotations

import math

import cv2
import numpy as np

import config
from core.utils import StepRecorder, resize_to_width


class Preprocessor:
    """Turns a raw smart-phone photo into a clean, deskewed binary image."""

    def __init__(self, target_width=None, logger=None):
        p = config.PIPELINE
        self.target_width = target_width or p["target_width"]
        self.log = logger or (lambda *a, **k: None)

    # ------------------------------------------------------- primitives
    @staticmethod
    def grayscale(bgr):
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def denoise(gray):
        c = config.PIPELINE["bilateral"]
        # bilateral keeps thin pen strokes sharp while removing sensor noise
        return cv2.bilateralFilter(gray, c["d"], c["sigmaColor"], c["sigmaSpace"])

    @staticmethod
    def flatten_illumination(gray):
        """Remove the uneven lamp / shadow gradient by background division."""
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k)
        background = cv2.GaussianBlur(background, (0, 0), 9)
        return cv2.divide(gray, background, scale=255)

    @staticmethod
    def binarize(gray):
        c = config.PIPELINE["adaptive"]
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, c["blockSize"], c["C"])

    @staticmethod
    def clean(binary):
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        return cv2.morphologyEx(binary, cv2.MORPH_OPEN, k, iterations=1)

    # ---------------------------------------------------------- deskew
    @staticmethod
    def estimate_skew(binary):
        """Median inclination of the long horizontal rules of the table."""
        h, w = binary.shape
        kern = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 25), 1))
        rules = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kern)
        lines = cv2.HoughLinesP(rules, 1, np.pi / 720, threshold=100,
                                minLineLength=w // 5, maxLineGap=25)
        if lines is None:
            return 0.0
        limit = config.PIPELINE["deskew_max_angle"]
        angles = []
        for x1, y1, x2, y2 in lines[:, 0]:
            a = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(a) <= limit:
                angles.append(a)
        return float(np.median(angles)) if angles else 0.0

    @staticmethod
    def rotate(img, angle, border=(255, 255, 255)):
        if abs(angle) < 0.05:
            return img
        h, w = img.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        flags = cv2.INTER_NEAREST if img.ndim == 2 else cv2.INTER_CUBIC
        bval = 0 if img.ndim == 2 else border
        return cv2.warpAffine(img, m, (w, h), flags=flags,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=bval)

    # ------------------------------------------------------------- run
    def run(self, bgr):
        rec = StepRecorder()
        rec.add("original", "Original capture",
                "Raw smart-phone photograph of the signing sheet.", bgr)

        resized, scale = resize_to_width(bgr, self.target_width)
        rec.add("resized", f"Normalised size ({self.target_width} px)",
                "Every sheet is processed at one fixed working resolution so "
                "all kernel sizes and thresholds stay comparable.", resized)

        gray = self.grayscale(resized)
        rec.add("grayscale", "Grayscale conversion",
                "BGR to a single luminance channel; the colour of the pen is "
                "ignored at this stage.", gray)

        den = self.denoise(gray)
        rec.add("denoised", "Bilateral denoising",
                "Edge-preserving smoothing removes camera noise but keeps the "
                "thin pen strokes intact.", den)

        # skew is measured on a quick binary, then the colour image is rotated
        angle = self.estimate_skew(self.binarize(den))
        resized = self.rotate(resized, angle)
        gray = self.grayscale(resized)
        den = self.denoise(gray)
        rec.add("deskewed", f"Deskew ({angle:+.2f} deg)",
                "A Hough transform on the long table rules gives the tilt of "
                "the page; the image is rotated back to horizontal.", resized)

        flat = self.flatten_illumination(den)
        rec.add("illumination", "Illumination flattening",
                "Morphological closing estimates the paper background; dividing "
                "by it removes shadows and hot-spots.", flat)

        binary = self.binarize(flat)
        rec.add("binarized", "Adaptive binarisation",
                "Gaussian adaptive threshold (block 41, C 12): ink becomes "
                "white, paper becomes black.", binary)

        binary = self.clean(binary)
        rec.add("morphology", "Morphological opening",
                "A 2x2 opening deletes isolated speckles left by JPEG "
                "compression.", binary)

        self.log(f"  deskew angle .......... {angle:+.2f} deg")
        return {"color": resized, "gray": flat, "binary": binary,
                "angle": angle, "scale": scale, "recorder": rec}
```

### `templates/process.html`

```html
{% extends "base.html" %}
{% block title %}Process{% endblock %}
{% block heading %}Process a signing sheet{% endblock %}
{% block sub %}Upload the photograph and info.xml &mdash; equivalent to
<code>python sams.py 05.07.2019.jpeg info.xml</code>{% endblock %}

{% block content %}
<form class="card upload" method="post" enctype="multipart/form-data">
  <label class="drop" id="drop">
    <input type="file" name="sheet" id="sheet" accept="image/*" hidden>
    <div class="drop-in">
      <div class="ico">&#8681;</div>
      <b>Drop the signing-sheet photo here</b>
      <span id="fname">PNG or JPG &mdash; straight from a smart phone</span>
    </div>
  </label>

  <label class="field">
    <span>info.xml (optional &mdash; defaults to the bundled file)</span>
    <input type="file" name="info" accept=".xml">
  </label>

  <div class="hint">
    <b>The session date is read from the file name</b> (for example
    <code>05.07.2019.jpeg</code>), exactly as on the coursework command line.
    Every stage of the pipeline is rendered on the next screen so the
    screenshots can go straight into the report.
  </div>

  <button class="btn primary lg" type="submit">Process sheet</button>
</form>
{% endblock %}

{% block scripts %}<script>SAMS.dropzone();</script>{% endblock %}
```

---
---

# M3 — Result
**Branch:** `feat/result-page`
**Files:** `core/table_detector.py` · `core/signature_detector.py` · `core/pipeline.py` · `templates/result.html`

### `core/table_detector.py`

```python
"""Stage 2 - locate the student table and cut it into cells."""
from __future__ import annotations

from dataclasses import dataclass

import cv2

import config
from core.utils import label_box


@dataclass
class TableGrid:
    x: int
    y: int
    w: int
    h: int
    xs: list          # absolute column separator positions
    ys: list          # absolute row separator positions
    fallback: bool = False

    @property
    def n_cols(self):
        return len(self.xs) - 1

    @property
    def n_rows(self):
        return len(self.ys) - 1

    def cell(self, row, col):
        """(x1, y1, x2, y2) of one cell."""
        return self.xs[col], self.ys[row], self.xs[col + 1], self.ys[row + 1]


class TableDetector:
    """Morphological line extraction plus projection profiling."""

    def __init__(self, expected_cols=5, logger=None):
        self.expected_cols = expected_cols
        self.log = logger or (lambda *a, **k: None)

    # ---------------------------------------------------------- helpers
    @staticmethod
    def _lines(binary):
        t = config.TABLE
        h, w = binary.shape
        hk = cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(15, w // t["h_kernel_div"]), 1))
        vk = cv2.getStructuringElement(
            cv2.MORPH_RECT, (1, max(15, h // t["v_kernel_div"])))
        horiz = cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk, iterations=1)
        vert = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk, iterations=1)
        horiz = cv2.dilate(horiz,
                           cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1)))
        vert = cv2.dilate(vert,
                          cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
        return horiz, vert

    @staticmethod
    def _peaks(profile, vote):
        """Group consecutive above-threshold indices, return their centres."""
        import numpy as np
        hits = np.where(profile >= vote)[0]
        if hits.size == 0:
            return []
        groups, start, prev = [], hits[0], hits[0]
        for v in hits[1:]:
            if v - prev > 4:
                groups.append(int((start + prev) // 2))
                start = v
            prev = v
        groups.append(int((start + prev) // 2))
        return groups

    # ------------------------------------------------------------- run
    def detect(self, binary, colour, n_students, recorder=None):
        t = config.TABLE
        H, W = binary.shape
        horiz, vert = self._lines(binary)
        grid = cv2.bitwise_or(horiz, vert)

        if recorder is not None:
            recorder.add("h_lines", "Horizontal rule extraction",
                         "Opening with a wide, one-pixel-tall kernel keeps only "
                         "the horizontal rules of the table.", horiz)
            recorder.add("v_lines", "Vertical rule extraction",
                         "Opening with a tall, one-pixel-wide kernel keeps only "
                         "the vertical rules.", vert)
            recorder.add("grid", "Reconstructed table skeleton",
                         "A bitwise OR of both rule masks rebuilds the grid.",
                         grid)

        # ---- pick the student table (the contour with the most rules)
        cnts, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
        best, best_rows = None, -1
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w < 0.30 * W or h < 0.030 * H:
                continue
            prof = (horiz[y:y + h, x:x + w] > 0).sum(axis=1)
            rows = len(self._peaks(prof, t["line_vote"] * w))
            if rows > best_rows:
                best, best_rows = (x, y, w, h), rows

        if best is None:                       # nothing found - use full page
            best = (0, 0, W, H)
        x, y, w, h = best

        # ---- projection profiling inside the table ROI
        hp = (horiz[y:y + h, x:x + w] > 0).sum(axis=1)
        vp = (vert[y:y + h, x:x + w] > 0).sum(axis=0)
        ys = [y + p for p in self._peaks(hp, t["line_vote"] * w)]
        xs = [x + p for p in self._peaks(vp, t["line_vote"] * h)]

        fallback = False
        # ---- fallback: the layout is STATIC, so the proportions are known
        if len(xs) != self.expected_cols + 1:
            xs = [int(round(x + r * w)) for r in t["column_ratios"]]
            fallback = True
        if len(ys) < n_students + 2:
            band = h / float(n_students + 1)
            ys = [int(round(y + i * band)) for i in range(n_students + 2)]
            fallback = True

        ys = sorted(ys)[: n_students + 2]      # header row + n student rows
        grid_obj = TableGrid(x, y, w, h, sorted(xs), ys, fallback)

        if recorder is not None:
            overlay = colour.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 165, 255), 3)
            for cx in grid_obj.xs:
                cv2.line(overlay, (cx, y), (cx, y + h), (255, 120, 0), 2)
            for cy in grid_obj.ys:
                cv2.line(overlay, (x, cy), (x + w, cy), (0, 220, 0), 2)
            label_box(overlay, "STUDENT TABLE", (x, max(20, y - 10)),
                      (0, 165, 255))
            recorder.add("table", "Table localisation",
                         f"Student table found at ({x},{y}) size {w}x{h}; "
                         f"{grid_obj.n_cols} columns by {grid_obj.n_rows} rows"
                         + (" [static-layout fallback]" if fallback else ""),
                         overlay)

            cells = colour.copy()
            for r in range(1, grid_obj.n_rows):
                x1, y1, x2, y2 = grid_obj.cell(r, grid_obj.n_cols - 1)
                cv2.rectangle(cells, (x1, y1), (x2, y2), (255, 0, 200), 2)
                label_box(cells, f"#{r}", (x1 + 5, y1 + 20), (255, 0, 200))
            recorder.add("cells", "Signature cell segmentation",
                         "The last column of every student row is isolated - "
                         "these are the regions of interest.", cells)

        self.log(f"  table ................. {w}x{h} @ ({x},{y})")
        self.log(f"  grid .................. {grid_obj.n_cols} cols x "
                 f"{grid_obj.n_rows} rows"
                 f"{'  (fallback)' if fallback else ''}")
        return grid_obj
```

### `core/signature_detector.py`

```python
"""Stage 3 - measure the ink in each signature cell -> present / absent."""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

import config
from core.utils import filter_components, montage


@dataclass
class CellDecision:
    row: int
    student_no: str
    name: str
    present: bool
    ink_ratio: float
    components: int
    largest: int
    confidence: float
    bbox: tuple
    crop: np.ndarray = field(repr=False, default=None)
    mask: np.ndarray = field(repr=False, default=None)

    @property
    def status(self):
        return "present" if self.present else "absent"

    def as_dict(self):
        return {"row": self.row, "student_no": self.student_no,
                "name": self.name, "status": self.status,
                "ink_ratio": round(self.ink_ratio * 100, 3),
                "components": self.components,
                "confidence": round(self.confidence * 100, 1)}


class SignatureDetector:
    """Colour-independent ink measurement (blue, black or red pens)."""

    def __init__(self, logger=None):
        self.cfg = config.SIGNATURE
        self.log = logger or (lambda *a, **k: None)

    # ------------------------------------------------------------ ink
    def ink_mask(self, cell_bgr):
        h, w = cell_bgr.shape[:2]
        gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)

        # local illumination flattening so the paper reaches ~255
        k = cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(3, w // 6) | 1, max(3, h // 3) | 1))
        bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k)
        bg = cv2.GaussianBlur(bg, (0, 0), 5)
        norm = cv2.divide(gray, bg, scale=255)

        # (a) dark strokes - black and dark blue pens
        _, dark = cv2.threshold(norm, self.cfg["dark_threshold"], 255,
                                cv2.THRESH_BINARY_INV)

        # (b) saturated strokes - blue / red / green pens on white paper
        hsv = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
        sat = cv2.inRange(hsv,
                          (0, self.cfg["sat_min"], self.cfg["val_min"]),
                          (180, 255, self.cfg["val_max"]))

        mask = cv2.bitwise_or(dark, sat)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                np.ones((2, 2), np.uint8))
        return mask

    # ------------------------------------------------------------ run
    def analyse(self, colour, grid, students, recorder=None):
        cfg = self.cfg
        decisions, rows_for_montage = [], []

        for i, st in enumerate(students):
            row = i + 1                                  # row 0 = header
            if row >= grid.n_rows:
                break
            x1, y1, x2, y2 = grid.cell(row, grid.n_cols - 1)
            mx = int((x2 - x1) * cfg["cell_margin_x"])
            my = int((y2 - y1) * cfg["cell_margin_y"])
            cx1, cy1 = max(0, x1 + mx), max(0, y1 + my)
            cx2 = min(colour.shape[1], x2 - mx)
            cy2 = min(colour.shape[0], y2 - my)
            if cx2 <= cx1 or cy2 <= cy1:
                continue
            crop = colour[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue

            mask = self.ink_mask(crop)
            mask, comps, largest = filter_components(
                mask, cfg["min_component_area"])

            area = mask.shape[0] * mask.shape[1]
            ratio = float(cv2.countNonZero(mask)) / area

            present = ratio >= cfg["ink_ratio_threshold"] and comps >= 1
            if present:
                conf = min(1.0, ratio / cfg["strong_ratio"])
            else:
                conf = min(1.0, 1.0 - ratio / cfg["ink_ratio_threshold"])

            decisions.append(CellDecision(
                row=row, student_no=st.index, name=st.name, present=present,
                ink_ratio=ratio, components=comps, largest=largest,
                confidence=conf, bbox=(cx1, cy1, cx2, cy2),
                crop=crop.copy(), mask=mask.copy()))

            rows_for_montage.append(
                (f"{st.index} {'PRESENT' if present else 'ABSENT '} "
                 f"{ratio * 100:5.2f}%", [crop, mask]))

            self.log(f"  [{row}] {st.index}  ink={ratio * 100:6.2f}%  "
                     f"blobs={comps:<3} -> "
                     f"{'PRESENT' if present else 'ABSENT'}")

        if recorder is not None and rows_for_montage:
            recorder.add(
                "signatures", "Per-cell ink extraction",
                "Left: the cropped signature cell. Right: the colour-independent "
                "ink mask (dark stroke OR high saturation) after small-component "
                "removal. Ink coverage is compared against the "
                f"{config.SIGNATURE['ink_ratio_threshold'] * 100:.1f}% threshold.",
                montage(rows_for_montage))

            verdict = colour.copy()
            for d in decisions:
                c = (0, 200, 0) if d.present else (0, 0, 255)
                cv2.rectangle(verdict, (d.bbox[0], d.bbox[1]),
                              (d.bbox[2], d.bbox[3]), c, 3)
                cv2.putText(verdict, d.status.upper(),
                            (d.bbox[0] + 6, d.bbox[1] + 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)
            recorder.add("verdict", "Attendance verdict",
                         "Green = signature detected (present), "
                         "red = empty cell (absent).", verdict)

        return decisions
```

### `core/pipeline.py`

```python
"""Glues pre-processing -> table detection -> signature detection -> database."""
from __future__ import annotations

import os
import json
import datetime as dt

import cv2

import config
from core.utils import imread_exif
from core.preprocess import Preprocessor
from core.table_detector import TableDetector
from core.signature_detector import SignatureDetector
from core.xml_parser import InfoXmlParser, parse_date_from_filename
from core.database import Database


class AttendancePipeline:
    def __init__(self, logger=print):
        self.log = logger or (lambda *a, **k: None)
        self.pre = Preprocessor(logger=self.log)
        self.tab = TableDetector(logger=self.log)
        self.sig = SignatureDetector(logger=self.log)
        self.xml = InfoXmlParser()

    # -------------------------------------------------------------- run
    def process(self, image_path, xml_path=None, job_name=None,
                save_steps=True):
        xml_path = xml_path or config.DEFAULT_XML
        info = self.xml.parse(xml_path)

        # the command line supplies the date via the file name
        file_date = parse_date_from_filename(image_path)
        if file_date:
            info.session.date = file_date

        self.log(f"\n[1/5] Loading  : {os.path.basename(image_path)}")
        bgr = imread_exif(image_path)
        self.log(f"      resolution ......... {bgr.shape[1]}x{bgr.shape[0]}")

        self.log("[2/5] Pre-processing (grayscale, denoise, deskew, binarise)")
        pp = self.pre.run(bgr)
        rec = pp["recorder"]

        self.log("[3/5] Table detection and cell segmentation")
        grid = self.tab.detect(pp["binary"], pp["color"],
                               len(info.students), recorder=rec)

        self.log("[4/5] Signature analysis")
        decisions = self.sig.analyse(pp["color"], grid, info.students,
                                     recorder=rec)

        job = job_name or (
            f"{os.path.splitext(os.path.basename(image_path))[0]}_"
            f"{dt.datetime.now():%Y%m%d%H%M%S}")
        out_dir = os.path.join(config.OUTPUT_DIR, job)
        steps = rec.save(out_dir) if save_steps else []

        self._store_signature_crops(decisions, info)

        result = {
            "job": job,
            "image": os.path.basename(image_path),
            "out_dir": out_dir,
            "xml_path": xml_path,
            "subject_code": info.subject_code,
            "subject_title": info.subject_title,
            "session": {"date": info.session.date.isoformat(),
                        "start": info.session.start,
                        "end": info.session.end,
                        "lecturer": info.session.lecturer,
                        "hall": info.session.hall},
            "skew": round(pp["angle"], 2),
            "grid": {"cols": grid.n_cols, "rows": grid.n_rows,
                     "fallback": grid.fallback},
            "steps": steps,
            "records": [d.as_dict() for d in decisions],
        }
        if save_steps:
            with open(os.path.join(out_dir, "result.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
        self.log(f"[5/5] Steps written to {out_dir}")
        return result, info, decisions

    # ------------------------------------------------- signature archive
    @staticmethod
    def _store_signature_crops(decisions, info):
        """Collect a sample of every signature for investigate.py."""
        for d in decisions:
            if not d.present or d.crop is None:
                continue
            folder = os.path.join(config.SIGN_DIR, d.student_no)
            os.makedirs(folder, exist_ok=True)
            cv2.imwrite(
                os.path.join(folder, f"{info.session.date.isoformat()}.png"),
                d.crop)

    # -------------------------------------------------------- persistence
    def persist(self, result, info=None, records=None):
        """Write the (possibly user-corrected) result into sams_db."""
        db = Database()
        db.upsert_subject(result["subject_code"], result["subject_title"])
        if info is not None:
            db.upsert_students(info.students, result["subject_code"])

        s = result["session"]
        session_id = db.upsert_session(result["subject_code"], s["date"],
                                       s["start"], s["end"], s["lecturer"],
                                       s["hall"], result["image"])
        rows = records or [(r["student_no"], r["status"])
                           for r in result["records"]]
        db.save_attendance(session_id, rows)
        return session_id
```

### `templates/result.html`

```html
{% extends "base.html" %}
{% block title %}Result{% endblock %}
{% block heading %}{{ r.image }}{% endblock %}
{% block sub %}{{ r.session.date }} &middot; {{ r.session.start }}&ndash;{{ r.session.end }}
&middot; Hall {{ r.session.hall or '-' }} &middot; {{ r.session.lecturer }}{% endblock %}

{% block content %}
{% set present = r.records|selectattr('status','equalto','present')|list|length %}
<section class="stats">
  <div class="card stat"><span>Present</span><strong class="g">{{ present }}</strong><em>signatures found</em></div>
  <div class="card stat"><span>Absent</span><strong class="rd">{{ r.records|length - present }}</strong><em>empty cells</em></div>
  <div class="card stat"><span>Skew corrected</span><strong>{{ r.skew }}&deg;</strong><em>page rotation</em></div>
  <div class="card stat"><span>Grid</span><strong>{{ r.grid.cols }}&times;{{ r.grid.rows }}</strong>
    <em>{{ 'static fallback' if r.grid.fallback else 'detected' }}</em></div>
</section>

<section class="card">
  <h3>Image-processing stages <small>(report screenshots)</small></h3>
  <div class="steps">
    {% for s in r.steps %}
    <figure class="step">
      <a href="{{ url_for('output_file', job=r.job, filename=s.path) }}" target="_blank">
        <img src="{{ url_for('output_file', job=r.job, filename=s.path) }}" alt="{{ s.title }}">
      </a>
      <figcaption><b>{{ loop.index }}. {{ s.title }}</b><span>{{ s.description }}</span></figcaption>
    </figure>
    {% endfor %}
  </div>
</section>

<form class="card" method="post" action="{{ url_for('save_job', job=r.job) }}">
  <h3>Detected attendance <small>&mdash; correct any row before saving</small></h3>
  <table class="tbl">
    <thead><tr><th>#</th><th>Index</th><th>Name</th><th>Ink coverage</th>
      <th>Confidence</th><th>Status</th></tr></thead>
    <tbody>
    {% for rec in r.records %}
      <tr>
        <td>{{ loop.index }}</td>
        <td class="mono">{{ rec.student_no }}</td>
        <td>{{ rec.name }}</td>
        <td><div class="bar sm"><i style="width:{{ [rec.ink_ratio*10, 100]|min }}%"></i></div>
            <small class="mono">{{ rec.ink_ratio }} %</small></td>
        <td class="mono">{{ rec.confidence }} %</td>
        <td>
          <select name="status_{{ rec.student_no }}" class="sel {{ rec.status }}">
            <option value="present" {{ 'selected' if rec.status=='present' }}>PRESENT</option>
            <option value="absent"  {{ 'selected' if rec.status=='absent' }}>ABSENT</option>
          </select>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <button class="btn primary lg" type="submit" {{ 'disabled' if not db_online }}>Save to sams_db</button>
  {% if not db_online %}<p class="warn">Start MySQL in XAMPP to enable saving.</p>{% endif %}
</form>

<details class="card">
  <summary>Console log</summary>
  <pre class="log">{{ logs|join('\n') }}</pre>
</details>
{% endblock %}

{% block scripts %}<script>SAMS.selects();</script>{% endblock %}
```

---
---

# M4 — Sessions
**Branch:** `feat/sessions-page`
**Files:** `core/xml_parser.py` · `info.xml` · `sams.py` · `templates/sessions.html`

### `info.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- info.xml : student indices and subject related information (Figure 1) -->
<attendance>
    <subject code="CS402.3" title="Computer Graphics and Visualization"/>

    <session date="2019-07-05" start="13:00" end="16:00"
             lecturer="Dr. Rasika Ranaweera" hall="L104"/>

    <students>
        <student no="1">
            <index>10000409</index><title>Ms</title>
            <name>M S Dilshanika Perera</name>
        </student>
        <student no="2">
            <index>10009301</index><title>Mr</title>
            <name>C W M A Shehan Abeyrathne</name>
        </student>
        <student no="3">
            <index>10009302</index><title>Mr</title>
            <name>B A K M Chithrananda</name>
        </student>
        <student no="4">
            <index>10009303</index><title>Ms</title>
            <name>W Shashini Minosha De Silva</name>
        </student>
        <student no="5">
            <index>10009304</index><title>Mr</title>
            <name>K L Udara Maduranga Liyanage</name>
        </student>
        <student no="6">
            <index>10009306</index><title>Mr</title>
            <name>Hansa Anuradha Wickramanayake</name>
        </student>
    </students>
</attendance>
```

### `core/xml_parser.py`

```python
"""Reads info.xml (Figure 1) - student indices and subject information."""
from __future__ import annotations

import os
import re
import datetime as dt
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Student:
    no: int
    index: str
    title: str
    name: str


@dataclass
class SessionInfo:
    date: dt.date
    start: str
    end: str
    lecturer: str
    hall: str


@dataclass
class SheetInfo:
    subject_code: str
    subject_title: str
    session: SessionInfo
    students: list


_DATE_PATTERNS = [
    (r"(\d{4})[.\-_](\d{1,2})[.\-_](\d{1,2})", ("y", "m", "d")),
    (r"(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{4})", ("d", "m", "y")),
]


def parse_date_from_filename(path):
    """'05.07.2019.jpeg' or '2019-07-05.png' -> datetime.date, else None."""
    stem = os.path.splitext(os.path.basename(path))[0]
    for pattern, order in _DATE_PATTERNS:
        m = re.search(pattern, stem)
        if not m:
            continue
        vals = dict(zip(order, m.groups()))
        try:
            return dt.date(int(vals["y"]), int(vals["m"]), int(vals["d"]))
        except ValueError:
            continue
    return None


class InfoXmlParser:
    def parse(self, path) -> SheetInfo:
        if not os.path.exists(path):
            raise FileNotFoundError(f"info.xml not found: {path}")
        root = ET.parse(path).getroot()

        subj = root.find("subject")
        code = subj.get("code", "CS402.3") if subj is not None else "CS402.3"
        title = subj.get("title", "") if subj is not None else ""

        s = root.find("session")
        if s is not None:
            session = SessionInfo(
                date=dt.date.fromisoformat(s.get("date",
                                                 dt.date.today().isoformat())),
                start=s.get("start", "13:00"),
                end=s.get("end", "16:00"),
                lecturer=s.get("lecturer", ""),
                hall=s.get("hall", ""))
        else:
            session = SessionInfo(dt.date.today(), "13:00", "16:00", "", "")

        students = []
        for i, node in enumerate(root.findall("./students/student"), 1):
            students.append(Student(
                no=int(node.get("no", i)),
                index=node.findtext("index", "").strip(),
                title=node.findtext("title", "").strip(),
                name=node.findtext("name", "").strip()))

        if not students:
            raise ValueError("info.xml contains no <student> records")
        return SheetInfo(code, title, session, students)
```

### `sams.py`

```python
#!/usr/bin/env python
"""
SAMS - Student Attendance Management System
CS402.3 Computer Graphics and Visualization

    $ python sams.py 05.07.2019.jpeg info.xml
"""
from __future__ import annotations

import os
import sys
import argparse

import config
from core.pipeline import AttendancePipeline
from core.database import Database

G, R, Y, C, B, X = ("\033[92m", "\033[91m", "\033[93m",
                    "\033[96m", "\033[1m", "\033[0m")


def banner():
    print(f"{C}{'=' * 66}\n"
          f"  SAMS  |  Student Attendance Management System\n"
          f"  CS402.3 - Computer Graphics and Visualization\n"
          f"{'=' * 66}{X}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Process a signing-sheet photograph and store attendance.")
    ap.add_argument("image", help="signing sheet image, e.g. 05.07.2019.jpeg")
    ap.add_argument("info", nargs="?", default=config.DEFAULT_XML,
                    help="info.xml with the student indices")
    ap.add_argument("--no-db", action="store_true",
                    help="do not write to MySQL")
    ap.add_argument("--no-steps", action="store_true",
                    help="do not save the intermediate step images")
    args = ap.parse_args(argv)

    if not os.path.exists(args.image):
        print(f"{R}ERROR:{X} image not found: {args.image}")
        return 2

    banner()
    pipeline = AttendancePipeline(logger=print)
    result, info, decisions = pipeline.process(
        args.image, args.info, save_steps=not args.no_steps)

    # ------------------------------------------------------------ report
    print(f"\n{B}Subject :{X} {result['subject_code']} - "
          f"{result['subject_title']}")
    s = result["session"]
    print(f"{B}Session :{X} {s['date']}  {s['start']}-{s['end']}  "
          f"Hall {s['hall'] or '-'}  ({s['lecturer'] or '-'})")
    print(f"{B}Skew    :{X} {result['skew']:+.2f} deg     "
          f"{B}Grid:{X} {result['grid']['cols']} x {result['grid']['rows']}"
          f"{'  (static-layout fallback)' if result['grid']['fallback'] else ''}\n")

    print(f"{B}{'No':<4}{'Student No':<13}{'Name':<34}{'Ink %':>8}"
          f"{'Conf':>7}  Status{X}")
    print("-" * 78)
    for i, d in enumerate(decisions, 1):
        col = G if d.present else R
        print(f"{i:<4}{d.student_no:<13}{d.name[:33]:<34}"
              f"{d.ink_ratio * 100:>7.2f}%{d.confidence * 100:>6.0f}%  "
              f"{col}{d.status.upper()}{X}")
    print("-" * 78)
    present = sum(1 for d in decisions if d.present)
    total = max(1, len(decisions))
    print(f"{B}Present: {G}{present}{X}{B} / {total}    "
          f"Absent: {R}{total - present}{X}{B} / {total}    "
          f"Rate: {present / total * 100:.1f} %{X}")

    # ------------------------------------------------------------ store
    if not args.no_db:
        try:
            db = Database()
            if not db.ping():
                db.bootstrap()
            sid = pipeline.persist(result, info)
            print(f"\n{G}Stored in sams_db{X}  (session_id = {sid})")
        except Exception as exc:                       # noqa: BLE001
            print(f"\n{Y}WARNING:{X} could not write to MySQL -> {exc}")
            print("        Start MySQL in XAMPP and re-run, "
                  "or pass --no-db to skip.")

    print(f"\nStep images: {result['out_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `templates/sessions.html`

```html
{% extends "base.html" %}
{% block title %}Sessions{% endblock %}
{% block heading %}Sessions{% endblock %}
{% block sub %}One row per processed signing sheet{% endblock %}
{% block content %}
<section class="card">
  <table class="tbl">
    <thead><tr><th>#</th><th>Date</th><th>Time</th><th>Lecturer</th>
      <th>Hall</th><th>Source image</th><th>Present</th></tr></thead>
    <tbody>
    {% for s in sessions %}
      <tr>
        <td>{{ s.session_id }}</td>
        <td>{{ s.session_date }}</td>
        <td class="mono">{{ '%s'|format(s.start_time) }}</td>
        <td>{{ s.lecturer or '-' }}</td>
        <td>{{ s.hall or '-' }}</td>
        <td class="mono dim">{{ s.source_image or '-' }}</td>
        <td><span class="tag ok">{{ s.present or 0 }}/{{ s.total or 0 }}</span></td>
      </tr>
    {% else %}
      <tr><td colspan="7" class="empty">No sessions stored yet.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}
```

---
---

# M5 — Students
**Branch:** `feat/students-page`
**Files:** `templates/students.html`

### `templates/students.html`

```html
{% extends "base.html" %}
{% block title %}Students{% endblock %}
{% block heading %}Students{% endblock %}
{% block sub %}Open a student for the attendance visualization{% endblock %}
{% block content %}
<section class="grid-3">
{% for r in summary %}
  {% set p = (r.present / r.total * 100) if r.total else 0 %}
  <div class="card person">
    <div class="avatar">{{ r.name[:1] }}</div>
    <b>{{ r.title }} {{ r.name }}</b>
    <span class="mono dim">{{ r.student_no }}</span>
    <div class="bar"><i style="width:{{ p }}%"></i></div>
    <small>{{ r.present }}/{{ r.total }} sessions &middot; {{ '%.0f'|format(p) }} %</small>
    <div class="row">
      <a class="btn ghost sm" href="{{ url_for('student', student_no=r.student_no) }}">Attendance</a>
      <a class="btn ghost sm" href="{{ url_for('investigate', student_no=r.student_no) }}">Signatures</a>
    </div>
  </div>
{% else %}
  <p class="empty">No students &mdash; import sams_db.sql or run sams.py once.</p>
{% endfor %}
</section>
{% endblock %}
```

---
---

# M6 — Student detail
**Branch:** `feat/student-detail`
**Files:** `core/visualization.py` · `infovis.py` · `static/js/app.js` · `templates/student.html`

### `core/visualization.py`

```python
"""Data-visualization module (matplotlib) used by infovis.py."""
from __future__ import annotations

import os
import sys
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

PRESENT, ABSENT, ACCENT = "#22c55e", "#ef4444", "#38bdf8"

plt.rcParams.update({
    "figure.facecolor": "#0f172a", "axes.facecolor": "#111c33",
    "axes.edgecolor": "#334155", "axes.labelcolor": "#cbd5e1",
    "text.color": "#e2e8f0", "xtick.color": "#94a3b8",
    "ytick.color": "#94a3b8", "grid.color": "#1e293b",
    "font.size": 9,
})


def open_file(path):
    """Open a saved chart with the operating system's default viewer."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)                       # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:                                # noqa: BLE001
        pass


def student_dashboard(student, rows, out_path=None, show=False):
    """Three-panel attendance summary for one student."""
    labels = [r["session_date"].strftime("%d %b") for r in rows]
    values = [1 if r["status"] == "present" else 0 for r in rows]
    present, total = sum(values), len(values)
    pct = (present / total * 100) if total else 0.0

    cumulative, run = [], 0
    for i, v in enumerate(values, 1):
        run += v
        cumulative.append(run / i * 100)

    fig = plt.figure(figsize=(12, 6.5))
    gs = GridSpec(2, 3, figure=fig, hspace=.45, wspace=.35,
                  left=.07, right=.96, top=.86, bottom=.12)
    fig.suptitle(f"Attendance Summary  |  {student['title']} {student['name']}"
                 f"  ({student['student_no']})",
                 fontsize=14, fontweight="bold", y=.96)

    # (1) session timeline
    ax = fig.add_subplot(gs[0, :])
    ax.bar(labels, [1] * total,
           color=[PRESENT if v else ABSENT for v in values],
           edgecolor="#0f172a", width=.55)
    for i, v in enumerate(values):
        ax.text(i, .5, "P" if v else "A", ha="center", va="center",
                fontweight="bold", color="#0b1120")
    ax.set_ylim(0, 1.35)
    ax.set_yticks([])
    ax.set_title("Session-by-session attendance", loc="left",
                 fontweight="bold")
    ax.grid(axis="x", alpha=.15)

    # (2) donut
    ax = fig.add_subplot(gs[1, 0])
    ax.pie([present, total - present], colors=[PRESENT, ABSENT],
           startangle=90, wedgeprops=dict(width=.42, edgecolor="#0f172a"),
           labels=["Present", "Absent"], autopct="%1.0f%%", pctdistance=.78)
    ax.text(0, 0, f"{pct:.0f}%", ha="center", va="center",
            fontsize=17, fontweight="bold")
    ax.set_title("Overall ratio", loc="left", fontweight="bold")

    # (3) cumulative trend
    ax = fig.add_subplot(gs[1, 1:])
    ax.plot(labels, cumulative, marker="o", color=ACCENT, linewidth=2)
    ax.fill_between(range(total), cumulative, color=ACCENT, alpha=.12)
    ax.axhline(80, color="#f59e0b", linestyle="--", linewidth=1.2,
               label="80 % requirement")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Cumulative %")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=.2)
    ax.set_title("Cumulative attendance trend", loc="left", fontweight="bold")

    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=130)
    plt.close(fig)
    if show and out_path:
        open_file(out_path)
    return out_path


def class_overview(summary, out_path=None, show=False):
    names = [str(r["student_no"]) for r in summary]
    pcts = [float(r["present"]) / r["total"] * 100 if r["total"] else 0.0
            for r in summary]

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.barh(names, pcts, color=[PRESENT if p >= 80 else ABSENT for p in pcts])
    ax.axvline(80, color="#f59e0b", ls="--")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Attendance %")
    ax.set_title("Class attendance overview", fontweight="bold", loc="left")
    fig.tight_layout()

    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=130)
    plt.close(fig)
    if show and out_path:
        open_file(out_path)
    return out_path
```

### `infovis.py`

```python
#!/usr/bin/env python
"""
Attendance visualization for one student.

    $ python infovis.py 10000409
"""
from __future__ import annotations

import os
import sys
import argparse

import config
from core.database import Database
from core.visualization import student_dashboard, class_overview

G, R, Y, C, B, X = ("\033[92m", "\033[91m", "\033[93m",
                    "\033[96m", "\033[1m", "\033[0m")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Visualize a student's attendance summary.")
    ap.add_argument("student", nargs="?", help="student index, e.g. 10000409")
    ap.add_argument("--all", action="store_true",
                    help="class-wide overview instead of one student")
    ap.add_argument("--save", default=None, help="output PNG path")
    ap.add_argument("--show", action="store_true",
                    help="open the chart after saving")
    args = ap.parse_args(argv)

    db = Database()
    if not db.ping():
        print(f"{R}ERROR:{X} cannot reach MySQL - start it in XAMPP.")
        return 2

    out_dir = os.path.join(config.OUTPUT_DIR, "charts")

    # -------------------------------------------------- class overview
    if args.all or not args.student:
        summary = db.get_class_summary()
        path = args.save or os.path.join(out_dir, "class_overview.png")
        class_overview(summary, path, show=args.show)
        print(f"\n{B}{'Index':<12}{'Name':<34}{'P/T':>8}{'%':>9}{X}")
        print("-" * 63)
        for r in summary:
            pct = (r["present"] / r["total"] * 100) if r["total"] else 0
            col = G if pct >= 80 else (Y if pct >= 60 else R)
            print(f"{r['student_no']:<12}{r['name'][:33]:<34}"
                  f"{r['present']}/{r['total']:<6}{col}{pct:>8.1f}%{X}")
        print(f"\nChart saved to {path}")
        return 0

    # -------------------------------------------------- single student
    student = db.get_student(args.student)
    if not student:
        print(f"{R}ERROR:{X} student {args.student} not found in sams_db.")
        return 2

    rows = db.get_student_attendance(args.student)
    if not rows:
        print(f"{Y}No attendance records yet for {args.student}. "
              f"Run sams.py on a signing sheet first.{X}")
        return 1

    present = sum(1 for r in rows if r["status"] == "present")
    print(f"\n{C}{student['title']} {student['name']}  "
          f"({student['student_no']}){X}")
    print("-" * 56)
    for r in rows:
        col = G if r["status"] == "present" else R
        print(f"  {r['session_date']}  {str(r['start_time'])[:5]}  "
              f"Hall {(r['hall'] or '-'):<6} {col}{r['status'].upper()}{X}")
    print("-" * 56)
    print(f"  {B}Attendance: {present}/{len(rows)} "
          f"({present / len(rows) * 100:.1f} %){X}\n")

    path = args.save or os.path.join(out_dir, f"{args.student}.png")
    student_dashboard(student, rows, path, show=args.show)
    print(f"Chart saved to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `static/js/app.js`

```javascript
const SAMS = {
  colors: { ok: '#22c55e', bad: '#ef4444', ac: '#38bdf8',
            grid: '#1e293b', txt: '#94a3b8' },

  async overviewChart(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const d = await (await fetch('/api/overview')).json();
    new Chart(el, {
      type: 'bar',
      data: {
        labels: d.labels,
        datasets: [{
          label: 'Attendance %', data: d.values, borderRadius: 6,
          backgroundColor: d.values.map(v => v >= 80 ? SAMS.colors.ok
                                                     : SAMS.colors.bad)
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: SAMS.colors.txt } } },
        scales: {
          y: { max: 100, ticks: { color: SAMS.colors.txt },
               grid: { color: SAMS.colors.grid } },
          x: { ticks: { color: SAMS.colors.txt }, grid: { display: false } }
        }
      }
    });
  },

  async studentCharts() {
    const t = document.getElementById('timeline');
    if (t) {
      const d = await (await fetch('/api/student/' + t.dataset.student)).json();
      new Chart(t, {
        type: 'bar',
        data: {
          labels: d.labels,
          datasets: [{
            label: 'Present (1) / Absent (0)', data: d.values, borderRadius: 6,
            backgroundColor: d.values.map(v => v ? SAMS.colors.ok
                                                 : SAMS.colors.bad)
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { labels: { color: SAMS.colors.txt } } },
          scales: {
            y: { max: 1, ticks: { stepSize: 1, color: SAMS.colors.txt },
                 grid: { color: SAMS.colors.grid } },
            x: { ticks: { color: SAMS.colors.txt }, grid: { display: false } }
          }
        }
      });
    }
    const n = document.getElementById('donut');
    if (n) {
      new Chart(n, {
        type: 'doughnut',
        data: {
          labels: ['Present', 'Absent'],
          datasets: [{
            data: [+n.dataset.present, +n.dataset.absent],
            backgroundColor: [SAMS.colors.ok, SAMS.colors.bad], borderWidth: 0
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '62%',
          plugins: { legend: { labels: { color: SAMS.colors.txt } } }
        }
      });
    }
  },

  dropzone() {
    const drop = document.getElementById('drop'),
          input = document.getElementById('sheet'),
          name = document.getElementById('fname');
    if (!drop) return;
    input.addEventListener('change', () => {
      if (input.files[0]) name.textContent = input.files[0].name;
    });
    ['dragenter', 'dragover'].forEach(e => drop.addEventListener(e, ev => {
      ev.preventDefault(); drop.classList.add('hot');
    }));
    ['dragleave', 'drop'].forEach(e => drop.addEventListener(e, ev => {
      ev.preventDefault(); drop.classList.remove('hot');
    }));
    drop.addEventListener('drop', ev => {
      input.files = ev.dataTransfer.files;
      if (input.files[0]) name.textContent = input.files[0].name;
    });
  },

  selects() {
    document.querySelectorAll('.sel').forEach(s =>
      s.addEventListener('change', () => {
        s.classList.toggle('absent', s.value === 'absent');
      }));
  }
};
```

### `templates/student.html`

```html
{% extends "base.html" %}
{% block title %}{{ s.name }}{% endblock %}
{% block heading %}{{ s.title }} {{ s.name }}{% endblock %}
{% block sub %}Index {{ s.student_no }} &middot;
<code>python infovis.py {{ s.student_no }}</code>{% endblock %}

{% block content %}
{% set present = rows|selectattr('status','equalto','present')|list|length %}
{% set pct = (present / rows|length * 100) if rows else 0 %}
<section class="stats">
  <div class="card stat"><span>Attended</span><strong class="g">{{ present }}</strong><em>sessions</em></div>
  <div class="card stat"><span>Missed</span><strong class="rd">{{ rows|length - present }}</strong><em>sessions</em></div>
  <div class="card stat"><span>Rate</span><strong>{{ '%.1f'|format(pct) }}%</strong><em>of {{ rows|length }} sheets</em></div>
  <div class="card stat"><span>Eligibility</span>
    <strong class="{{ 'g' if pct>=80 else 'rd' }}">{{ 'OK' if pct>=80 else 'LOW' }}</strong>
    <em>80 % requirement</em></div>
</section>

<section class="grid-2">
  <div class="card"><h3>Session timeline</h3>
    <canvas id="timeline" height="170" data-student="{{ s.student_no }}"></canvas></div>
  <div class="card"><h3>Present vs absent</h3>
    <canvas id="donut" height="170" data-present="{{ present }}"
            data-absent="{{ rows|length - present }}"></canvas></div>
</section>

<section class="card">
  <h3>Records</h3>
  <table class="tbl">
    <thead><tr><th>Date</th><th>Time</th><th>Hall</th><th>Lecturer</th><th>Status</th></tr></thead>
    <tbody>
    {% for r in rows %}
      <tr>
        <td>{{ r.session_date }}</td>
        <td class="mono">{{ '%s'|format(r.start_time) }}</td>
        <td>{{ r.hall or '-' }}</td>
        <td>{{ r.lecturer or '-' }}</td>
        <td><span class="tag {{ 'ok' if r.status=='present' else 'bad' }}">{{ r.status|upper }}</span></td>
      </tr>
    {% else %}
      <tr><td colspan="5" class="empty">No records.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}

{% block scripts %}<script>SAMS.studentCharts();</script>{% endblock %}
```

---
---

# M7 — Investigate
**Branch:** `feat/investigate-page`
**Files:** `core/signature_verify.py` · `investigate.py` · `templates/investigate.html`

### `core/signature_verify.py`

```python
"""Signature normalisation, feature extraction and matching (investigate.py)."""
from __future__ import annotations

import os
import glob
from dataclasses import dataclass

import cv2
import numpy as np

import config
from core.signature_detector import SignatureDetector
from core.utils import filter_components


@dataclass
class Sample:
    label: str
    path: str
    image: np.ndarray          # normalised binary canvas
    features: dict


class SignatureVerifier:
    def __init__(self):
        self.cfg = config.VERIFY
        self.det = SignatureDetector()
        self.orb = cv2.ORB_create(nfeatures=400, scaleFactor=1.2)

    # ------------------------------------------------------ normalisation
    def normalise(self, bgr):
        mask = self.det.ink_mask(bgr)
        mask, _, _ = filter_components(
            mask, config.SIGNATURE["min_component_area"])
        ys, xs = np.nonzero(mask)
        if ys.size == 0:
            return None
        mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

        cw, ch = self.cfg["canvas"]
        h, w = mask.shape
        scale = min((cw - 12) / w, (ch - 12) / h)
        resized = cv2.resize(mask,
                             (max(1, int(w * scale)), max(1, int(h * scale))),
                             interpolation=cv2.INTER_AREA)
        _, resized = cv2.threshold(resized, 40, 255, cv2.THRESH_BINARY)

        canvas = np.zeros((ch, cw), np.uint8)
        y0 = (ch - resized.shape[0]) // 2
        x0 = (cw - resized.shape[1]) // 2
        canvas[y0:y0 + resized.shape[0], x0:x0 + resized.shape[1]] = resized
        return canvas

    # -------------------------------------------------------- descriptors
    def features(self, canvas):
        m = cv2.moments(canvas)
        hu = cv2.HuMoments(m).flatten()
        hu = np.sign(hu) * np.log1p(np.abs(hu) * 1e10)

        vproj = canvas.sum(axis=0).astype(np.float32)
        hproj = canvas.sum(axis=1).astype(np.float32)
        vproj = cv2.resize(vproj.reshape(1, -1), (48, 1)).flatten()
        hproj = cv2.resize(hproj.reshape(1, -1), (24, 1)).flatten()
        profile = np.concatenate([vproj, hproj])
        norm = np.linalg.norm(profile)
        profile = profile / norm if norm else profile

        _, des = self.orb.detectAndCompute(canvas, None)
        return {"hu": hu, "profile": profile, "orb": des,
                "density": float(np.count_nonzero(canvas)) / canvas.size}

    # ---------------------------------------------------------- matching
    def similarity(self, a: Sample, b: Sample) -> float:
        w = self.cfg["weights"]

        shape = float(np.exp(-cv2.matchShapes(a.image, b.image,
                                              cv2.CONTOURS_MATCH_I2, 0)))
        prof = float(np.clip(np.dot(a.features["profile"],
                                    b.features["profile"]), 0, 1))

        k = np.ones((3, 3), np.uint8)
        iters = self.cfg["overlap_dilate_iter"]
        da = cv2.dilate(a.image, k, iterations=iters)
        db = cv2.dilate(b.image, k, iterations=iters)
        inter = np.count_nonzero(cv2.bitwise_and(da, db))
        union = np.count_nonzero(cv2.bitwise_or(da, db))
        overlap = inter / union if union else 0.0

        orb = 0.0
        da_, db_ = a.features["orb"], b.features["orb"]
        if da_ is not None and db_ is not None and len(da_) > 5 and len(db_) > 5:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING)
            pairs = bf.knnMatch(da_, db_, k=2)
            good = [p[0] for p in pairs
                    if len(p) == 2 and p[0].distance < .78 * p[1].distance]
            orb = min(1.0, len(good) / float(min(len(da_), len(db_))))

        score = (w["shape"] * shape + w["profile"] * prof +
                 w["overlap"] * overlap + w["orb"] * orb) * 100
        return float(np.clip(score, 0, 100))

    # ------------------------------------------------------------- API
    def load_samples(self, student_no):
        folder = os.path.join(config.SIGN_DIR, student_no)
        samples = []
        for path in sorted(glob.glob(os.path.join(folder, "*.png"))):
            bgr = cv2.imread(path)
            if bgr is None:
                continue
            canvas = self.normalise(bgr)
            if canvas is None:
                continue
            samples.append(Sample(
                os.path.splitext(os.path.basename(path))[0],
                path, canvas, self.features(canvas)))
        return samples

    def investigate(self, student_no):
        """Pairwise comparison with an OUTLIER-RELATIVE verdict.

        Real testing showed genuine same-person signatures only score
        ~45-65% on raw pixel/shape similarity across different photographs
        (natural handwriting variation + photo/crop differences). A fixed
        global threshold therefore flagged nearly everyone. Instead, each
        sample's mean similarity to that SAME student's other samples is
        compared against that student's own group average: a sample is
        flagged only if it sits meaningfully below its own peers, i.e. it
        is unusual relative to how consistent that person's signature
        normally is - not relative to an arbitrary global number.
        """
        samples = self.load_samples(student_no)
        n = len(samples)
        if n < 2:
            return {"student_no": student_no, "samples": samples,
                    "matrix": [], "report": [], "threshold": None,
                    "error": "At least two collected signatures are required. "
                             "Process more signing sheets first."}

        matrix = [[100.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                s = self.similarity(samples[i], samples[j])
                matrix[i][j] = matrix[j][i] = round(s, 1)

        means = []
        for i in range(n):
            others = [matrix[i][j] for j in range(n) if j != i]
            means.append(float(np.mean(others)))

        floor = self.cfg["min_absolute_floor"]
        z_cut = self.cfg["outlier_z"]

        if n >= 3:
            group_mean = float(np.mean(means))
            group_std = float(np.std(means)) or 1e-6   # avoid divide-by-zero
            cutoff = group_mean - z_cut * group_std
        else:
            # only 2 samples: no statistically meaningful outlier detection
            # possible: fall back to an absolute sanity floor only, to catch
            # a clearly corrupted crop rather than genuine forgery
            group_mean, group_std, cutoff = means[0], 0.0, floor

        report = []
        for i, smp in enumerate(samples):
            mean = means[i]
            others = [matrix[i][j] for j in range(n) if j != i]
            flagged = mean < floor or (n >= 3 and mean < cutoff)
            report.append({"label": smp.label, "path": smp.path,
                           "mean": round(mean, 1),
                           "best": round(max(others), 1),
                           "worst": round(min(others), 1),
                           "match": not flagged})
        return {"student_no": student_no, "samples": samples,
                "matrix": matrix, "report": report,
                "threshold": round(cutoff, 1),
                "group_mean": round(group_mean, 1),
                "error": None}
```

### `investigate.py`

```python
#!/usr/bin/env python
"""
Signature verification for one student.

    $ python investigate.py 10000409
"""
from __future__ import annotations

import os
import sys
import argparse

import cv2
import numpy as np

import config
from core.database import Database
from core.signature_verify import SignatureVerifier
from core.utils import label_box

G, R, Y, C, B, X = ("\033[92m", "\033[91m", "\033[93m",
                    "\033[96m", "\033[1m", "\033[0m")


def build_contact_sheet(result, out_path):
    samples = result["samples"]
    tiles = []
    for smp, rep in zip(samples, result["report"]):
        img = cv2.cvtColor(smp.image, cv2.COLOR_GRAY2BGR)
        img = cv2.copyMakeBorder(img, 26, 8, 8, 8, cv2.BORDER_CONSTANT,
                                 value=(15, 23, 42))
        colour = (80, 220, 120) if rep["match"] else (80, 80, 250)
        cv2.rectangle(img, (2, 2), (img.shape[1] - 3, img.shape[0] - 3),
                      colour, 2)
        label_box(img, f"{rep['label']}  {rep['mean']:.0f}%", (10, 19), colour)
        tiles.append(img)

    per_row = 3
    rows = []
    for i in range(0, len(tiles), per_row):
        chunk = tiles[i:i + per_row]
        while len(chunk) < per_row:
            chunk.append(np.zeros_like(tiles[0]))
        rows.append(np.hstack(chunk))
    sheet = np.vstack(rows)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, sheet)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Compare the collected signatures of one student.")
    ap.add_argument("student", help="student index, e.g. 10000409")
    ap.add_argument("--save", default=None, help="output PNG path")
    args = ap.parse_args(argv)

    ver = SignatureVerifier()
    result = ver.investigate(args.student)

    db = Database()
    student = db.get_student(args.student) if db.ping() else None
    title = f"{student['title']} {student['name']}" if student else args.student

    print(f"\n{C}Signature investigation - {title} ({args.student}){X}")
    print("-" * 70)

    if result["error"]:
        print(f"{Y}{result['error']}{X}")
        print(f"Collected samples live in "
              f"{os.path.join(config.SIGN_DIR, args.student)}")
        return 1

    n = len(result["samples"])
    labels = [s.label for s in result["samples"]]

    print(f"{B}Pairwise similarity matrix (%){X}")
    print(" " * 13 + "".join(f"{l[-5:]:>9}" for l in labels))
    for i, row in enumerate(result["matrix"]):
        print(f"{labels[i]:<13}" + "".join(f"{v:>9.1f}" for v in row))

    print(f"\n{B}{'Sample':<14}{'mean':>8}{'best':>8}{'worst':>8}   Verdict{X}")
    print("-" * 70)
    flagged = 0
    for rep in result["report"]:
        col = G if rep["match"] else R
        verdict = "MATCHES" if rep["match"] else "NOT MATCHING"
        flagged += 0 if rep["match"] else 1
        print(f"{rep['label']:<14}{rep['mean']:>8.1f}{rep['best']:>8.1f}"
              f"{rep['worst']:>8.1f}   {col}{verdict}{X}")
    print("-" * 70)
    tail = (f"{G}All signatures are consistent.{X}" if not flagged
            else f"{R}{flagged} signature(s) flagged for review.{X}")
    print(f"Threshold: {result['threshold']:.0f} %   Samples: {n}   {tail}")

    path = args.save or os.path.join(config.OUTPUT_DIR, "charts",
                                     f"signatures_{args.student}.png")
    build_contact_sheet(result, path)
    print(f"\nContact sheet saved to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `templates/investigate.html`

```html
{% extends "base.html" %}
{% block title %}Signatures{% endblock %}
{% block heading %}Signature verification{% endblock %}
{% block sub %}{{ s.title }} {{ s.name }} ({{ s.student_no }}) &middot;
<code>python investigate.py {{ s.student_no }}</code>{% endblock %}

{% block content %}
{% if res.error %}
  <div class="card"><p class="empty">{{ res.error }}</p></div>
{% else %}
<section class="card">
  <h3>Collected samples</h3>
  <div class="sigs">
    {% for smp in samples %}
      {% set rep = res.report[loop.index0] %}
      <figure class="sig {{ 'ok' if rep.match else 'bad' }}">
        <img src="{{ smp.url }}" alt="{{ smp.label }}">
        <figcaption>
          <b>{{ rep.label }}</b>
          <span>mean {{ rep.mean }} % &middot; best {{ rep.best }} % &middot; worst {{ rep.worst }} %</span>
          <em>{{ 'MATCHES' if rep.match else 'NOT MATCHING' }}</em>
        </figcaption>
      </figure>
    {% endfor %}
  </div>
</section>

<section class="card">
  <h3>Pairwise similarity matrix <small>(outlier cutoff for this student: {{ res.threshold }} %)</small></h3>
  <table class="tbl matrix">
    <thead><tr><th></th>{% for r in res.report %}<th>{{ r.label }}</th>{% endfor %}</tr></thead>
    <tbody>
    {% for row in res.matrix %}
      <tr><th>{{ res.report[loop.index0].label }}</th>
      {% for v in row %}<td class="cellscore" style="--v:{{ v }}">{{ '%.0f'|format(v) }}</td>{% endfor %}
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <p class="hint">Similarity = 0.35&middot;Hu-moment shape + 0.35&middot;projection profile
     + 0.20&middot;dilated overlap (IoU) + 0.10&middot;ORB descriptor matching.
     Verdicts are relative, not absolute: real testing showed genuine same-person
     signatures only score 45&ndash;65% across different photos, so each sample is
     compared against <em>this student's own</em> average consistency &mdash; it is
     flagged only if it sits more than 1 standard deviation below their own baseline,
     not against a fixed global number.</p>
</section>
{% endif %}
{% endblock %}
```

---
---

# M8 — Accounts
**Branch:** `feat/accounts-page`
**Files:** `manage_users.py` · `templates/users.html`

### `manage_users.py`

```python
#!/usr/bin/env python
"""
Create / list / delete SAMS login accounts.

    $ python manage_users.py add admin admin123 admin "Dr Rasika Ranaweera"
    $ python manage_users.py add staff01 pass123 staff "Group Member 1"
    $ python manage_users.py list
    $ python manage_users.py delete 3
"""
import sys

from core.database import Database
from core.auth import hash_password, ROLES


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    db = Database()
    if not db.ping():
        print("ERROR: cannot reach MySQL - start it in XAMPP first.")
        return 2

    if not argv or argv[0] == "list":
        users = db.list_users()
        if not users:
            print("No accounts yet.")
        for u in users:
            print(f"  [{u['user_id']}] {u['username']:<16} "
                  f"{u['role']:<6} {u['full_name'] or ''}")
        return 0

    if argv[0] == "add":
        if len(argv) < 4:
            print("Usage: python manage_users.py add "
                  "<username> <password> <admin|staff> [full name]")
            return 2
        username, password, role = argv[1], argv[2], argv[3]
        full_name = " ".join(argv[4:]) if len(argv) > 4 else ""
        if role not in ROLES:
            print(f"role must be one of {ROLES}")
            return 2
        if db.get_user_by_username(username):
            print(f"'{username}' already exists.")
            return 1
        db.create_user(username, hash_password(password), role, full_name)
        print(f"Created {role} account '{username}'.")
        return 0

    if argv[0] == "delete" and len(argv) > 1:
        db.delete_user(int(argv[1]))
        print(f"Deleted account #{argv[1]}.")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

### `templates/users.html`

```html
{% extends "base.html" %}
{% block title %}User accounts{% endblock %}
{% block heading %}User accounts{% endblock %}
{% block sub %}Admin and staff logins for the SAMS web front-end{% endblock %}

{% block content %}
<section class="card">
  <h3>Existing accounts</h3>
  <table class="tbl">
    <thead><tr><th>Username</th><th>Role</th><th>Full name</th>
      <th>Created</th><th></th></tr></thead>
    <tbody>
    {% for u in accounts %}
      <tr>
        <td class="mono">{{ u.username }}</td>
        <td><span class="tag {{ 'ok' if u.role=='admin' else 'neutral' }}">{{ u.role|upper }}</span></td>
        <td>{{ u.full_name or '-' }}</td>
        <td class="dim">{{ u.created_at }}</td>
        <td class="r">
          <form method="post" action="{{ url_for('users_delete', user_id=u.user_id) }}"
                onsubmit="return confirm('Delete this account?')">
            <button class="btn ghost sm" type="submit">Delete</button>
          </form>
        </td>
      </tr>
    {% else %}
      <tr><td colspan="5" class="empty">No accounts yet.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</section>

<form class="card" method="post" action="{{ url_for('users_add') }}">
  <h3>Add account</h3>
  <div class="grid-3">
    <label class="field"><span>Username</span>
      <input name="username" required></label>
    <label class="field"><span>Password</span>
      <input name="password" type="password" required></label>
    <label class="field"><span>Role</span>
      <select name="role">
        <option value="staff">Staff</option>
        <option value="admin">Admin</option>
      </select></label>
  </div>
  <label class="field"><span>Full name</span><input name="full_name"></label>
  <button class="btn primary lg" type="submit">Create account</button>
</form>
{% endblock %}
```
