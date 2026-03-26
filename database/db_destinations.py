#!/usr/bin/env python3
"""Destination groups database operations"""

from datetime import datetime
from .db_core import get_db

def add_dest(group_id: str, name: str = "") -> bool:
    """Add destination group"""
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO dest_groups (group_id,group_name,added_at) VALUES (?,?,?)",
            (group_id, name, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_dest(group_id: str):
    """Remove destination"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM dest_groups WHERE group_id=?", (group_id,))
    conn.commit()
    conn.close()

def get_all_dests():
    """Get all active destinations"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM dest_groups WHERE active=1 ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
