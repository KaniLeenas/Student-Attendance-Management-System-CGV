"""
General Utility Helpers (Module 2)
"""
import os
import cv2

def load_image(filepath: str):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    return cv2.imread(filepath)
