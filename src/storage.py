#!/usr/bin/env python3
"""
storage.py - Data Storage Manager

This file handles all data persistence for the bot.
Manages scheduled calls, user settings, and data validation.
"""

import pytz
import json
import os
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from config import *

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ScheduledCall:
    """Data class for scheduled call information"""
    call_id: str
    user_id: int
    type: str  # 'once', 'daily', 'weekly'
    time: str  # HH:MM format
    message: str
    created_at: str
    active: bool = True
    weekday: Optional[str] = None  # For weekly calls
    date: Optional[str] = None  # For one-time calls (YYYY-MM-DD)
    last_executed: Optional[str] = None
    execution_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledCall':
        """Create instance from dictionary"""
        return cls(**data)

@dataclass
class UserSettings:
    """Data class for user settings"""
    user_id: int
    username: Optional[str] = None
    phone: Optional[str] = None
    language: str = DEFAULT_CALL_SETTINGS['language']
    repeat: int = DEFAULT_CALL_SETTINGS['repeat']
    timeout: int = DEFAULT_CALL_SETTINGS['timeout']
    send_text_copy: bool = DEFAULT_CALL_SETTINGS['send_text_copy']
    timezone: str = DEFAULT_USER_TIMEZONE  # Use detected timezone
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # Add timezone utility functions
    def get_user_timezone(user_settings: Dict[str, Any]) -> pytz.timezone:
        """Get user's timezone object"""
        tz_name = user_settings.get('timezone', DEFAULT_USER_TIMEZONE)
        try:
            return pytz.timezone(tz_name)
        except:
            return pytz.timezone('UTC')

    def now_in_timezone(timezone_name: str) -> datetime:
        """Get current time in specified timezone"""
        try:
            tz = pytz.timezone(timezone_name)
            return datetime.now(tz)
        except:
            return datetime.now()

    def convert_time_to_user_tz(time_str: str, user_timezone: str) -> datetime:
        """Convert HH:MM time string to datetime in user's timezone"""
        try:
            from datetime import time
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            
            # Get user timezone
            tz = pytz.timezone(user_timezone)
            
            # Create datetime for today in user's timezone
            today = datetime.now(tz).date()
            dt = datetime.combine(today, time_obj)
            
            # Localize to user's timezone
            return tz.localize(dt)
            
        except Exception as e:
            # Fallback to local time
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            today = datetime.now().date()
            return datetime.combine(today, time_obj)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSettings':
        """Create instance from dictionary"""
        return cls(**data)

class StorageManager:
    """Manages all data storage operations"""
    
    def __init__(self):
        """Initialize the storage manager"""
        self.scheduled_calls_file = SCHEDULED_CALLS_FILE
        self.user_settings_file = USER_SETTINGS_FILE
        
        # Thread lock for file operations
        self._lock = threading.Lock()
        
        # In-memory cache
        self._scheduled_calls: Dict[str, ScheduledCall] = {}
        self._user_settings: Dict[int, UserSettings] = {}
        
        # Load existing data
        self.load_all_data()
        
        logger.info("StorageManager initialized")
    
    def load_all_data(self):
        """Load all data from files into memory"""
        try:
            self.load_scheduled_calls()
            self.load_user_settings()
            logger.info("All data loaded successfully")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def load_scheduled_calls(self):
        """Load scheduled calls from file"""
        try:
            if os.path.exists(self.scheduled_calls_file):
                with open(self.scheduled_calls_file, 'r') as f:
                    data = json.load(f)
                
                # Convert to ScheduledCall objects
                for call_data in data.values():
                    call = ScheduledCall.from_dict(call_data)
                    self._scheduled_calls[call.call_id] = call
                
                logger.info(f"Loaded {len(self._scheduled_calls)} scheduled calls")
            else:
                logger.info("No existing scheduled calls file found")
                
        except Exception as e:
            logger.error(f"Error loading scheduled calls: {e}")
            self._scheduled_calls = {}
    
    def load_user_settings(self):
        """Load user settings from file"""
        try:
            if os.path.exists(self.user_settings_file):
                with open(self.user_settings_file, 'r') as f:
                    data = json.load(f)
                
                # Convert to UserSettings objects
                for user_id_str, settings_data in data.items():
                    user_id = int(user_id_str)
                    settings = UserSettings.from_dict(settings_data)
                    self._user_settings[user_id] = settings
                
                logger.info(f"Loaded settings for {len(self._user_settings)} users")
            else:
                logger.info("No existing user settings file found")
                
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
            self._user_settings = {}
    
    def save_scheduled_calls(self):
        """Save scheduled calls to file"""
        try:
            with self._lock:
                # Convert to serializable format
                data = {}
                for call_id, call in self._scheduled_calls.items():
                    data[call_id] = call.to_dict()
                
                # Write to file
                with open(self.scheduled_calls_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.debug(f"Saved {len(data)} scheduled calls to file")
                
        except Exception as e:
            logger.error(f"Error saving scheduled calls: {e}")
    
    def save_user_settings(self):
        """Save user settings to file"""
        try:
            with self._lock:
                # Convert to serializable format
                data = {}
                for user_id, settings in self._user_settings.items():
                    data[str(user_id)] = settings.to_dict()
                
                # Write to file
                with open(self.user_settings_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.debug(f"Saved settings for {len(data)} users to file")
                
        except Exception as e:
            logger.error(f"Error saving user settings: {e}")
    
    def add_scheduled_call(self, user_id: int, call_data: Dict[str, Any]) -> str:
        """
        Add a new scheduled call
        
        Args:
            user_id: User's Telegram ID
            call_data: Call configuration data
            
        Returns:
            str: Generated call ID
        """
        try:
            # Generate unique call ID
            call_id = self.generate_call_id()
            
            # Create ScheduledCall object
            call = ScheduledCall(
                call_id=call_id,
                user_id=user_id,
                type=call_data['type'],
                time=call_data['time'],
                message=call_data['message'],
                created_at=datetime.now().isoformat(),
                weekday=call_data.get('weekday'),
                date=call_data.get('date')
            )
            
            # Add to memory cache
            self._scheduled_calls[call_id] = call
            
            # Save to file
            self.save_scheduled_calls()
            
            logger.info(f"Added scheduled call {call_id} for user {user_id}")
            return call_id
            
        except Exception as e:
            logger.error(f"Error adding scheduled call: {e}")
            raise
    
    def get_scheduled_call(self, call_id: str) -> Optional[ScheduledCall]:
        """Get a specific scheduled call by ID"""
        return self._scheduled_calls.get(call_id)
    
    def get_user_calls(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get all scheduled calls for a user
        
        Returns:
            Dict with call_id as key and call data as value
        """
        user_calls = {}
        for call_id, call in self._scheduled_calls.items():
            if call.user_id == user_id:
                user_calls[call_id] = call.to_dict()
        
        return user_calls
    
    def get_all_active_calls(self) -> Dict[str, ScheduledCall]:
        """Get all active scheduled calls"""
        return {
            call_id: call for call_id, call in self._scheduled_calls.items()
            if call.active
        }
    
    def update_scheduled_call(self, call_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a scheduled call
        
        Args:
            call_id: Call ID to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if successful
        """
        try:
            if call_id not in self._scheduled_calls:
                return False
            
            call = self._scheduled_calls[call_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(call, field):
                    setattr(call, field, value)
            
            # Save changes
            self.save_scheduled_calls()
            
            logger.info(f"Updated scheduled call {call_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating scheduled call {call_id}: {e}")
            return False
    
    def delete_scheduled_call(self, call_id: str) -> bool:
        """
        Delete a scheduled call
        
        Args:
            call_id: Call ID to delete
            
        Returns:
            bool: True if successful
        """
        try:
            if call_id in self._scheduled_calls:
                del self._scheduled_calls[call_id]
                self.save_scheduled_calls()
                logger.info(f"Deleted scheduled call {call_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting scheduled call {call_id}: {e}")
            return False
    
    def toggle_call_active(self, call_id: str) -> bool:
        """
        Toggle active status of a scheduled call
        
        Returns:
            bool: New active status
        """
        if call_id in self._scheduled_calls:
            call = self._scheduled_calls[call_id]
            call.active = not call.active
            self.save_scheduled_calls()
            logger.info(f"Toggled call {call_id} active status to {call.active}")
            return call.active
        return False
    
    def mark_call_executed(self, call_id: str):
        """Mark a call as executed (update execution stats)"""
        if call_id in self._scheduled_calls:
            call = self._scheduled_calls[call_id]
            call.last_executed = datetime.now().isoformat()
            call.execution_count += 1
            
            # For one-time calls, mark as inactive after execution
            if call.type == 'once':
                call.active = False
            
            self.save_scheduled_calls()
            logger.info(f"Marked call {call_id} as executed (count: {call.execution_count})")
    
    def initialize_user(self, user_id: int) -> UserSettings:
        """Initialize a new user with default settings"""
        if user_id not in self._user_settings:
            settings = UserSettings(
                user_id=user_id,
                created_at=datetime.now().isoformat()
            )
            self._user_settings[user_id] = settings
            self.save_user_settings()
            logger.info(f"Initialized new user {user_id}")
        
        return self._user_settings[user_id]
    
    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user settings as dictionary"""
        if user_id not in self._user_settings:
            self.initialize_user(user_id)
        
        return self._user_settings[user_id].to_dict()
    
    def update_user_settings(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update user settings
        
        Args:
            user_id: User's Telegram ID
            updates: Dictionary of settings to update
            
        Returns:
            bool: True if successful
        """
        try:
            if user_id not in self._user_settings:
                self.initialize_user(user_id)
            
            settings = self._user_settings[user_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(settings, field):
                    setattr(settings, field, value)
            
            # Update timestamp
            settings.updated_at = datetime.now().isoformat()
            
            # Save changes
            self.save_user_settings()
            
            logger.info(f"Updated settings for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user settings for {user_id}: {e}")
            return False
    
    def generate_call_id(self) -> str:
        """Generate a unique call ID"""
        # Use timestamp + short UUID for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"call_{timestamp}_{short_uuid}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_calls = len(self._scheduled_calls)
        active_calls = len([call for call in self._scheduled_calls.values() if call.active])
        total_users = len(self._user_settings)
        
        # Count calls by type
        call_types = {}
        for call in self._scheduled_calls.values():
            call_types[call.type] = call_types.get(call.type, 0) + 1
        
        return {
            'total_calls': total_calls,
            'active_calls': active_calls,
            'inactive_calls': total_calls - active_calls,
            'total_users': total_users,
            'call_types': call_types,
            'files': {
                'scheduled_calls': os.path.exists(self.scheduled_calls_file),
                'user_settings': os.path.exists(self.user_settings_file)
            }
        }
    
    def cleanup_old_calls(self, days_old: int = 30):
        """
        Clean up old inactive one-time calls
        
        Args:
            days_old: Remove calls older than this many days
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            calls_to_remove = []
            for call_id, call in self._scheduled_calls.items():
                if (call.type == 'once' and 
                    not call.active and 
                    call.last_executed and
                    datetime.fromisoformat(call.last_executed) < cutoff_date):
                    calls_to_remove.append(call_id)
            
            # Remove old calls
            for call_id in calls_to_remove:
                del self._scheduled_calls[call_id]
            
            if calls_to_remove:
                self.save_scheduled_calls()
                logger.info(f"Cleaned up {len(calls_to_remove)} old calls")
            
            return len(calls_to_remove)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def backup_data(self, backup_dir: str = "backups"):
        """Create a backup of all data"""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Backup scheduled calls
            if os.path.exists(self.scheduled_calls_file):
                backup_file = os.path.join(backup_dir, f"scheduled_calls_{timestamp}.json")
                with open(self.scheduled_calls_file, 'r') as src:
                    with open(backup_file, 'w') as dst:
                        dst.write(src.read())
            
            # Backup user settings
            if os.path.exists(self.user_settings_file):
                backup_file = os.path.join(backup_dir, f"user_settings_{timestamp}.json")
                with open(self.user_settings_file, 'r') as src:
                    with open(backup_file, 'w') as dst:
                        dst.write(src.read())
            
            logger.info(f"Data backup created in {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False

# Utility functions for external use
def validate_call_data(call_data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate call data before storage
    
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = ['type', 'time', 'message']
    
    # Check required fields
    for field in required_fields:
        if field not in call_data:
            return False, f"Missing required field: {field}"
    
    # Validate schedule type
    if call_data['type'] not in VALID_SCHEDULE_TYPES:
        return False, ERROR_MESSAGES["invalid_schedule_type"]
    
    # Validate time format
    if not validate_time_format(call_data['time']):
        return False, ERROR_MESSAGES["invalid_time_format"]
    
    # Validate message
    is_valid, error_msg = validate_message(call_data['message'])
    if not is_valid:
        return False, error_msg
    
    # Validate weekday for weekly calls
    if call_data['type'] == 'weekly':
        weekday = call_data.get('weekday', '').lower()
        if weekday not in VALID_WEEKDAYS:
            return False, ERROR_MESSAGES["invalid_weekday"]
    
    return True, ""

if __name__ == "__main__":
    # Test the storage manager
    print("Testing StorageManager...")
    
    storage = StorageManager()
    stats = storage.get_stats()
    
    print("Storage Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")