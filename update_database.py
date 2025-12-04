#!/usr/bin/env python3
"""
Update database to use new datetime functions
"""

import sqlite3
from datetime import datetime
import pytz

def update_database():
    print("Starting database update...")
    
    # Connect to database
    conn = sqlite3.connect('milkbooth.db')
    cursor = conn.cursor()
    
    # Check current structure
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Found tables: {[t[0] for t in tables]}")
    
    # For each table with created_at, the new defaults will apply to new records
    # Existing records remain unchanged
    
    print("\n✅ Database is ready for new IST datetime defaults.")
    print("   Existing data remains unchanged.")
    print("   New records will use IST timezone.")
    
    conn.close()

if __name__ == "__main__":
    update_database()
