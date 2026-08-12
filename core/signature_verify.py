"""Signature normalisation, feature extraction and matching (investigate.py)."""
from __future__ import annotations

import os
import glob
from dataclasses import dataclass

import cv2
import numpy as np

import config
from core.signature_detector import SignatureDetector
from core.utils import filter_components


@dataclass
class Sample:
    label: str
    path: str
    image: np.ndarray          # normalised binary canvas
    features: dict


class SignatureVerifier:
    def __init__(self):
        self.cfg = config.VERIFY
        self.det = SignatureDetector()
        self.orb = cv2.ORB_create(nfeatures=400, scaleFactor=1.2)

    # ------------------------------------------------------ normalisation
    def normalise(self, bgr):
        mask = self.det.ink_mask(bgr)
        mask, _, _ = filter_components(
            mask, config.SIGNATURE["min_component_area"])
        ys, xs = np.nonzero(mask)
        if ys.size == 0:
            return None
        mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

        cw, ch = self.cfg["canvas"]
        h, w = mask.shape
        scale = min((cw - 12) / w, (ch - 12) / h)
        resized = cv2.resize(mask,
                             (max(1, int(w * scale)), max(1, int(h * scale))),
                             interpolation=cv2.INTER_AREA)
        _, resized = cv2.threshold(resized, 40, 255, cv2.THRESH_BINARY)

        canvas = np.zeros((ch, cw), np.uint8)
        y0 = (ch - resized.shape[0]) // 2
        x0 = (cw - resized.shape[1]) // 2
        canvas[y0:y0 + resized.shape[0], x0:x0 + resized.shape[1]] = resized
        return canvas

    # -------------------------------------------------------- descriptors
    def features(self, canvas):
        m = cv2.moments(canvas)
        hu = cv2.HuMoments(m).flatten()
        hu = np.sign(hu) * np.log1p(np.abs(hu) * 1e10)

        vproj = canvas.sum(axis=0).astype(np.float32)
        hproj = canvas.sum(axis=1).astype(np.float32)
        vproj = cv2.resize(vproj.reshape(1, -1), (48, 1)).flatten()
        hproj = cv2.resize(hproj.reshape(1, -1), (24, 1)).flatten()
        profile = np.concatenate([vproj, hproj])
        norm = np.linalg.norm(profile)
        profile = profile / norm if norm else profile

        _, des = self.orb.detectAndCompute(canvas, None)
        return {"hu": hu, "profile": profile, "orb": des,
                "density": float(np.count_nonzero(canvas)) / canvas.size}

    # ---------------------------------------------------------- matching
    def similarity(self, a: Sample, b: Sample) -> float:
        w = self.cfg["weights"]

        shape = float(np.exp(-cv2.matchShapes(a.image, b.image,
                                              cv2.CONTOURS_MATCH_I2, 0)))
        prof = float(np.clip(np.dot(a.features["profile"],
                                    b.features["profile"]), 0, 1))

        k = np.ones((3, 3), np.uint8)
        iters = self.cfg["overlap_dilate_iter"]
        da = cv2.dilate(a.image, k, iterations=iters)
        db = cv2.dilate(b.image, k, iterations=iters)
        inter = np.count_nonzero(cv2.bitwise_and(da, db))
        union = np.count_nonzero(cv2.bitwise_or(da, db))
        overlap = inter / union if union else 0.0

        orb = 0.0
        da_, db_ = a.features["orb"], b.features["orb"]
        if da_ is not None and db_ is not None and len(da_) > 5 and len(db_) > 5:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING)
            pairs = bf.knnMatch(da_, db_, k=2)
            good = [p[0] for p in pairs
                    if len(p) == 2 and p[0].distance < .78 * p[1].distance]
            orb = min(1.0, len(good) / float(min(len(da_), len(db_))))

        score = (w["shape"] * shape + w["profile"] * prof +
                 w["overlap"] * overlap + w["orb"] * orb) * 100
        return float(np.clip(score, 0, 100))

    # ------------------------------------------------------------- API
    def load_samples(self, student_no):
        folder = os.path.join(config.SIGN_DIR, student_no)
        samples = []
        for path in sorted(glob.glob(os.path.join(folder, "*.png"))):
            bgr = cv2.imread(path)
            if bgr is None:
                continue
            canvas = self.normalise(bgr)
            if canvas is None:
                continue
            samples.append(Sample(
                os.path.splitext(os.path.basename(path))[0],
                path, canvas, self.features(canvas)))
        return samples

    def investigate(self, student_no):
        """Pairwise comparison with an OUTLIER-RELATIVE verdict.

        Real testing showed genuine same-person signatures only score
        ~45-65% on raw pixel/shape similarity across different photographs
        (natural handwriting variation + photo/crop differences). A fixed
        global threshold therefore flagged nearly everyone. Instead, each
        sample's mean similarity to that SAME student's other samples is
        compared against that student's own group average: a sample is
        flagged only if it sits meaningfully below its own peers, i.e. it
        is unusual relative to how consistent that person's signature
        normally is - not relative to an arbitrary global number.
        """
        samples = self.load_samples(student_no)
        n = len(samples)
        if n < 2:
            return {"student_no": student_no, "samples": samples,
                    "matrix": [], "report": [], "threshold": None,
                    "error": "At least two collected signatures are required. "
                             "Process more signing sheets first."}

        matrix = [[100.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                s = self.similarity(samples[i], samples[j])
                matrix[i][j] = matrix[j][i] = round(s, 1)

        means = []
        for i in range(n):
            others = [matrix[i][j] for j in range(n) if j != i]
            means.append(float(np.mean(others)))

        floor = self.cfg["min_absolute_floor"]
        z_cut = self.cfg["outlier_z"]

        if n >= 3:
            group_mean = float(np.mean(means))
            group_std = float(np.std(means)) or 1e-6   # avoid divide-by-zero
            cutoff = group_mean - z_cut * group_std
        else:
            # only 2 samples: no statistically meaningful outlier detection
            # possible: fall back to an absolute sanity floor only, to catch
            # a clearly corrupted crop rather than genuine forgery
            group_mean, group_std, cutoff = means[0], 0.0, floor

        report = []
        for i, smp in enumerate(samples):
            mean = means[i]
            others = [matrix[i][j] for j in range(n) if j != i]
            flagged = mean < floor or (n >= 3 and mean < cutoff)
            report.append({"label": smp.label, "path": smp.path,
                           "mean": round(mean, 1),
                           "best": round(max(others), 1),
                           "worst": round(min(others), 1),
                           "match": not flagged})
        return {"student_no": student_no, "samples": samples,
                "matrix": matrix, "report": report,
                "threshold": round(cutoff, 1),
                "group_mean": round(group_mean, 1),
                "error": None}