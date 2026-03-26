#!/usr/bin/env python3
"""Core forwarding engine"""

import asyncio
import random
import logging
from datetime import datetime

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telegram.error import TelegramError

from database import db_sources, db_destinations, db_stats, db_settings
from database.db_stats import log_flood, get_today_forwarded
from database.db_settings import forward_delay, small_cooldown, large_cooldown, batch_cooldown, daily_limit, batch_size, smart_mode
from utils.notifications import notify

logger = logging.getLogger(__name__)

# Global engine state
_engine_running = False
_skip_current = False
_flood_count = 0
_consecutive_errors = 0
_current_source_id = None
_preserve_sender = True
_userbot = None

def set_userbot(ub):
    global _userbot
    _userbot = ub

def engine_running():
    return _engine_running

def engine_start():
    global _engine_running, _flood_count, _skip_current
    _engine_running = True
    _flood_count = 0
    _skip_current = False

def engine_stop():
    global _engine_running
    _engine_running = False

def engine_signal_skip():
    global _skip_current
    _skip_current = True

def get_status_light():
    if not _engine_running:
        return "🔴 STOPPED"
    if _current_source_id:
        return "🟢 RUNNING"
    return "🟡 IDLE"

async def resolve_entity(group_id: str):
    try:
        return await _userbot.get_entity(int(group_id))
    except ValueError:
        return await _userbot.get_entity(group_id)

async def last_msg_id(entity):
    try:
        msgs = await _userbot.get_messages(entity, limit=1)
        return msgs[0].id if msgs else 0
    except Exception:
        return 0

def detect_media_type(msg):
    from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
    
    if not msg.media:
        return None, False
    if isinstance(msg.media, MessageMediaPhoto):
        return "photo", False
    if isinstance(msg.media, MessageMediaDocument):
        for attr in msg.media.document.attributes:
            if type(attr).__name__ in ("DocumentAttributeVideo", "DocumentAttributeAnimated"):
                return "video", True
    return None, False

async def send_media_to_dest(dest_id: str, entity, msg_id: int, preserve_sender: bool = True):
    """Forward media using forward_messages if possible"""
    try:
        if preserve_sender:
            try:
                await _userbot.forward_messages(dest_id, msg_id, entity)
                return True
            except Exception as e:
                if "not enough rights" in str(e).lower() or "cant" in str(e).lower():
                    msg = await _userbot.get_messages(entity, ids=msg_id)
                    if msg and msg.media:
                        data = await _userbot.download_media(msg, bytes)
                        if data:
                            from telegram import Bot
                            if isinstance(msg.media, MessageMediaPhoto):
                                await _bot.send_photo(chat_id=dest_id, photo=data)
                            else:
                                is_video = any(
                                    type(a).__name__ == "DocumentAttributeVideo"
                                    for a in getattr(msg.media, "document", type("", (), {"attributes": []})()).attributes
                                )
                                if is_video:
                                    await _bot.send_video(chat_id=dest_id, video=data)
                                else:
                                    await _bot.send_document(chat_id=dest_id, document=data)
                            return True
                raise
        else:
            msg = await _userbot.get_messages(entity, ids=msg_id)
            if not msg or not msg.media:
                return False
            data = await _userbot.download_media(msg, bytes)
            if not data:
                return False
            from telegram import Bot
            if isinstance(msg.media, MessageMediaPhoto):
                await _bot.send_photo(chat_id=dest_id, photo=data)
            else:
                is_video = any(
                    type(a).__name__ == "DocumentAttributeVideo"
                    for a in getattr(msg.media, "document", type("", (), {"attributes": []})()).attributes
                )
                if is_video:
                    await _bot.send_video(chat_id=dest_id, video=data)
                else:
                    await _bot.send_document(chat_id=dest_id, document=data)
            return True
    except FloodWaitError as e:
        log_flood("flood_userbot", f"forward wait={e.seconds}s")
        raise
    except TelegramError as e:
        if "flood" in str(e).lower():
            log_flood("flood_bot", str(e))
            raise FloodWaitError(60) from e
        logger.warning(f"send_media TelegramError: {e}")
    except Exception as ex:
        logger.warning(f"send_media error: {ex}")
    return False

async def apply_cooldown(cooldown_type: str):
    """Apply cooldown with smart delay adjustment"""
    global forward_delay, _consecutive_errors
    
    if cooldown_type == "small":
        delay = random.randint(small_cooldown[0], small_cooldown[1])
        await notify(f"⏸️ Small cooldown: {delay}s (after 10 forwards)")
        await asyncio.sleep(delay)
    elif cooldown_type == "large":
        delay = random.randint(large_cooldown[0], large_cooldown[1])
        await notify(f"⏸️ Major cooldown: {delay}s (after 100 forwards)")
        await asyncio.sleep(delay)
    elif cooldown_type == "batch":
        delay = random.randint(batch_cooldown[0], batch_cooldown[1])
        await notify(f"⏸️ Batch cooldown: {delay}s")
        await asyncio.sleep(delay)
    
    if smart_mode and _consecutive_errors == 0:
        if forward_delay > 3:
            forward_delay = max(3, forward_delay - 1)
            db_settings.save_setting("forward_delay", forward_delay)

async def handle_flood(seconds: int, source: str):
    global _flood_count, _engine_running, forward_delay, _consecutive_errors
    _flood_count += 1
    _consecutive_errors += 1
    log_flood(f"flood_{source}", f"wait={seconds}s")
    
    if smart_mode:
        forward_delay = min(forward_delay + 2, 10)
        db_settings.save_setting("forward_delay", forward_delay)
        await notify(f"🧠 Smart delay increased to {forward_delay}s due to flood")

    await notify(
        f"⚠️ <b>Flood Control #{_flood_count}</b>\nFrom: <b>{source}</b> | Wait: <b>{seconds}s</b>\nDelay increased to {forward_delay}s",
        alert=(_flood_count >= 2),
    )

    if _flood_count >= 2:
        _engine_running = False
        await notify(
            "🚨🚨🚨 <b>EMERGENCY STOP</b> 🚨🚨🚨\n\n"
            "<b>2 flood control events triggered!</b>\n"
            "Bot <b>auto-stopped</b> to protect your account.\n\n"
            "✅ Use /start_bot or press ▶️ Start Bot to resume.",
            alert=True,
        )
        return

    await asyncio.sleep(min(seconds + 5, 300))
    _consecutive_errors = max(0, _consecutive_errors - 1)

async def process_batch(sg: dict, batch_start: int, batch_end: int):
    """Process a single batch: scan messages, forward media found"""
    global _consecutive_errors
    
    group_id = sg["group_id"]
    src_id = sg["id"]
    entity = await resolve_entity(group_id)
    
    await notify(f"🔍 Scanning batch {batch_start}-{batch_end}...")
    
    media_found = []
    videos_found = 0
    photos_found = 0
    
    try:
        msgs = await _userbot.get_messages(entity, min_id=batch_start - 1, max_id=batch_end + 1, limit=batch_size + 10)
    except FloodWaitError as e:
        await handle_flood(e.seconds, "userbot")
        return False, 0, 0, 0
    except Exception as ex:
        logger.warning(f"Scan batch error: {ex}")
        return False, 0, 0, 0
    
    for msg in msgs:
        mt, is_video = detect_media_type(msg)
        if mt:
            media_found.append({"msg_id": msg.id, "media_type": mt, "is_video": is_video})
            if mt == "video":
                videos_found += 1
            else:
                photos_found += 1
    
    total_found = len(media_found)
    db_sources.update_batch_progress(src_id, batch_start, batch_end, total_found, videos_found, photos_found)
    
    if total_found == 0:
        await notify(f"📭 Batch {batch_start}-{batch_end}: No media found")
        db_stats.log_batch(src_id, batch_start, batch_end, 0, 0, 0, 0, 0, 0, "completed")
        return True, 0, 0, 0
    
    await notify(f"📸 Batch {batch_start}-{batch_end}: Found {total_found} media ({videos_found} videos, {photos_found} photos)")
    
    dests = db_destinations.get_all_dests()
    if not dests:
        await notify("⚠️ No destination groups. Skipping batch.")
        return False, 0, 0, 0
    
    forwarded = 0
    videos_forwarded = 0
    photos_forwarded = 0
    batch_counter = 0
    
    for idx, item in enumerate(media_found, 1):
        if not _engine_running or _skip_current:
            return False, forwarded, videos_forwarded, photos_forwarded
        
        today_total, _, _ = get_today_forwarded()
        if today_total >= daily_limit:
            await notify(f"📊 Daily limit reached ({daily_limit}). Pausing until tomorrow.")
            db_stats.log_batch(src_id, batch_start, batch_end, total_found, videos_found, photos_found,
                        forwarded, videos_forwarded, photos_forwarded, "partial")
            return False, forwarded, videos_forwarded, photos_forwarded
        
        any_ok = False
        for dest in dests:
            try:
                ok = await send_media_to_dest(dest["group_id"], entity, item["msg_id"], _preserve_sender)
                if ok:
                    any_ok = True
            except FloodWaitError as e:
                await handle_flood(e.seconds, "forward")
                if not _engine_running:
                    return False, forwarded, videos_forwarded, photos_forwarded
                ok = await send_media_to_dest(dest["group_id"], entity, item["msg_id"], _preserve_sender)
                if ok:
                    any_ok = True
        
        if any_ok:
            forwarded += 1
            if item["media_type"] == "video":
                videos_forwarded += 1
            else:
                photos_forwarded += 1
            batch_counter += 1
            db_sources.update_batch_forwarded(src_id, 1, 1 if item["media_type"] == "video" else 0, 1 if item["media_type"] == "photo" else 0)
            db_stats.record_stat(src_id, 1, 1 if item["media_type"] == "video" else 0, 1 if item["media_type"] == "photo" else 0)
            _consecutive_errors = max(0, _consecutive_errors - 1)
        
        await asyncio.sleep(forward_delay)
        
        if batch_counter > 0 and batch_counter % 10 == 0:
            await apply_cooldown("small")
        
        if batch_counter > 0 and batch_counter % 100 == 0:
            await apply_cooldown("large")
    
    db_stats.log_batch(src_id, batch_start, batch_end, total_found, videos_found, photos_found,
                forwarded, videos_forwarded, photos_forwarded, "completed")
    
    return True, forwarded, videos_forwarded, photos_forwarded

async def run_engine():
    global _skip_current, _current_source_id, _preserve_sender
    
    while _engine_running:
        sg = db_sources.get_next_pending()
        if not sg:
            await asyncio.sleep(5)
            continue
        
        _skip_current = False
        group_id = sg["group_id"]
        src_id = sg["id"]
        _current_source_id = src_id
        
        try:
            entity = await resolve_entity(group_id)
            group_name = getattr(entity, "title", None) or str(entity.id)
            db_sources.update_source(group_id, group_name=group_name, status="active", started_at=datetime.utcnow().isoformat())
        except Exception as ex:
            db_sources.update_source(group_id, status="failed", fail_reason=str(ex))
            await notify(f"❌ Cannot access <code>{group_id}</code>:\n{ex}")
            _current_source_id = None
            continue
        
        total_msgs = await last_msg_id(entity)
        current_pos = sg.get("current_msg_id", sg.get("start_msg_id", 1))
        if current_pos == 0:
            current_pos = 1
        
        await notify(f"▶️ Started processing <b>{group_name}</b>\nFrom message: {current_pos}\nTotal messages: {total_msgs}")
        
        batch_num = 1
        while _engine_running and not _skip_current and current_pos <= total_msgs:
            batch_end = min(current_pos + batch_size - 1, total_msgs)
            
            success, forwarded, videos_fwd, photos_fwd = await process_batch(sg, current_pos, batch_end)
            
            if not success:
                if _skip_current:
                    db_sources.update_source(group_id, status="cancelled", cancelled_at=datetime.utcnow().isoformat())
                    await notify(f"⏭ Skipped <b>{group_name}</b>")
                else:
                    today_total, _, _ = get_today_forwarded()
                    if today_total >= daily_limit:
                        db_sources.update_source(group_id,
