#!/usr/bin/env python3
"""
MilkBooth Timezone Utilities for IST (Indian Standard Time)
"""

from datetime import datetime
import pytz

# Timezone definitions
IST = pytz.timezone('Asia/Kolkata')

def get_today_ist():
    """Get today's date in DD-MM-YYYY format (IST)"""
    return datetime.now(IST).strftime('%d-%m-%Y')

def get_ist_datetime():
    """Get current datetime in IST"""
    return datetime.now(IST)

print(f"[Timezone Utils] Today's date (IST): {get_today_ist()}")
