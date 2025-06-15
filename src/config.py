#!/usr/bin/env python3
"""
config.py - Configuration settings for Telegram Call Scheduler Bot

This file contains all configuration settings and constants.
Update the values here to customize the bot behavior.
"""

import os
import pytz
from datetime import datetime
from typing import Dict, Any

# =============================================
# BOT CONFIGURATION
# =============================================

# Telegram Bot Token - Get this from @BotFather
# IMPORTANT: Replace with your actual bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8158192206:AAGUHuYtDcy7DnsDNVLEKF2zrnQ-EhYemFY")

# Bot settings
BOT_NAME = "Call Scheduler Bot"
BOT_VERSION = "1.0.0"

# =============================================
# CALLMEBOT API CONFIGURATION
# =============================================

# CallMeBot API endpoint
CALLMEBOT_API_URL = "http://api.callmebot.com/start.php"

# Default call settings
DEFAULT_CALL_SETTINGS = {
    "language": "en-US-Standard-B",          # Default language for text-to-speech
    "repeat": 2,                # How many times to repeat the message
    "timeout": 30,              # Call timeout in seconds
    "send_text_copy": True      # Whether to send text message copy
}

# Available languages for CallMeBot TTS
# Use the "Voice Name" column from CallMeBot documentation
AVAILABLE_LANGUAGES = {
    "English": "en",
    "Spanish": "es", 
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko"
}

# =============================================
# STORAGE CONFIGURATION
# =============================================

# File paths for data storage
DATA_DIR = "data"
SCHEDULED_CALLS_FILE = os.path.join(DATA_DIR, "scheduled_calls.json")
USER_SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")
LOGS_DIR = "logs"
BOT_LOG_FILE = os.path.join(LOGS_DIR, "bot.log")

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# =============================================
# SCHEDULER CONFIGURATION
# =============================================

# How often to check for scheduled calls (in seconds)
SCHEDULER_CHECK_INTERVAL = 60

# Maximum number of scheduled calls per user
MAX_CALLS_PER_USER = 50

# Call execution settings
CALL_EXECUTION_TIMEOUT = 120  # Max time to wait for call completion
RETRY_FAILED_CALLS = True
MAX_CALL_RETRIES = 3

# =============================================
# MESSAGE TEMPLATES
# =============================================

# Welcome message template
WELCOME_MESSAGE = """
🤖 **Welcome to {bot_name}!**

I can help you schedule automatic voice calls through Telegram using CallMeBot API.

**Quick Setup:**
1. First, authorize CallMeBot: /setup
2. Schedule your first call: /schedule
3. Test it works: /test

**Commands:**
/schedule - Schedule a new call
/list - View scheduled calls
/delete - Delete a scheduled call
/test - Test call functionality
/setup - Setup instructions
/help - Show this help

Let's get started! 🚀
"""

# Help message template
HELP_MESSAGE = """
🔧 **Call Scheduler Bot Commands:**

📞 **Call Management:**
/schedule - Schedule a new automatic call
/list - View all your scheduled calls
/delete - Delete a scheduled call
/test - Test the calling functionality

⚙️ **Setup:**
/setup - Get setup instructions for CallMeBot

📋 **How it works:**
1. You schedule calls through this chat
2. I use CallMeBot API to make actual voice calls
3. Calls are made to your Telegram account at scheduled times

💡 **Tips:**
- Make sure to complete CallMeBot setup first
- Test with /test before scheduling important calls
- Use 24-hour format for times (e.g., 14:30)
- Messages are converted to speech during calls
"""

# Setup instructions template
SETUP_MESSAGE = """
🔧 **CallMeBot Setup Instructions:**

**Step 1: Authorize CallMeBot**
Choose one method:

📱 **Method A:** Visit this link:
https://www.callmebot.com/telegram-call-api/

💬 **Method B:** Send this message:
Send `/start` to @CallMeBot_txtbot

**Step 2: Get your details**
After authorization, note your:
- Telegram username (e.g., @yourusername)
- Or phone number with country code (e.g., +1234567890)

**Step 3: Test it works**
Use /test command here to verify everything is working.

⚠️ **Important Notes:**
- You need to authorize CallMeBot only once
- The service works with your Telegram account
- Calls will come through Telegram's voice calling feature
- There may be iOS audio playback issues (known CallMeBot bug)

Need help? Just type your question!
"""

# =============================================
# VALIDATION SETTINGS
# =============================================

# Message validation
MAX_MESSAGE_LENGTH = 256  # CallMeBot limit
MIN_MESSAGE_LENGTH = 5

# Time format validation
TIME_FORMAT = "%H:%M"  # 24-hour format
DATE_FORMAT = "%Y-%m-%d"

# User input validation
VALID_SCHEDULE_TYPES = ["once", "daily", "weekly"]
VALID_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# =============================================
# ERROR MESSAGES
# =============================================

ERROR_MESSAGES = {
    "bot_token_missing": "❌ Bot token not configured! Check config.py",
    "callmebot_unauthorized": "❌ CallMeBot not authorized. Use /setup first.",
    "invalid_time_format": "❌ Invalid time format. Use HH:MM (24-hour format)",
    "message_too_long": f"❌ Message too long! Max {MAX_MESSAGE_LENGTH} characters.",
    "message_too_short": f"❌ Message too short! Min {MIN_MESSAGE_LENGTH} characters.",
    "max_calls_reached": f"❌ Maximum {MAX_CALLS_PER_USER} scheduled calls reached.",
    "call_not_found": "❌ Scheduled call not found.",
    "api_error": "❌ API error occurred. Please try again later.",
    "invalid_schedule_type": f"❌ Invalid schedule type. Use: {', '.join(VALID_SCHEDULE_TYPES)}",
    "invalid_weekday": f"❌ Invalid weekday. Use: {', '.join(VALID_WEEKDAYS)}"
}

# =============================================
# SUCCESS MESSAGES
# =============================================

SUCCESS_MESSAGES = {
    "call_scheduled": "✅ Call scheduled successfully!",
    "call_deleted": "✅ Call deleted successfully!",
    "test_call_sent": "✅ Test call initiated! Check your phone.",
    "settings_updated": "✅ Settings updated successfully!"
}

# =============================================
# UTILITY FUNCTIONS
# =============================================

def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value with fallback to default"""
    return globals().get(key, default)

def is_valid_bot_token(token: str) -> bool:
    """Check if bot token format is valid"""
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        return False
    
    # Basic token format validation (should be like: 123456:ABC-DEF...)
    parts = token.split(":")
    if len(parts) != 2:
        return False
    
    try:
        int(parts[0])  # First part should be numeric
        return len(parts[1]) > 10  # Second part should be reasonably long
    except ValueError:
        return False

def validate_time_format(time_str: str) -> bool:
    """Validate time format (HH:MM)"""
    try:
        from datetime import datetime
        datetime.strptime(time_str, TIME_FORMAT)
        return True
    except ValueError:
        return False
    
def get_system_timezone():
    """Automatically detect system timezone"""
    try:
        import time
        import pytz
        
        # Get system timezone
        if hasattr(time, 'tzname'):
            # Windows/Unix method
            local_tz_name = time.tzname[time.daylight]
            if local_tz_name:
                return local_tz_name
        
        # Alternative method - try to get from system
        try:
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                # Windows timezone detection
                result = subprocess.run(['tzutil', '/g'], capture_output=True, text=True)
                if result.returncode == 0:
                    win_tz = result.stdout.strip()
                    # Convert Windows timezone to pytz timezone
                    tz_mapping = {
                        'Eastern Standard Time': 'US/Eastern',
                        'Central Standard Time': 'US/Central',
                        'Mountain Standard Time': 'US/Mountain',
                        'Pacific Standard Time': 'US/Pacific',
                        'Singapore Standard Time': 'Asia/Singapore',
                        # Add more mappings as needed
                    }
                    return tz_mapping.get(win_tz, 'UTC')
            else:
                # Unix/Linux timezone detection
                try:
                    with open('/etc/timezone', 'r') as f:
                        return f.read().strip()
                except FileNotFoundError:
                    pass
        except:
            pass
        
        # Fallback - detect from current time offset
        now = datetime.now()
        utc_now = datetime.utcnow()
        offset = now - utc_now
        offset_hours = offset.total_seconds() / 3600
        
        # Map common offsets to timezones
        offset_mapping = {
            8: 'Asia/Singapore',
            -5: 'US/Eastern',
            -6: 'US/Central', 
            -7: 'US/Mountain',
            -8: 'US/Pacific',
            0: 'UTC',
            1: 'Europe/London',
            9: 'Asia/Tokyo'
        }
        
        return offset_mapping.get(int(offset_hours), 'UTC')
        
    except Exception:
        return 'UTC'  # Safe fallback

# Auto-detect system timezone
SYSTEM_TIMEZONE = get_system_timezone()
DEFAULT_USER_TIMEZONE = SYSTEM_TIMEZONE

print(f"🌍 Detected timezone: {SYSTEM_TIMEZONE}")

def validate_message(message: str) -> tuple[bool, str]:
    """
    Validate call message
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(message) < MIN_MESSAGE_LENGTH:
        return False, ERROR_MESSAGES["message_too_short"]
    
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, ERROR_MESSAGES["message_too_long"]
    
    return True, ""

# =============================================
# DEVELOPMENT/DEBUG SETTINGS
# =============================================

# Debug mode - set to False in production
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

# Logging configuration
LOGGING_CONFIG = {
    "level": "DEBUG" if DEBUG_MODE else "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S"
}

# Test settings (for development)
TEST_USER_ID = os.getenv("TEST_USER_ID", None)
TEST_PHONE_NUMBER = os.getenv("TEST_PHONE_NUMBER", None)

# =============================================
# EXPORT CONFIGURATION
# =============================================

# Configuration summary for other modules
CONFIG_SUMMARY = {
    "bot_token": BOT_TOKEN,
    "bot_name": BOT_NAME,
    "version": BOT_VERSION,
    "callmebot_api": CALLMEBOT_API_URL,
    "data_dir": DATA_DIR,
    "debug_mode": DEBUG_MODE
}

# Validate critical configuration on import
if __name__ == "__main__":
    print("Configuration Validation:")
    print(f"Bot Token Valid: {is_valid_bot_token(BOT_TOKEN)}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Debug Mode: {DEBUG_MODE}")
    print(f"CallMeBot API: {CALLMEBOT_API_URL}")