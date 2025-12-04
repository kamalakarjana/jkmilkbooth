#!/usr/bin/env python3
import sqlite3
import boto3
import datetime
import os
import gzip
import shutil
from pathlib import Path

# Configuration
DB_PATH = '/home/ubuntu/milkbooth_server/milkbooth.db'
BACKUP_DIR = '/home/ubuntu/milkbooth_server/backups'
S3_BUCKET = 'milk-s3-bucket-name'  # REPLACE WITH YOUR BUCKET NAME
S3_FOLDER = 'database-backups'

# Ensure backup directory exists
Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

def create_backup():
    # Generate timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'milkbooth_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DB_PATH)
        
        # Create backup using SQLite's backup API
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()
        
        print(f"Database backup created: {backup_path}")
        
        # Compress the backup
        compressed_path = f"{backup_path}.gz"
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        print(f"Backup compressed: {compressed_path}")
        
        # Upload to S3
        upload_to_s3(compressed_path, backup_name)
        
        # Clean up local files (keep compressed version if desired)
        os.remove(backup_path)
        
        # Optional: Remove old local backups (keep last 7 days)
        cleanup_local_backups()
        
        return True
        
    except Exception as e:
        print(f"Backup failed: {str(e)}")
        return False

def upload_to_s3(file_path, backup_name):
    s3_client = boto3.client('s3')
    s3_key = f"{S3_FOLDER}/{backup_name}.gz"
    
    s3_client.upload_file(
        file_path,
        S3_BUCKET,
        s3_key,
        ExtraArgs={'StorageClass': 'STANDARD_IA'}  # Lower cost for backups
    )
    
    print(f"Backup uploaded to S3: s3://{S3_BUCKET}/{s3_key}")

def cleanup_local_backups(days_to_keep=7):
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    for file in os.listdir(BACKUP_DIR):
        file_path = os.path.join(BACKUP_DIR, file)
        if file.endswith('.gz'):
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if file_time < cutoff_date:
                os.remove(file_path)
                print(f"Removed old backup: {file}")

if __name__ == "__main__":
    create_backup()
