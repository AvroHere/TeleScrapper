#!/usr/bin/env python3
"""Configuration file - credentials and constants"""

import os
from pathlib import Path

# Credentials
API_ID = xxxxxxx
API_HASH = "xxxxxxxxx"
BOT_TOKEN = "xxxx:xxxxxxxx"
ADMIN_ID = xxxxxxx

# Paths
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "forwarder.db"
SESSION_FILE = str(BASE_DIR / "userbot.session")
TEMP_DIR = Path("/tmp/tg_media")
LOG_FILE = BASE_DIR / "bot.log"

# Create directories
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Default delay settings (safe for 6-month account)
DEFAULT_FORWARD_DELAY = 3
DEFAULT_SMALL_COOLDOWN = (15, 30)
DEFAULT_LARGE_COOLDOWN = (60, 90)
DEFAULT_BATCH_COOLDOWN = (15, 30)
DEFAULT_DAILY_LIMIT = 10000
DEFAULT_BATCH_SIZE = 200

# Conversation states
(
    WAIT_SOURCE_ID,
    WAIT_DEST_ID,
    WAIT_REORDER,
    WAIT_START_MSG_ID,
    WAIT_STATS_DATE,
    WAIT_RESTRICTED_LINK,
    WAIT_LOG_RANGE,
    WAIT_BATCH_SIZE,
    WAIT_FORWARD_DELAY,
    WAIT_SMALL_COOLDOWN,
    WAIT_LARGE_COOLDOWN,
    WAIT_BATCH_COOLDOWN,
    WAIT_DAILY_LIMIT,
) = range(13)
