
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