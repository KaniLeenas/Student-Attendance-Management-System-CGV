"""
Configuration settings for SAMS (Module 1)
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
SIGNATURES_DIR = os.path.join(DATA_DIR, 'signatures')
SHEETS_DIR = os.path.join(DATA_DIR, 'sheets')

SECRET_KEY = os.environ.get('SECRET_KEY', 'sams-secret-key-default')
DATABASE_PATH = os.path.join(BASE_DIR, 'sams.db')
