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