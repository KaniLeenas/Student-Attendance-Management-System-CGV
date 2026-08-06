"""Stage 1 - grayscale, denoise, deskew, illumination flattening, binarisation."""
from __future__ import annotations

import math

import cv2
import numpy as np

import config
from core.utils import StepRecorder, resize_to_width


class Preprocessor:
    """Turns a raw smart-phone photo into a clean, deskewed binary image."""

    def __init__(self, target_width=None, logger=None):
        p = config.PIPELINE
        self.target_width = target_width or p["target_width"]
        self.log = logger or (lambda *a, **k: None)

    # ------------------------------------------------------- primitives
    @staticmethod
    def grayscale(bgr):
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def denoise(gray):
        c = config.PIPELINE["bilateral"]
        # bilateral keeps thin pen strokes sharp while removing sensor noise
        return cv2.bilateralFilter(gray, c["d"], c["sigmaColor"], c["sigmaSpace"])

    @staticmethod
    def flatten_illumination(gray):
        """Remove the uneven lamp / shadow gradient by background division."""
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k)
        background = cv2.GaussianBlur(background, (0, 0), 9)
        return cv2.divide(gray, background, scale=255)

    @staticmethod
    def binarize(gray):
        c = config.PIPELINE["adaptive"]
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, c["blockSize"], c["C"])

    @staticmethod
    def clean(binary):
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        return cv2.morphologyEx(binary, cv2.MORPH_OPEN, k, iterations=1)

    # ---------------------------------------------------------- deskew
    @staticmethod
    def estimate_skew(binary):
        """Median inclination of the long horizontal rules of the table."""
        h, w = binary.shape
        kern = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 25), 1))
        rules = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kern)
        lines = cv2.HoughLinesP(rules, 1, np.pi / 720, threshold=100,
                                minLineLength=w // 5, maxLineGap=25)
        if lines is None:
            return 0.0
        limit = config.PIPELINE["deskew_max_angle"]
        angles = []
        for x1, y1, x2, y2 in lines[:, 0]:
            a = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(a) <= limit:
                angles.append(a)
        return float(np.median(angles)) if angles else 0.0

    @staticmethod
    def rotate(img, angle, border=(255, 255, 255)):
        if abs(angle) < 0.05:
            return img
        h, w = img.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        flags = cv2.INTER_NEAREST if img.ndim == 2 else cv2.INTER_CUBIC
        bval = 0 if img.ndim == 2 else border
        return cv2.warpAffine(img, m, (w, h), flags=flags,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=bval)

    # ------------------------------------------------------------- run
    def run(self, bgr):
        rec = StepRecorder()
        rec.add("original", "Original capture",
                "Raw smart-phone photograph of the signing sheet.", bgr)

        resized, scale = resize_to_width(bgr, self.target_width)
        rec.add("resized", f"Normalised size ({self.target_width} px)",
                "Every sheet is processed at one fixed working resolution so "
                "all kernel sizes and thresholds stay comparable.", resized)

        gray = self.grayscale(resized)
        rec.add("grayscale", "Grayscale conversion",
                "BGR to a single luminance channel; the colour of the pen is "
                "ignored at this stage.", gray)

        den = self.denoise(gray)
        rec.add("denoised", "Bilateral denoising",
                "Edge-preserving smoothing removes camera noise but keeps the "
                "thin pen strokes intact.", den)

        # skew is measured on a quick binary, then the colour image is rotated
        angle = self.estimate_skew(self.binarize(den))
        resized = self.rotate(resized, angle)
        gray = self.grayscale(resized)
        den = self.denoise(gray)
        rec.add("deskewed", f"Deskew ({angle:+.2f} deg)",
                "A Hough transform on the long table rules gives the tilt of "
                "the page; the image is rotated back to horizontal.", resized)

        flat = self.flatten_illumination(den)
        rec.add("illumination", "Illumination flattening",
                "Morphological closing estimates the paper background; dividing "
                "by it removes shadows and hot-spots.", flat)

        binary = self.binarize(flat)
        rec.add("binarized", "Adaptive binarisation",
                "Gaussian adaptive threshold (block 41, C 12): ink becomes "
                "white, paper becomes black.", binary)

        binary = self.clean(binary)
        rec.add("morphology", "Morphological opening",
                "A 2x2 opening deletes isolated speckles left by JPEG "
                "compression.", binary)

        self.log(f"  deskew angle .......... {angle:+.2f} deg")
        return {"color": resized, "gray": flat, "binary": binary,
                "angle": angle, "scale": scale, "recorder": rec}