# SAMS — Student Attendance Management System
### CS402.3 Computer Graphics and Visualization · Group Coursework · NSBM Green University Town, School of Computing

Processes a phone photo of a paper signing sheet, detects which students signed, and stores attendance in MySQL. Built around three CLI tools plus a Flask front-end.

---

## Files in this submission

| File | What it is |
|---|---|
| `SAMS_Database_Schema.md` | the MySQL schema (`sams_db.sql`) — import this **first** |
| `SAMS_Code_By_Member.md` | full source, split into the 8 members' owned pages/branches |
| `sams_db.sql` | the schema file itself, ready to import |

---

## Project structure

Once every file from `SAMS_Code_By_Member.md` is pulled out to its own path, the folder looks like this (`data/` is created automatically on first run):

```
SAMS/
├── app.py                       # Flask app, all routes                    (M1)
├── config.py                    # paths, DB config, pipeline thresholds    (shared)
├── manage_users.py              # create/list/delete login accounts        (M8)
├── sams.py                      # CLI: process one signing sheet           (M4)
├── infovis.py                   # CLI: attendance chart for a student      (M6)
├── investigate.py               # CLI: signature consistency check         (M7)
├── info.xml                     # student roster + subject/session info    (M4)
├── requirements.txt
├── sams_db.sql                  # one-time DB import — see SAMS_Database_Schema.md
│
├── core/
│   ├── __init__.py
│   ├── auth.py                  # login, password hashing, role_required   (M1)
│   ├── database.py              # all MySQL reads/writes                   (shared)
│   ├── preprocess.py            # greyscale, denoise, deskew, binarise     (M2)
│   ├── utils.py                 # shared image helpers                     (M2)
│   ├── table_detector.py        # finds the grid / cells                  (M3)
│   ├── signature_detector.py    # ink-ratio present/absent per cell        (M3)
│   ├── pipeline.py              # wires preprocess -> detect -> persist    (M3)
│   ├── xml_parser.py            # reads info.xml                          (M4)
│   ├── visualization.py         # matplotlib chart for infovis.py          (M6)
│   └── signature_verify.py      # SSIM/ORB signature comparison            (M7)
│
├── templates/
│   ├── base.html, base_public.html          # shared layout                (M1)
│   ├── login.html, index.html               # login + dashboard            (M1)
│   ├── process.html                         # upload/process page          (M2)
│   ├── result.html                          # per-sheet result page        (M3)
│   ├── sessions.html                        # session list                 (M4)
│   ├── students.html                        # student list                 (M5)
│   ├── student.html                         # student detail + chart       (M6)
│   ├── investigate.html                     # signature verification page  (M7)
│   └── users.html                           # account management           (M8)
│
├── static/
│   ├── css/style.css
│   └── js/app.js                            # (M6)
│
└── data/                        # created at runtime, not in the by-member doc
    ├── sheets/                  # signing sheet images you process
    ├── output/                  # step images + charts per job
    ├── signatures/              # collected signature crops for investigate.py
    └── uploads/                 # images uploaded through the web /process page
```

---

## Setup

1. Start **MySQL** in XAMPP.
2. Import the schema:
   ```bash
   mysql -u root < sams_db.sql
   ```
   (or phpMyAdmin → Import → `sams_db.sql` → Go)
3. Pull every file out of `SAMS_Code_By_Member.md` into a project folder, at the path given in each `` `path` `` header.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a login:
   ```bash
   python manage_users.py add admin <password> admin "Your Name"
   ```
6. Run the web app:
   ```bash
   python app.py
   ```
   → http://127.0.0.1:5000

---

## Command-line tools

Matches the run commands given in the coursework brief:

```bash
python sams.py 05.07.2019.jpeg info.xml     # process one signing sheet
python infovis.py 10009303                  # attendance chart for one student
python investigate.py 10009303              # signature consistency check
```

**Name each image by its actual session date** (`05.07.2019.jpeg`, `12.07.2019.jpeg`, …) — `sams.py` reads the date from the filename first and only falls back to the date in `info.xml` if the filename doesn't have one. This is what keeps each of the five signing sheets as its own session in the database instead of all collapsing into one. For the report, the five supplied sheets rename as:

| Supplied sheet | Rename to | Hall |
|---|---|---|
| Sheet 1 | `05.07.2019.jpeg` | L104 |
| Sheet 2 | `12.07.2019.jpeg` | 103 |
| Sheet 3 | `28.06.2019.jpeg` | 106 |
| Sheet 4 | `31.05.2019.jpeg` | 106 |
| Sheet 5 | `21.06.2019.jpeg` | 106 |

---

