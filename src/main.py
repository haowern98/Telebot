#!/usr/bin/env python3
"""
main.py - Interactive Telegram Call Scheduler Bot
Main entry point and bot setup

This is the main file you run to start the bot.
Chat with this bot to schedule automatic calls using CallMeBot API.

Usage: python main.py
"""

import asyncio
import logging
import os
from telegram.ext import Application

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from bot_handlers import CallSchedulerBot
from config import BOT_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to start the bot"""
    
    # Check if bot token is configured
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN not found!")
        print("Please set your bot token in config.py")
        print("Get a token from @BotFather on Telegram")
        return
    
    print("🤖 Starting Telegram Call Scheduler Bot...")
    print("=" * 50)
    print("Features:")
    print("- Schedule voice calls through chat")
    print("- One-time, daily, and weekly calls")
    print("- CallMeBot integration for actual calling")
    print("- Persistent call storage")
    print("=" * 50)
    
    try:
        # Create and start the bot
        bot = CallSchedulerBot(BOT_TOKEN)
        
        print("✅ Bot initialized successfully")
        print("📱 You can now chat with your bot on Telegram")
        print("🔧 Use /setup for CallMeBot configuration")
        print("\n🏃 Bot is running... Press Ctrl+C to stop")
        
        # Run the bot
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check your bot token in config.py")
        print("2. Ensure you have internet connection")
        print("3. Check the logs in bot.log for details")

if __name__ == "__main__":
    main()