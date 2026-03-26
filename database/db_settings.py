#!/usr/bin/env python3
"""Settings database operations"""

from .db_core import get_db
from config import DEFAULT_FORWARD_DELAY, DEFAULT_SMALL_COOLDOWN, DEFAULT_LARGE_COOLDOWN, DEFAULT_BATCH_COOLDOWN, DEFAULT_DAILY_LIMIT, DEFAULT_BATCH_SIZE

# Global settings (will be loaded)
forward_delay = DEFAULT_FORWARD_DELAY
small_cooldown = DEFAULT_SMALL_COOLDOWN
large_cooldown = DEFAULT_LARGE_COOLDOWN
batch_cooldown = DEFAULT_BATCH_COOLDOWN
daily_limit = DEFAULT_DAILY_LIMIT
batch_size = DEFAULT_BATCH_SIZE
smart_mode = True

def load_settings():
    """Load all settings from database"""
    global forward_delay, small_cooldown, large_cooldown, batch_cooldown, daily_limit, batch_size, smart_mode
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT value FROM settings WHERE key=?", ("forward_delay",))
    row = c.fetchone()
    if row:
        forward_delay = int(row[0])
    
    c.execute("SELECT value FROM settings WHERE key=?", ("small_cooldown_min",))
    min_row = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key=?", ("small_cooldown_max",))
    max_row = c.fetchone()
    if min_row and max_row:
        small_cooldown = (int(min_row[0]), int(max_row[0]))
    
    c.execute("SELECT value FROM settings WHERE key=?", ("large_cooldown_min",))
    min_row = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key=?", ("large_cooldown_max",))
    max_row = c.fetchone()
    if min_row and max_row:
        large_cooldown = (int(min_row[0]), int(max_row[0]))
    
    c.execute("SELECT value FROM settings WHERE key=?", ("batch_cooldown_min",))
    min_row = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key=?", ("batch_cooldown_max",))
    max_row = c.fetchone()
    if min_row and max_row:
        batch_cooldown = (int(min_row[0]), int(max_row[0]))
    
    c.execute("SELECT value FROM settings WHERE key=?", ("daily_limit",))
    row = c.fetchone()
    if row:
        daily_limit = int(row[0])
    
    c.execute("SELECT value FROM settings WHERE key=?", ("batch_size",))
    row = c.fetchone()
    if row:
        batch_size = int(row[0])
    
    c.execute("SELECT value FROM settings WHERE key=?", ("smart_mode",))
    row = c.fetchone()
    if row:
        smart_mode = bool(int(row[0]))
    
    conn.close()

def save_setting(key, value):
    """Save individual setting"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE settings SET value=? WHERE key=?", (str(value), key))
    conn.commit()
    conn.close()
