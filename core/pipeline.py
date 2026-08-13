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