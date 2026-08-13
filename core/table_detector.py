"""Stage 2 - locate the student table and cut it into cells."""
from __future__ import annotations

from dataclasses import dataclass

import cv2

import config
from core.utils import label_box


@dataclass
class TableGrid:
    x: int
    y: int
    w: int
    h: int
    xs: list          # absolute column separator positions
    ys: list          # absolute row separator positions
    fallback: bool = False

    @property
    def n_cols(self):
        return len(self.xs) - 1

    @property
    def n_rows(self):
        return len(self.ys) - 1

    def cell(self, row, col):
        """(x1, y1, x2, y2) of one cell."""
        return self.xs[col], self.ys[row], self.xs[col + 1], self.ys[row + 1]


class TableDetector:
    """Morphological line extraction plus projection profiling."""

    def __init__(self, expected_cols=5, logger=None):
        self.expected_cols = expected_cols
        self.log = logger or (lambda *a, **k: None)

    # ---------------------------------------------------------- helpers
    @staticmethod
    def _lines(binary):
        t = config.TABLE
        h, w = binary.shape
        hk = cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(15, w // t["h_kernel_div"]), 1))
        vk = cv2.getStructuringElement(
            cv2.MORPH_RECT, (1, max(15, h // t["v_kernel_div"])))
        horiz = cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk, iterations=1)
        vert = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk, iterations=1)
        horiz = cv2.dilate(horiz,
                           cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1)))
        vert = cv2.dilate(vert,
                          cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
        return horiz, vert

    @staticmethod
    def _peaks(profile, vote):
        """Group consecutive above-threshold indices, return their centres."""
        import numpy as np
        hits = np.where(profile >= vote)[0]
        if hits.size == 0:
            return []
        groups, start, prev = [], hits[0], hits[0]
        for v in hits[1:]:
            if v - prev > 4:
                groups.append(int((start + prev) // 2))
                start = v
            prev = v
        groups.append(int((start + prev) // 2))
        return groups

    # ------------------------------------------------------------- run
    def detect(self, binary, colour, n_students, recorder=None):
        t = config.TABLE
        H, W = binary.shape
        horiz, vert = self._lines(binary)
        grid = cv2.bitwise_or(horiz, vert)

        if recorder is not None:
            recorder.add("h_lines", "Horizontal rule extraction",
                         "Opening with a wide, one-pixel-tall kernel keeps only "
                         "the horizontal rules of the table.", horiz)
            recorder.add("v_lines", "Vertical rule extraction",
                         "Opening with a tall, one-pixel-wide kernel keeps only "
                         "the vertical rules.", vert)
            recorder.add("grid", "Reconstructed table skeleton",
                         "A bitwise OR of both rule masks rebuilds the grid.",
                         grid)

        # ---- pick the student table (the contour with the most rules)
        cnts, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
        best, best_rows = None, -1
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w < 0.30 * W or h < 0.030 * H:
                continue
            prof = (horiz[y:y + h, x:x + w] > 0).sum(axis=1)
            rows = len(self._peaks(prof, t["line_vote"] * w))
            if rows > best_rows:
                best, best_rows = (x, y, w, h), rows

        if best is None:                       # nothing found - use full page
            best = (0, 0, W, H)
        x, y, w, h = best

        # ---- projection profiling inside the table ROI
        hp = (horiz[y:y + h, x:x + w] > 0).sum(axis=1)
        vp = (vert[y:y + h, x:x + w] > 0).sum(axis=0)
        ys = [y + p for p in self._peaks(hp, t["line_vote"] * w)]
        xs = [x + p for p in self._peaks(vp, t["line_vote"] * h)]

        fallback = False
        # ---- fallback: the layout is STATIC, so the proportions are known
        if len(xs) != self.expected_cols + 1:
            xs = [int(round(x + r * w)) for r in t["column_ratios"]]
            fallback = True
        if len(ys) < n_students + 2:
            band = h / float(n_students + 1)
            ys = [int(round(y + i * band)) for i in range(n_students + 2)]
            fallback = True

        ys = sorted(ys)[: n_students + 2]      # header row + n student rows
        grid_obj = TableGrid(x, y, w, h, sorted(xs), ys, fallback)

        if recorder is not None:
            overlay = colour.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 165, 255), 3)
            for cx in grid_obj.xs:
                cv2.line(overlay, (cx, y), (cx, y + h), (255, 120, 0), 2)
            for cy in grid_obj.ys:
                cv2.line(overlay, (x, cy), (x + w, cy), (0, 220, 0), 2)
            label_box(overlay, "STUDENT TABLE", (x, max(20, y - 10)),
                      (0, 165, 255))
            recorder.add("table", "Table localisation",
                         f"Student table found at ({x},{y}) size {w}x{h}; "
                         f"{grid_obj.n_cols} columns by {grid_obj.n_rows} rows"
                         + (" [static-layout fallback]" if fallback else ""),
                         overlay)

            cells = colour.copy()
            for r in range(1, grid_obj.n_rows):
                x1, y1, x2, y2 = grid_obj.cell(r, grid_obj.n_cols - 1)
                cv2.rectangle(cells, (x1, y1), (x2, y2), (255, 0, 200), 2)
                label_box(cells, f"#{r}", (x1 + 5, y1 + 20), (255, 0, 200))
            recorder.add("cells", "Signature cell segmentation",
                         "The last column of every student row is isolated - "
                         "these are the regions of interest.", cells)

        self.log(f"  table ................. {w}x{h} @ ({x},{y})")
        self.log(f"  grid .................. {grid_obj.n_cols} cols x "
                 f"{grid_obj.n_rows} rows"
                 f"{'  (fallback)' if fallback else ''}")
        return grid_obj