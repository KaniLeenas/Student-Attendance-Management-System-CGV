"""
Flask Web Application (Module 8)
"""
from flask import Flask, render_template, request, redirect, url_for, flash
import config

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)







#student details version 01

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
