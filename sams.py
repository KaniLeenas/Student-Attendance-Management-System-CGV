"""
Main CLI Interface for SAMS (Module 5)
"""
import argparse
from core.pipeline import process_attendance_sheet

def main():
    parser = argparse.ArgumentParser(description="Student Attendance Management System CLI")
    parser.add_argument("--image", type=str, help="Path to attendance sheet image")
    args = parser.parse_args()

if __name__ == '__main__':
    main()
