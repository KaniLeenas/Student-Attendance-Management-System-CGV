"""
Database Connection & Operations (Module 1)
"""
import sqlite3
import config

def get_db_connection():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn
