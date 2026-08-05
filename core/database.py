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
