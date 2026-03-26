#!/usr/bin/env python3
"""Statistics database operations"""

from datetime import datetime
from .db_core import get_db

def record_stat(src_id: int, count: int = 1, videos: int = 0, photos: int = 0):
    """Record forwarding stat"""
    now = datetime.utcnow()
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO stats (date,hour,forwarded,videos,photos,source_group_id) VALUES (?,?,?,?,?,?)
           ON CONFLICT(date,hour,source_group_id) DO UPDATE SET
           forwarded=forwarded+?, videos=videos+?, photos=photos+?""",
        (now.strftime("%Y-%m-%d"), now.hour, count, videos, photos, src_id, count, videos, photos),
    )
    conn.commit()
    conn.close()
    increment_daily_stats(count, videos, photos)

def increment_daily_stats(media: int, videos: int, photos: int):
    """Increment daily counters"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO daily_stats (date, media_forwarded, videos_forwarded, photos_forwarded)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
           media_forwarded = media_forwarded + ?,
           videos_forwarded = videos_forwarded + ?,
           photos_forwarded = photos_forwarded + ?""",
        (today, media, videos, photos, media, videos, photos),
    )
    conn.commit()
    conn.close()

def get_today_forwarded():
    """Get today's totals"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT media_forwarded, videos_forwarded, photos_forwarded FROM daily_stats WHERE date=?", (today,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0], row[1], row[2]
    return 0, 0, 0

def get_stats(from_date: str, to_date: str):
    """Get stats for date range"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT s.date,s.hour,s.forwarded,s.videos,s.photos,sg.group_name,sg.group_id
           FROM stats s LEFT JOIN source_groups sg ON s.source_group_id=sg.id
           WHERE s.date BETWEEN ? AND ? ORDER BY s.date,s.hour""",
        (from_date, to_date),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats_total(from_date: str, to_date: str):
    """Get total stats for date range"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(forwarded),0), COALESCE(SUM(videos),0), COALESCE(SUM(photos),0) FROM stats WHERE date BETWEEN ? AND ?", (from_date, to_date))
    row = c.fetchone()
    conn.close()
    return row[0], row[1], row[2]

def log_batch(src_id: int, batch_start: int, batch_end: int, media_found: int, videos_found: int, photos_found: int,
              media_forwarded: int, videos_forwarded: int, photos_forwarded: int, status: str):
    """Log batch completion"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO forward_logs (source_group_id, batch_start, batch_end, media_found, videos_found, photos_found,
           media_forwarded, videos_forwarded, photos_forwarded, status, timestamp)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (src_id, batch_start, batch_end, media_found, videos_found, photos_found,
         media_forwarded, videos_forwarded, photos_forwarded, status, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def get_batch_logs(src_id: int, start_msg: int, end_msg: int):
    """Get logs for message range"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT * FROM forward_logs WHERE source_group_id=? AND batch_start >= ? AND batch_end <= ? ORDER BY batch_start""",
        (src_id, start_msg, end_msg),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_flood(event_type: str, detail: str = ""):
    """Log flood event"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO flood_events (event_type,detail,happened_at) VALUES (?,?,?)",
        (event_type, detail, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def get_recent_floods(limit=20):
    """Get recent flood events"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM flood_events ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
