
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