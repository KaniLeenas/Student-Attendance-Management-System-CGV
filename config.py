"""Central configuration for SAMS ."""
import os

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
SHEETS_DIR  = os.path.join(DATA_DIR, "sheets")
OUTPUT_DIR  = os.path.join(DATA_DIR, "output")
SIGN_DIR    = os.path.join(DATA_DIR, "signatures")
UPLOAD_DIR  = os.path.join(DATA_DIR, "uploads")
SQL_FILE    = os.path.join(BASE_DIR, "sams_db.sql")
DEFAULT_XML = os.path.join(BASE_DIR, "info.xml")

for _d in (DATA_DIR, SHEETS_DIR, OUTPUT_DIR, SIGN_DIR, UPLOAD_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------- database
DB = {
    "host":     os.getenv("SAMS_DB_HOST", "127.0.0.1"),
    "port":     int(os.getenv("SAMS_DB_PORT", 3306)),
    "user":     os.getenv("SAMS_DB_USER", "root"),
    "password": os.getenv("SAMS_DB_PASS", ""),       # XAMPP default = empty
    "database": os.getenv("SAMS_DB_NAME", "sams_db"),
}

# ------------------------------------------------------------------ web
SECRET_KEY = os.getenv("SAMS_SECRET", "cs402.3-sams-change-me")

# ------------------------------------------------------- image pre-process
PIPELINE = {
    "target_width": 1600,
    "bilateral":    {"d": 7, "sigmaColor": 60, "sigmaSpace": 60},
    "adaptive":     {"blockSize": 41, "C": 12},
    "deskew_max_angle": 15.0,
}

# ------------------------------------------------------- table / grid step
TABLE = {
    "h_kernel_div": 30,        # horizontal line kernel = width  / 30
    "v_kernel_div": 60,        # vertical   line kernel = height / 60
    "line_vote":    0.55,      # fraction of the ROI a peak must cover
    # static layout fallback (measured from the NSBM signing sheet)
    "column_ratios": [0.000, 0.127, 0.307, 0.408, 0.794, 1.000],
}

# ------------------------------------------------- signature ink detection
SIGNATURE = {
    "cell_margin_x": 0.05,     # trim grid lines before measuring ink
    "cell_margin_y": 0.14,
    "dark_threshold": 190,     # after illumination flattening (paper ~255)
    "sat_min": 55,             # colour pens -> high saturation
    "val_min": 25,
    "val_max": 235,
    "min_component_area": 40,  # removes dust / JPEG speckle
    "ink_ratio_threshold": 0.015,
    "strong_ratio": 0.050,     # ratio mapped to 100 % confidence
}

# --------------------------------------------------- signature comparison
# NOTE: real-world testing (5 signing sheets, 6 students) showed that even a
# genuine same-person signature scores only ~45-65% similarity across
# different photographs (natural handwriting variation + photo-to-photo
# crop/lighting differences dominate the raw pixel/shape comparison). A
# FIXED absolute threshold therefore false-flagged every student. Verdicts
# are now relative: a sample is flagged only if it is a statistical outlier
# against that same student's OTHER samples, not against a global number.
VERIFY = {
    "canvas": (240, 120),        # w, h of the normalised signature canvas
    "weights": {"shape": 0.35, "profile": 0.35, "overlap": 0.20, "orb": 0.10},
    "outlier_z": 1.0,            # flag if mean sim is > 1.0 std below the group
    "min_absolute_floor": 25.0,  # below this, always flag regardless of z-score
    "overlap_dilate_iter": 4,    # tolerance for natural stroke-position drift
}