#!/usr/bin/env python3
"""Source group database operations"""

from datetime import datetime
from .db_core import get_db

def add_source(group_id: str, group_name: str = "", start_msg_id: int = 1):
    """Add a source group to queue"""
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT COALESCE(MAX(position),0) FROM source_groups")
        pos = c.fetchone()[0] + 1
        c.execute(
            "INSERT INTO source_groups (group_id,group_name,position,start_msg_id,current_msg_id,added_at) VALUES (?,?,?,?,?,?)",
            (group_id, group_name, pos, start_msg_id, start_msg_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return get_source(group_id)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_source(group_id: str):
    """Get source by group_id"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM source_groups WHERE group_id=?", (group_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_source_by_id(src_id: int):
    """Get source by database ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM source_groups WHERE id=?", (src_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_sources():
    """Get all sources ordered by position"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM source_groups ORDER BY position")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_next_pending():
    """Get next pending source"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM source_groups WHERE status IN ('pending','failed') ORDER BY position LIMIT 1")
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_source(group_id: str, **kw):
    """Update source fields"""
    if not kw:
        return
    conn = get_db()
    c = conn.cursor()
    cols = ", ".join(f"{k}=?" for k in kw)
    c.execute(f"UPDATE source_groups SET {cols} WHERE group_id=?", [*kw.values(), group_id])
    conn.commit()
    conn.close()

def remove_source(group_id: str):
    """Remove source and its logs"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM source_groups WHERE group_id=?", (group_id,))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM forward_logs WHERE source_group_id=?", (row[0],))
    c.execute("DELETE FROM source_groups WHERE group_id=?", (group_id,))
    conn.commit()
    conn.close()

def reorder_sources(ids: list):
    """Reorder sources by position"""
    conn = get_db()
    c = conn.cursor()
    for pos, gid in enumerate(ids, 1):
        c.execute("UPDATE source_groups SET position=? WHERE group_id=?", (pos, gid))
    conn.commit()
    conn.close()

def set_start_msg(group_id: str, msg_id: int):
    """Set start message ID and reset"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE source_groups SET start_msg_id=?,current_msg_id=?,total_forwarded=0,total_videos=0,total_photos=0,status='pending' WHERE group_id=?",
        (msg_id, msg_id, group_id),
    )
    conn.commit()
    conn.close()

def update_batch_progress(src_id: int, batch_start: int, batch_end: int, media_found: int, videos: int, photos: int):
    """Update current batch info"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE source_groups SET current_batch_start=?,current_batch_end=?,current_batch_media=?,current_batch_videos=?,current_batch_photos=?,current_batch_forwarded=0 WHERE id=?",
        (batch_start, batch_end, media_found, videos, photos, src_id),
    )
    conn.commit()
    conn.close()

def update_batch_forwarded(src_id: int, forwarded: int, videos: int, photos: int):
    """Update forwarded counts"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE source_groups SET current_batch_forwarded=current_batch_forwarded+?, total_forwarded=total_forwarded+?, total_videos=total_videos+?, total_photos=total_photos+? WHERE id=?",
        (forwarded, forwarded, videos, photos, src_id),
    )
    conn.commit()
    conn.close()
