#!/usr/bin/env python3
"""Menu and main handlers"""

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode

from config import ADMIN_ID
from utils.keyboards import main_menu_kb
from engine.forwarder import engine_running, get_status_light

def admin_only(fn):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else None
        if uid != ADMIN_ID:
            await update.effective_message.reply_text("⛔ Unauthorized.")
            return
        return await fn(update, ctx)
    wrapper.__name__ = fn.__name__
    return wrapper

@admin_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 <b>Elite Media Forwarder</b>\n\nChoose an action:",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(),
    )

@admin_only
async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await show_menu(update)

async def show_menu(update: Update, text="📋 <b>Main Menu</b>"):
    kb = main_menu_kb()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@admin_only
async def cb_back(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await show_menu(update)

@admin_only
async def cb_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    
    from database import db_sources, db_stats, db_settings
    from engine.forwarder import engine_running, get_status_light, _current_source_id
    
    groups = db_sources.get_all_sources()
    active = next((g for g in groups if g["status"] == "active"), None)
    pending = [g for g in groups if g["status"] == "pending"]
    completed = [g for g in groups if g["status"] == "completed"]
    failed = [g for g in groups if g["status"] == "failed"]
    
    today_total, today_videos, today_photos = db_stats.get_today_forwarded()
    daily_remaining = max(0, db_settings.daily_limit - today_total)
    
    lines = [
        f"📊 <b>STATUS DASHBOARD</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"{get_status_light()} <b>ENGINE STATUS:</b> {'Running' if engine_running() else 'Stopped'}",
    ]
    
    if active:
        name = active.get("group_name", active["group_id"])
        lines.extend([
            f"\n🎯 <b>ACTIVE SOURCE:</b>",
            f"📱 {name}",
            f"📍 <code>{active['group_id']}</code>",
            f"📊 Forwarded: {active['total_forwarded']} total | 🎬 {active['total_videos']} videos | 🖼️ {active['total_photos']} photos",
            f"\n📦 <b>CURRENT BATCH:</b>",
            f"📨 Messages {active['current_batch_start']} - {active['current_batch_end']}",
            f"📸 Media found: {active['current_batch_media']} ({active['current_batch_videos']} videos, {active['current_batch_photos']} photos)",
            f"✅ Forwarded: {active['current_batch_forwarded']} / {active['current_batch_media']} ({int(active['current_batch_forwarded']/active['current_batch_media']*100) if active['current_batch_media'] else 0}%)",
        ])
    else:
        lines.append("\n📭 No active source.")
    
    lines.extend([
        f"\n⏱️ <b>DELAY STATUS:</b>",
        f"📊 Forward delay: {db_settings.forward_delay} seconds",
        f"🛡️ Small cooldown: {db_settings.small_cooldown[0]}-{db_settings.small_cooldown[1]}s (after 10)",
        f"🛡️ Large cooldown: {db_settings.large_cooldown[0]}-{db_settings.large_cooldown[1]}s (after 100)",
        f"🛡️ Batch cooldown: {db_settings.batch_cooldown[0]}-{db_settings.batch_cooldown[1]}s",
    ])
    
    if db_settings.smart_mode:
        lines.append("🧠 Smart mode: ACTIVE")
    
    lines.extend([
        f"\n⏳ <b>QUEUE INFORMATION:</b>",
        f"Pending: {len(pending)} | Completed: {len(completed)} | Failed: {len(failed)}",
    ])
    
    next_source = None
    for g in groups:
        if g["status"] in ("pending", "failed"):
            next_source = g
            break
    if next_source:
        lines.append(f"📱 Next source: {next_source['group_name'] or next_source['group_id']}")
    
    lines.extend([
        f"\n📊 <b>DAILY LIMIT:</b>",
        f"Today: {today_total} / {db_settings.daily_limit} media ({int(today_total/db_settings.daily_limit*100) if db_settings.daily_limit else 0}%)",
        f"🎬 Videos: {today_videos} | 🖼️ Photos: {today_photos}",
        f"📅 Remaining: {daily_remaining} media",
        f"🕐 Resets at: 00:00 UTC",
    ])
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    from utils.keyboards import back_button
    await update.callback_query.edit_message_text(
        "\n".join(lines), parse_mode=ParseMode.HTML,
        reply_markup=back_button()
    )

def register_menu_handlers(app):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CallbackQueryHandler(cb_back, pattern="^back_menu$"))
    app.add_handler(CallbackQueryHandler(cb_status, pattern="^status$"))
