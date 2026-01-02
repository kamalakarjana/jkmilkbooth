#!/usr/bin/env python3
"""
Database backup script
"""

import os
import sqlite3
import shutil
from datetime import datetime
from app import basedir

def backup_database():
    """Create a backup of the database"""
    db_path = os.path.join(basedir, 'milkbooth.db')
    backup_dir = os.path.join(basedir, 'backups')
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    # Create backups directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'milkbooth_backup_{timestamp}.db')
    
    try:
        # Copy database file
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backup created: {backup_path}")
        
        # Clean old backups (keep last 10)
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join(backup_dir, old_backup))
                print(f"  Removed old backup: {old_backup}")
                
    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")

if __name__ == '__main__':
    backup_database()