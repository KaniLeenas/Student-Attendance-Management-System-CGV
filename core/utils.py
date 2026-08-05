"""Shared helpers: EXIF-safe loading, step recording, overlays, montages."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageOps


@dataclass
class Step:
    """One recorded stage of the image-processing pipeline."""
    key: str
    title: str
    description: str
    image: np.ndarray = field(repr=False, default=None)
    path: str = ""

    def as_dict(self):
        return {"key": self.key, "title": self.title,
                "description": self.description, "path": self.path}


class StepRecorder:
    """Collects every intermediate image so the report can screenshot them."""

    def __init__(self):
        self.steps: list[Step] = []

    def add(self, key, title, description, image):
        self.steps.append(Step(key, title, description, image.copy()))
        return image

    def save(self, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        for i, s in enumerate(self.steps, 1):
            fname = f"{i:02d}_{s.key}.png"
            cv2.imwrite(os.path.join(out_dir, fname), s.image)
            s.path = fname
        return [s.as_dict() for s in self.steps]


def imread_exif(path):
    """cv2.imread that honours the phone camera's EXIF rotation flag."""
    pil = ImageOps.exif_transpose(Image.open(path).convert("RGB"))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def resize_to_width(img, width):
    h, w = img.shape[:2]
    if w == width:
        return img, 1.0
    scale = width / float(w)
    return cv2.resize(img, (width, int(round(h * scale))),
                      interpolation=cv2.INTER_AREA), scale


def to_bgr(img):
    """Promote a single-channel mask to 3 channels for display."""
    return img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def filter_components(mask, min_area):
    """Drop connected components smaller than min_area."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = np.zeros_like(mask)
    kept, largest = 0, 0
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area >= min_area:
            out[labels == i] = 255
            kept += 1
            largest = max(largest, area)
    return out, kept, largest


def label_box(img, text, org, colour=(0, 200, 0)):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 4)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 1)
    return img


def montage(rows, row_height=70, pad=6, bg=(24, 24, 28), pane_width=300):
    """rows = [(label, [img, img, ...]), ...] -> one tall BGR montage."""
    tiles = []
    for label, imgs in rows:
        parts = []
        for im in imgs:
            im = to_bgr(im)
            h, w = im.shape[:2]
            scale = row_height / float(h)
            parts.append(cv2.resize(im, (max(1, int(w * scale)), row_height)))
        strip = parts[0]
        for p in parts[1:]:
            sep = np.full((row_height, pad, 3), 90, np.uint8)
            strip = np.hstack([strip, sep, p])
        pane = np.full((row_height, pane_width, 3), bg, np.uint8)
        label_box(pane, label, (8, row_height // 2 + 5), (120, 220, 255))
        tiles.append(np.hstack([pane, strip]))

    width = max(t.shape[1] for t in tiles)
    canvas = []
    for t in tiles:
        if t.shape[1] < width:
            t = np.hstack([t, np.full((t.shape[0], width - t.shape[1], 3),
                                      bg, np.uint8)])
        canvas.append(t)
        canvas.append(np.full((pad, width, 3), bg, np.uint8))
    return np.vstack(canvas)