#!/usr/bin/env python3
"""
bot_handlers.py - Telegram Bot Command Handlers

This file contains the main bot class and all command handlers.
Handles user interactions, conversations, and command processing.
"""

import asyncio
import pytz
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

from config import *
from storage import StorageManager
from call_scheduler import CallScheduler
from callmebot_api import CallMeBotAPI

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
(WAITING_FOR_TIME, WAITING_FOR_MESSAGE, WAITING_FOR_SCHEDULE_TYPE, 
 WAITING_FOR_WEEKDAY, WAITING_FOR_USERNAME, WAITING_FOR_DELETE_CHOICE) = range(6)

class CallSchedulerBot:
    """Main bot class that handles all Telegram interactions"""
    
    def __init__(self, bot_token: str):
        """Initialize the call scheduler bot"""
        self.bot_token = bot_token
        self.application = Application.builder().token(bot_token).build()
        
        # TODO: Initialize components as we create them
        self.storage = StorageManager()
        self.scheduler = CallScheduler(self.storage)
        self.callmebot = CallMeBotAPI()
        
        # For now, create placeholder objects
        #self.storage = None
        #self.scheduler = None
        #self.callmebot = None
        
        # Track user conversation states
        self.user_states: Dict[int, Dict[str, Any]] = {}
        
        # Setup handlers
        self.setup_handlers()
        
        logger.info("CallSchedulerBot initialized successfully")
    
    def setup_handlers(self):
        """Setup all bot command and message handlers"""
        
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("setup", self.setup_command))
        
        # Call management commands
        self.application.add_handler(CommandHandler("schedule", self.schedule_command))
        self.application.add_handler(CommandHandler("list", self.list_calls_command))
        self.application.add_handler(CommandHandler("delete", self.delete_call_command))
        self.application.add_handler(CommandHandler("test", self.test_call_command))
        
        # Settings commands
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("timezone", self.timezone_command))  # ADD THIS LINE
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for conversation flows
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        
        self.application.add_handler(CommandHandler("fixlang", self.fix_language_command))
        
        logger.info("Bot handlers setup complete")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "there"
        
        # Initialize user in storage if new
        self.storage.initialize_user(user_id)
        
        welcome_text = WELCOME_MESSAGE.format(bot_name=BOT_NAME)
        
        # Create welcome keyboard
        keyboard = [
            [InlineKeyboardButton("📞 Schedule Call", callback_data="schedule_start")],
            [InlineKeyboardButton("🔧 Setup CallMeBot", callback_data="setup_start")],
            [InlineKeyboardButton("📋 View Calls", callback_data="list_calls")],
            [InlineKeyboardButton("🧪 Test Call", callback_data="test_call")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"User {user_id} ({user_name}) started the bot")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')
    
    async def setup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setup command"""
        keyboard = [
            [InlineKeyboardButton("✅ I've completed setup", callback_data="setup_complete")],
            [InlineKeyboardButton("❓ I need help", callback_data="setup_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            SETUP_MESSAGE,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule command"""
        user_id = update.effective_user.id
        
        # Check if user has reached max calls
        user_calls = self.storage.get_user_calls(user_id)
        if len(user_calls) >= MAX_CALLS_PER_USER:
            await update.message.reply_text(ERROR_MESSAGES["max_calls_reached"])
            return
        
        keyboard = [
            [InlineKeyboardButton("📞 One-time call", callback_data="schedule_once")],
            [InlineKeyboardButton("🔄 Daily calls", callback_data="schedule_daily")],
            [InlineKeyboardButton("📅 Weekly calls", callback_data="schedule_weekly")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📞 **What type of call would you like to schedule?**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def list_calls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command"""
        user_id = update.effective_user.id
        user_calls = self.storage.get_user_calls(user_id)
        
        if not user_calls:
            await update.message.reply_text("📭 You have no scheduled calls.")
            return
        
        calls_text = "📋 **Your Scheduled Calls:**\n\n"
        
        for call_id, call_info in user_calls.items():
            status_emoji = "✅" if call_info.get('active', True) else "⏸"
            calls_text += f"{status_emoji} **{call_id}**\n"
            calls_text += f"   ⏰ Time: {call_info['time']}\n"
            calls_text += f"   📝 Message: {call_info['message'][:50]}{'...' if len(call_info['message']) > 50 else ''}\n"
            calls_text += f"   🔄 Type: {call_info['type'].title()}\n"
            if call_info['type'] == 'weekly':
                calls_text += f"   📅 Day: {call_info.get('weekday', 'Unknown').title()}\n"
            calls_text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("🗑 Delete a call", callback_data="delete_call_menu")],
            [InlineKeyboardButton("⏸ Pause/Resume calls", callback_data="toggle_calls_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            calls_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def delete_call_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /delete command"""
        await self.show_delete_menu(update, context)
    
    async def test_call_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /test command"""
        user_id = update.effective_user.id
        user_settings = self.storage.get_user_settings(user_id)
        
        # Check if user has configured their username/phone
        if not user_settings.get('username') and not user_settings.get('phone'):
            await update.message.reply_text(
                "❌ Please configure your username or phone number first.\n"
                "Use /settings to set up your contact details."
            )
            return
        
        # Set user state for test call
        self.user_states[user_id] = {
            'action': 'test_call',
            'step': 'waiting_for_message'
        }
        
        await update.message.reply_text(
            "🧪 **Test Call Setup**\n\n"
            "What message would you like me to say during the test call?\n"
            "(This will be converted to speech)",
            parse_mode='Markdown'
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        user_id = update.effective_user.id
        user_settings = self.storage.get_user_settings(user_id)
        
        settings_text = "⚙️ **Your Settings:**\n\n"
        settings_text += f"👤 Username: {user_settings.get('username', 'Not set')}\n"
        settings_text += f"📱 Phone: {user_settings.get('phone', 'Not set')}\n"
        settings_text += f"🗣 Language: {user_settings.get('language', DEFAULT_CALL_SETTINGS['language'])}\n"
        settings_text += f"🔁 Repeat: {user_settings.get('repeat', DEFAULT_CALL_SETTINGS['repeat'])} times\n"
        settings_text += f"⏱ Timeout: {user_settings.get('timeout', DEFAULT_CALL_SETTINGS['timeout'])} seconds\n"
        
        keyboard = [
            [InlineKeyboardButton("👤 Set Username", callback_data="settings_username")],
            [InlineKeyboardButton("📱 Set Phone", callback_data="settings_phone")],
            [InlineKeyboardButton("🗣 Set Language", callback_data="settings_language")],
            [InlineKeyboardButton("🔁 Set Repeat", callback_data="settings_repeat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        logger.info(f"Button callback from user {user_id}: {data}")
        
        # Route button callbacks to appropriate handlers
        if data.startswith("schedule_"):
            await self.handle_schedule_callback(query, context)
        elif data.startswith("setup_"):
            await self.handle_setup_callback(query, context)
        elif data.startswith("delete_"):
            await self.handle_delete_callback(query, context)
        elif data.startswith("settings_"):
            await self.handle_settings_callback(query, context)
        elif data == "list_calls":
            await self.list_calls_from_callback(query, context)
        elif data.startswith("tz_"):  
            await self.handle_timezone_callback(query, context) 
        elif data == "test_call":
            await self.test_call_from_callback(query, context)
        else:
            await query.edit_message_text("❌ Unknown action. Please try again.")
    
    async def handle_timezone_callback(self, query, context):
        """Handle timezone-related button callbacks"""
        user_id = query.from_user.id
        data = query.data
        
        if data == "tz_auto":
            # Use auto-detected timezone
            self.storage.update_user_settings(user_id, {'timezone': SYSTEM_TIMEZONE})
            await query.edit_message_text(
                f"✅ **Timezone Updated**\n\n"
                f"Your timezone is now set to: **{SYSTEM_TIMEZONE}**\n"
                f"All scheduled calls will use this timezone."
            )
        elif data == "tz_manual":
            # Set user state for manual timezone input
            self.user_states[user_id] = {
                'action': 'settings',
                'field': 'timezone',
                'step': 'waiting_for_input'
            }
            await query.edit_message_text(
                "🌍 **Manual Timezone Setup**\n\n"
                "Enter your timezone (e.g., Asia/Singapore, US/Eastern, Europe/London):\n\n"
                "You can find timezone names at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
            )
    
    async def handle_schedule_callback(self, query, context):
        """Handle schedule-related button callbacks"""
        user_id = query.from_user.id
        data = query.data
        
        if data == "schedule_once":
            schedule_type = "once"
        elif data == "schedule_daily":
            schedule_type = "daily"
        elif data == "schedule_weekly":
            schedule_type = "weekly"
        else:
            await query.edit_message_text("❌ Invalid schedule type.")
            return
        
        # Set user state
        self.user_states[user_id] = {
            'action': 'schedule',
            'type': schedule_type,
            'step': 'waiting_for_time'
        }
        
        if schedule_type == "weekly":
            # First ask for weekday
            self.user_states[user_id]['step'] = 'waiting_for_weekday'
            
            keyboard = []
            for day in VALID_WEEKDAYS:
                keyboard.append([InlineKeyboardButton(day.title(), callback_data=f"weekday_{day}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📅 **Which day of the week?**",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        elif schedule_type == "once":
            # For one-time calls, ask for date first
            self.user_states[user_id]['step'] = 'waiting_for_date'
            await query.edit_message_text(
                "📅 **One-time Call Setup**\n\n"
                "What date should I call you?\n"
                "Please use YYYY-MM-DD format\n\n"
                "Examples: 2025-06-16, 2025-12-25",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"⏰ **{schedule_type.title()} Call Setup**\n\n"
                "What time should I call you?\n"
                "Please use 24-hour format (HH:MM)\n\n"
                "Examples: 09:30, 14:15, 20:00",
                parse_mode='Markdown'
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages during conversation flows"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Check if user is in a conversation state
        if user_id not in self.user_states:
            await update.message.reply_text(
                "❓ I'm not sure what you want to do. Try using /help or /start to see available commands."
            )
            return
        
        user_state = self.user_states[user_id]
        action = user_state.get('action')
        step = user_state.get('step')
        
        if action == 'schedule':
            await self.handle_schedule_message(update, context, message_text, user_state)
        elif action == 'test_call':
            await self.handle_test_call_message(update, context, message_text)
        elif action == 'settings':
            await self.handle_settings_message(update, context, message_text, user_state)
        else:
            await update.message.reply_text("❓ I'm not sure what you want to do. Try /help")
    
    async def handle_schedule_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    message_text: str, user_state: Dict[str, Any]):
        """Handle messages during schedule conversation"""
        user_id = update.effective_user.id
        step = user_state.get('step')
        
        if step == 'waiting_for_date':
            # Validate date format for one-time calls
            try:
                from datetime import datetime
                date_obj = datetime.strptime(message_text, "%Y-%m-%d").date()
                if date_obj <= datetime.now().date():
                    await update.message.reply_text("❌ Date must be in the future!")
                    return
            except ValueError:
                await update.message.reply_text("❌ Invalid date format. Use YYYY-MM-DD (e.g., 2025-06-17)")
                return
            
            user_state['date'] = message_text
            user_state['step'] = 'waiting_for_time'
            
            await update.message.reply_text(
                "⏰ **What time should I call you?**\n\n"
                "Please use 24-hour format (HH:MM)\n\n"
                "Examples: 09:30, 14:15, 20:00",
                parse_mode='Markdown'
            )
            
        elif step == 'waiting_for_time':
            # Validate time format
            if not validate_time_format(message_text):
                await update.message.reply_text(ERROR_MESSAGES["invalid_time_format"])
                return
            
            user_state['time'] = message_text
            user_state['step'] = 'waiting_for_message'
            
            await update.message.reply_text(
                "📝 **What should I say during the call?**\n\n"
                f"Maximum {MAX_MESSAGE_LENGTH} characters.\n"
                "This message will be converted to speech.",
                parse_mode='Markdown'
            )
        
        elif step == 'waiting_for_message':
            # Validate message
            is_valid, error_msg = validate_message(message_text)
            if not is_valid:
                await update.message.reply_text(error_msg)
                return
            
            user_state['message'] = message_text
            
            # Create the scheduled call
            call_id = await self.create_scheduled_call(user_id, user_state)
            
            if call_id:
                # Clear user state
                del self.user_states[user_id]
                
                schedule_info = f"{user_state['type'].title()} call"
                if user_state['type'] == 'weekly':
                    schedule_info += f" on {user_state.get('weekday', '').title()}s"
                elif user_state['type'] == 'once':
                    schedule_info += f" on {user_state.get('date', 'Unknown date')}"
                
                # Build details message
                details_text = f"✅ Call Scheduled Successfully!\n\n"
                details_text += f"📋 Details:\n"
                details_text += f"🆔 ID: {call_id}\n"
                details_text += f"⏰ Time: {user_state['time']}\n"
                details_text += f"🔄 Type: {schedule_info}\n"
                if user_state['type'] == 'once':
                    details_text += f"📅 Date: {user_state.get('date', 'Unknown')}\n"
                details_text += f"📝 Message: {message_text[:50]}{'...' if len(message_text) > 50 else ''}\n\n"
                details_text += f"Use /list to view all your calls or /test to test the system."
                
                await update.message.reply_text(details_text)
            else:
                await update.message.reply_text("❌ Failed to schedule call. Please try again.")
    
    async def handle_test_call_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle test call message"""
        user_id = update.effective_user.id
        
        # Validate message
        is_valid, error_msg = validate_message(message_text)
        if not is_valid:
            await update.message.reply_text(error_msg)
            return
        
        # Clear user state
        del self.user_states[user_id]
        
        # Make test call
        success = await self.make_test_call(user_id, message_text)
        
        if success:
            await update.message.reply_text(SUCCESS_MESSAGES["test_call_sent"])
        else:
            await update.message.reply_text(
                "❌ Test call failed. Please check:\n"
                "1. CallMeBot authorization\n"
                "2. Your username/phone settings\n"
                "3. Internet connection\n\n"
                "Use /setup for help."
            )
    
    async def create_scheduled_call(self, user_id: int, call_data: Dict[str, Any]) -> Optional[str]:
        """Create a new scheduled call"""
        try:
            call_id = self.storage.add_scheduled_call(user_id, call_data)
            
            # Add to scheduler
            self.scheduler.add_call(user_id, call_id, call_data)
            
            logger.info(f"Created scheduled call {call_id} for user {user_id}")
            return call_id
            
        except Exception as e:
            logger.error(f"Failed to create scheduled call: {e}")
            return None
    
    async def make_test_call(self, user_id: int, message: str) -> bool:
        """Make a test call"""
        try:
            user_settings = self.storage.get_user_settings(user_id)
            
            # Determine target (username or phone)
            target = user_settings.get('username') or user_settings.get('phone')
            if not target:
                return False
            
            # Make call using CallMeBot API
            success = await self.callmebot.make_call(target, message, user_settings)
            
            logger.info(f"Test call for user {user_id}: {'success' if success else 'failed'}")
            return success
            
        except Exception as e:
            logger.error(f"Test call failed: {e}")
            return False
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        
    async def handle_setup_callback(self, query, context):
        """Handle setup-related button callbacks"""
        data = query.data
        
        if data == "setup_complete":
            await query.edit_message_text(
                "✅ Great! CallMeBot setup completed.\n\n"
                "Now use /settings to configure your username/phone,\n"
                "then try /test to verify everything works!"
            )
        elif data == "setup_help":
            await query.edit_message_text(
                "❓ **Need Help with Setup?**\n\n"
                "1. Make sure you've authorized CallMeBot\n"
                "2. Set your username in /settings\n"
                "3. Test with /test command\n\n"
                "Still having issues? Check your internet connection."
            )

    async def handle_settings_callback(self, query, context):
        """Handle settings-related button callbacks"""
        user_id = query.from_user.id
        data = query.data
        
        if data == "settings_username":
            self.user_states[user_id] = {
                'action': 'settings',
                'field': 'username',
                'step': 'waiting_for_input'
            }
            await query.edit_message_text(
                "👤 **Set Username**\n\n"
                "Enter your Telegram username (with @):\n"
                "Example: @haowernn"
            )
        elif data == "settings_phone":
            self.user_states[user_id] = {
                'action': 'settings',
                'field': 'phone',
                'step': 'waiting_for_input'
            }
            await query.edit_message_text(
                "📱 **Set Phone Number**\n\n"
                "Enter your phone number with country code:\n"
                "Example: +1234567890"
            )
        else:
            await query.edit_message_text("⚙️ Settings option not implemented yet.")

    async def handle_delete_callback(self, query, context):
        """Handle delete-related button callbacks"""
        await query.edit_message_text("🗑 Delete functionality not implemented yet.")

    async def list_calls_from_callback(self, query, context):
        """Handle list calls from callback"""
        # Simulate the list command
        user_id = query.from_user.id
        user_calls = self.storage.get_user_calls(user_id)
        
        if not user_calls:
            await query.edit_message_text("📭 You have no scheduled calls.")
        else:
            calls_text = "📋 **Your Scheduled Calls:**\n\n"
            for call_id, call_info in user_calls.items():
                calls_text += f"• {call_id}: {call_info['time']} - {call_info['message'][:30]}...\n"
            await query.edit_message_text(calls_text, parse_mode='Markdown')

    async def test_call_from_callback(self, query, context):
        """Handle test call from callback"""
        user_id = query.from_user.id
        user_settings = self.storage.get_user_settings(user_id)
        
        if not user_settings.get('username') and not user_settings.get('phone'):
            await query.edit_message_text(
                "❌ Please set your username or phone in /settings first."
            )
            return
        
        self.user_states[user_id] = {
            'action': 'test_call',
            'step': 'waiting_for_message'
        }
        
        await query.edit_message_text(
            "🧪 **Test Call Setup**\n\n"
            "What message should I say during the test call?"
        )

    async def fix_language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Temporary command to fix language setting"""
        user_id = update.effective_user.id
        self.storage.update_user_settings(user_id, {'language': 'en-US-Standard-B'})
        await update.message.reply_text("✅ Language updated to en-US-Standard-B")

    async def handle_settings_message(self, update, context, message_text, user_state):
        """Handle settings input messages"""
        user_id = update.effective_user.id
        field = user_state.get('field')
        
        if field == 'username':
            # Allow clearing username
            if message_text.lower() in ['none', 'delete', 'clear', '@none', '@clear', '@delete']:
                self.storage.update_user_settings(user_id, {'username': None})
                await update.message.reply_text("✅ Username cleared!")
            elif not message_text.startswith('@'):
                await update.message.reply_text("❌ Username must start with @ (e.g., @haowernn)")
                return
            else:
                self.storage.update_user_settings(user_id, {'username': message_text})
                await update.message.reply_text(f"✅ Username set to {message_text}")
                
        elif field == 'phone':
            # Allow clearing phone number
            if message_text.lower() in ['none', 'delete', 'clear']:
                self.storage.update_user_settings(user_id, {'phone': None})
                await update.message.reply_text("✅ Phone number cleared!")
            elif not message_text.startswith('+'):
                await update.message.reply_text("❌ Phone must start with + (e.g., +6512345678)")
                return
            else:
                self.storage.update_user_settings(user_id, {'phone': message_text})
                await update.message.reply_text(f"✅ Phone set to {message_text}")
        
        elif field == 'timezone':
            # Validate and set timezone
            try:
                import pytz
                # Test if timezone is valid
                pytz.timezone(message_text)
                
                # Update user settings
                self.storage.update_user_settings(user_id, {'timezone': message_text})
                
                # Get current time in new timezone for confirmation
                try:
                    tz = pytz.timezone(message_text)
                    current_time = datetime.now(tz)
                    time_str = current_time.strftime("%H:%M:%S %Z")
                    
                    await update.message.reply_text(
                        f"✅ **Timezone Updated!**\n\n"
                        f"🌍 Timezone: {message_text}\n"
                        f"🕐 Current time: {time_str}\n\n"
                        f"All scheduled calls will now use this timezone."
                    )
                except:
                    await update.message.reply_text(f"✅ Timezone set to {message_text}")
                    
            except pytz.exceptions.UnknownTimeZoneError:
                await update.message.reply_text(
                    f"❌ **Invalid timezone:** {message_text}\n\n"
                    "Please use a valid timezone like:\n"
                    "• Asia/Singapore\n"
                    "• US/Eastern\n"
                    "• Europe/London\n"
                    "• Australia/Sydney\n"
                    "• UTC\n\n"
                    "Try again or check the Wikipedia link for more options."
                )
                return
            except Exception as e:
                await update.message.reply_text(f"❌ Error setting timezone: {str(e)}")
                return
        
        # Clear user state
        del self.user_states[user_id]
        
    async def timezone_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /timezone command"""
        user_id = update.effective_user.id
        user_settings = self.storage.get_user_settings(user_id)
        current_tz = user_settings.get('timezone', SYSTEM_TIMEZONE)
        
        # Get current time in user's timezone
        try:
            tz = pytz.timezone(current_tz)
            current_time = datetime.now(tz)
            time_str = current_time.strftime("%H:%M:%S %Z")
        except:
            time_str = "Unknown"
        
        timezone_text = f"🌍 **Your Timezone Settings:**\n\n"
        timezone_text += f"📍 Current: {current_tz}\n"
        timezone_text += f"🕐 Local time: {time_str}\n"
        timezone_text += f"🤖 Detected: {SYSTEM_TIMEZONE}\n\n"
        timezone_text += f"All scheduled calls use your timezone.\n"
        timezone_text += f"When you schedule for 09:30, it means 9:30 AM in {current_tz}."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Use Auto-Detected", callback_data="tz_auto")],
            [InlineKeyboardButton("⚙️ Manual Setup", callback_data="tz_manual")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            timezone_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    def run(self):
        """Run the bot"""
        logger.info("Starting bot...")
        
        # Start scheduler
        self.scheduler.start()
        
        # Run bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        
        # Stop scheduler when bot stops
        self.scheduler.stop()