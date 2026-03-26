#!/usr/bin/env python3
"""Core database operations"""

import sqlite3
from config import DB_PATH

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    c = conn.cursor()
    
    c.executescript("""
        CREATE TABLE IF NOT EXISTS source_groups (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id         TEXT    NOT NULL UNIQUE,
            group_name       TEXT,
            position         INTEGER NOT NULL DEFAULT 0,
            status           TEXT    NOT NULL DEFAULT 'pending',
            start_msg_id     INTEGER NOT NULL DEFAULT 1,
            current_msg_id   INTEGER NOT NULL DEFAULT 0,
            total_forwarded  INTEGER NOT NULL DEFAULT 0,
            total_videos     INTEGER NOT NULL DEFAULT 0,
            total_photos     INTEGER NOT NULL DEFAULT 0,
            current_batch_start INTEGER NOT NULL DEFAULT 1,
            current_batch_end   INTEGER NOT NULL DEFAULT 0,
            current_batch_media INTEGER NOT NULL DEFAULT 0,
            current_batch_videos INTEGER NOT NULL DEFAULT 0,
            current_batch_photos INTEGER NOT NULL DEFAULT 0,
            current_batch_forwarded INTEGER NOT NULL DEFAULT 0,
            added_at         TEXT    NOT NULL,
            started_at       TEXT,
            completed_at     TEXT,
            cancelled_at     TEXT,
            fail_reason      TEXT
        );

        CREATE TABLE IF NOT EXISTS dest_groups (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id   TEXT NOT NULL UNIQUE,
            group_name TEXT,
            added_at   TEXT NOT NULL,
            active     INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS forward_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_group_id INTEGER NOT NULL,
            batch_start     INTEGER NOT NULL,
            batch_end       INTEGER NOT NULL,
            media_found     INTEGER NOT NULL,
            videos_found    INTEGER NOT NULL,
            photos_found    INTEGER NOT NULL,
            media_forwarded INTEGER NOT NULL,
            videos_forwarded INTEGER NOT NULL,
            photos_forwarded INTEGER NOT NULL,
            status          TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            FOREIGN KEY(source_group_id) REFERENCES source_groups(id)
        );

        CREATE TABLE IF NOT EXISTS flood_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            detail      TEXT,
            happened_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT NOT NULL,
            media_forwarded INTEGER NOT NULL DEFAULT 0,
            videos_forwarded INTEGER NOT NULL DEFAULT 0,
            photos_forwarded INTEGER NOT NULL DEFAULT 0,
            UNIQUE(date)
        );

        CREATE TABLE IF NOT EXISTS stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            hour            INTEGER NOT NULL,
            forwarded       INTEGER NOT NULL DEFAULT 0,
            videos          INTEGER NOT NULL DEFAULT 0,
            photos          INTEGER NOT NULL DEFAULT 0,
            source_group_id INTEGER,
            UNIQUE(date, hour, source_group_id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    
    # Insert default settings
    from config import DEFAULT_FORWARD_DELAY, DEFAULT_SMALL_COOLDOWN, DEFAULT_LARGE_COOLDOWN, DEFAULT_BATCH_COOLDOWN, DEFAULT_DAILY_LIMIT, DEFAULT_BATCH_SIZE
    
    defaults = [
        ("forward_delay", str(DEFAULT_FORWARD_DELAY)),
        ("small_cooldown_min", str(DEFAULT_SMALL_COOLDOWN[0])),
        ("small_cooldown_max", str(DEFAULT_SMALL_COOLDOWN[1])),
        ("large_cooldown_min", str(DEFAULT_LARGE_COOLDOWN[0])),
        ("large_cooldown_max", str(DEFAULT_LARGE_COOLDOWN[1])),
        ("batch_cooldown_min", str(DEFAULT_BATCH_COOLDOWN[0])),
        ("batch_cooldown_max", str(DEFAULT_BATCH_COOLDOWN[1])),
        ("daily_limit", str(DEFAULT_DAILY_LIMIT)),
        ("batch_size", str(DEFAULT_BATCH_SIZE)),
        ("smart_mode", "1"),
    ]
    
    for key, value in defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    
    conn.commit()
    conn.close()
