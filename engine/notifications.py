#!/usr/bin/env python3
"""Admin notifications"""

import logging
from config import ADMIN_ID

logger = logging.getLogger(__name__)
_bot = None

def set_bot(bot):
    global _bot
    _bot = bot

async def notify(text: str, alert: bool = False):
    """Send notification to admin"""
    try:
        await _bot.send_message(ADMIN_ID, text, parse_mode="HTML")
        if alert:
            await _bot.send_message(
                ADMIN_ID,
                "⚠️⚠️⚠️ <b>ATTENTION REQUIRED — SEE ABOVE</b> ⚠️⚠️⚠️",
                parse_mode="HTML",
            )
    except Exception as ex:
        logger.error(f"notify failed: {ex}")
