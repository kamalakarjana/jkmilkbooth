#!/bin/bash
cd /home/ubuntu/milkbooth_server
source venv/bin/activate
python3 backup_to_s3.py >> /home/ubuntu/milkbooth_server/logs/backup.log 2>&1
