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