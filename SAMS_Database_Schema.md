# SAMS — Database Schema
### CS402.3 Computer Graphics and Visualization · NSBM Green University Town, School of Computing

This is the **one-time import**. Run it before starting any of the code in `SAMS_Code_By_Member.md` — every page reads from these five tables.

---

## Tables at a glance

| Table | Purpose | Written by |
|---|---|---|
| `subjects` | subject code + title, from `info.xml` | seed data, upserted again by `sams.py` |
| `students` | the 6-student roster, from `info.xml` | seed data, upserted again by `sams.py` |
| `sessions` | one row per signing sheet processed | `sams.py` → `core/pipeline.py` |
| `attendance` | present/absent per student per session | `sams.py` → `core/pipeline.py` |
| `users` | login accounts for the Flask front-end | `manage_users.py` |

`students.subject_code` and `sessions.subject_code` reference `subjects`. `attendance.session_id` references `sessions` (cascades on delete) and `attendance.student_no` references `students`. `(session_id, student_no)` is unique, so re-processing the same sheet updates the same attendance rows instead of duplicating them.

**Import — pick one:**
```bash
mysql -u root < sams_db.sql
```
```
phpMyAdmin (XAMPP) -> Import -> choose sams_db.sql -> Go
```
XAMPP defaults (user `root`, empty password) match the `DB` dict in `config.py` as-is — no edits needed for a stock XAMPP install.

---

## `sams_db.sql`

```sql
-- ==========================================================================
-- Student Attendance Management System (SAMS)
-- CS402.3 - Computer Graphics and Visualization
-- Import in phpMyAdmin (XAMPP) or:  mysql -u root < sams_db.sql
-- ==========================================================================

CREATE DATABASE IF NOT EXISTS sams_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE sams_db;

-- --------------------------------------------------------------------------
-- subjects : subject related information from info.xml
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    subject_code   VARCHAR(20)  PRIMARY KEY,
    subject_title  VARCHAR(150) NOT NULL
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- students : student records from info.xml
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    student_no    VARCHAR(20)  PRIMARY KEY,
    title         VARCHAR(10),
    name          VARCHAR(100) NOT NULL,
    subject_code  VARCHAR(20),
    FOREIGN KEY (subject_code) REFERENCES subjects(subject_code)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- sessions : one row per signing sheet / lecture
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    session_id    INT AUTO_INCREMENT PRIMARY KEY,
    subject_code  VARCHAR(20),
    session_date  DATE NOT NULL,
    start_time    TIME,
    end_time      TIME,
    lecturer      VARCHAR(100),
    hall          VARCHAR(30),
    source_image  VARCHAR(255),
    FOREIGN KEY (subject_code) REFERENCES subjects(subject_code),
    UNIQUE KEY uq_session (subject_code, session_date, start_time)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- attendance : present / absent per student per session
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id    INT NOT NULL,
    student_no    VARCHAR(20) NOT NULL,
    status        ENUM('present', 'absent') NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (student_no) REFERENCES students(student_no),
    UNIQUE KEY uq_attendance (session_id, student_no),
    INDEX idx_attendance_student (student_no)
) ENGINE=InnoDB;

-- --------------------------------------------------------------------------
-- users : login accounts for the web front-end (admin / staff)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('admin', 'staff') NOT NULL DEFAULT 'staff',
    full_name     VARCHAR(100),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ==========================================================================
-- Seed data : the subject and the six students on the five CGV sheets.
-- Attendance rows are written by sams.py after processing each image.
-- Accounts are created by manage_users.py (passwords are hashed in Python).
-- ==========================================================================
INSERT INTO subjects (subject_code, subject_title) VALUES
    ('CS402.3', 'Computer Graphics and Visualization')
ON DUPLICATE KEY UPDATE subject_title = VALUES(subject_title);

INSERT INTO students (student_no, title, name, subject_code) VALUES
    ('10000409', 'Ms', 'M S Dilshanika Perera',          'CS402.3'),
    ('10009301', 'Mr', 'C W M A Shehan Abeyrathne',      'CS402.3'),
    ('10009302', 'Mr', 'B A K M Chithrananda',           'CS402.3'),
    ('10009303', 'Ms', 'W Shashini Minosha De Silva',    'CS402.3'),
    ('10009304', 'Mr', 'K L Udara Maduranga Liyanage',   'CS402.3'),
    ('10009306', 'Mr', 'Hansa Anuradha Wickramanayake',  'CS402.3')
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    name = VALUES(name),
    subject_code = VALUES(subject_code);
```
