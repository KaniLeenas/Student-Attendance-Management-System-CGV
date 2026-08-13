
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