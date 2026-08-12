"""Data-visualization module (matplotlib) used by infovis.py."""
from __future__ import annotations

import os
import sys
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

PRESENT, ABSENT, ACCENT = "#22c55e", "#ef4444", "#38bdf8"

plt.rcParams.update({
    "figure.facecolor": "#0f172a", "axes.facecolor": "#111c33",
    "axes.edgecolor": "#334155", "axes.labelcolor": "#cbd5e1",
    "text.color": "#e2e8f0", "xtick.color": "#94a3b8",
    "ytick.color": "#94a3b8", "grid.color": "#1e293b",
    "font.size": 9,
})


def open_file(path):
    """Open a saved chart with the operating system's default viewer."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)                       # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:                                # noqa: BLE001
        pass


def student_dashboard(student, rows, out_path=None, show=False):
    """Three-panel attendance summary for one student."""
    labels = [r["session_date"].strftime("%d %b") for r in rows]
    values = [1 if r["status"] == "present" else 0 for r in rows]
    present, total = sum(values), len(values)
    pct = (present / total * 100) if total else 0.0

    cumulative, run = [], 0
    for i, v in enumerate(values, 1):
        run += v
        cumulative.append(run / i * 100)

    fig = plt.figure(figsize=(12, 6.5))
    gs = GridSpec(2, 3, figure=fig, hspace=.45, wspace=.35,
                  left=.07, right=.96, top=.86, bottom=.12)
    fig.suptitle(f"Attendance Summary  |  {student['title']} {student['name']}"
                 f"  ({student['student_no']})",
                 fontsize=14, fontweight="bold", y=.96)

    # (1) session timeline
    ax = fig.add_subplot(gs[0, :])
    ax.bar(labels, [1] * total,
           color=[PRESENT if v else ABSENT for v in values],
           edgecolor="#0f172a", width=.55)
    for i, v in enumerate(values):
        ax.text(i, .5, "P" if v else "A", ha="center", va="center",
                fontweight="bold", color="#0b1120")
    ax.set_ylim(0, 1.35)
    ax.set_yticks([])
    ax.set_title("Session-by-session attendance", loc="left",
                 fontweight="bold")
    ax.grid(axis="x", alpha=.15)

    # (2) donut
    ax = fig.add_subplot(gs[1, 0])
    ax.pie([present, total - present], colors=[PRESENT, ABSENT],
           startangle=90, wedgeprops=dict(width=.42, edgecolor="#0f172a"),
           labels=["Present", "Absent"], autopct="%1.0f%%", pctdistance=.78)
    ax.text(0, 0, f"{pct:.0f}%", ha="center", va="center",
            fontsize=17, fontweight="bold")
    ax.set_title("Overall ratio", loc="left", fontweight="bold")

    # (3) cumulative trend
    ax = fig.add_subplot(gs[1, 1:])
    ax.plot(labels, cumulative, marker="o", color=ACCENT, linewidth=2)
    ax.fill_between(range(total), cumulative, color=ACCENT, alpha=.12)
    ax.axhline(80, color="#f59e0b", linestyle="--", linewidth=1.2,
               label="80 % requirement")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Cumulative %")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=.2)
    ax.set_title("Cumulative attendance trend", loc="left", fontweight="bold")

    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=130)
    plt.close(fig)
    if show and out_path:
        open_file(out_path)
    return out_path


def class_overview(summary, out_path=None, show=False):
    names = [str(r["student_no"]) for r in summary]
    pcts = [float(r["present"]) / r["total"] * 100 if r["total"] else 0.0
            for r in summary]

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.barh(names, pcts, color=[PRESENT if p >= 80 else ABSENT for p in pcts])
    ax.axvline(80, color="#f59e0b", ls="--")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Attendance %")
    ax.set_title("Class attendance overview", fontweight="bold", loc="left")
    fig.tight_layout()

    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=130)
    plt.close(fig)
    if show and out_path:
        open_file(out_path)
    return out_path