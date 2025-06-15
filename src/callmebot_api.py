#!/usr/bin/env python3
"""
callmebot_api.py - CallMeBot API Integration

This file handles all interactions with the CallMeBot API.
Makes actual voice calls through Telegram using CallMeBot service.
"""

import asyncio
import logging
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import requests
from datetime import datetime

from config import *

# Configure logging
logger = logging.getLogger(__name__)

class CallMeBotAPI:
    """Handles CallMeBot API interactions for making voice calls"""
    
    def __init__(self):
        """Initialize the CallMeBot API client"""
        self.api_url = CALLMEBOT_API_URL
        self.session = requests.Session()
        
        # Set reasonable timeout and headers
        self.session.timeout = 30
        self.session.headers.update({
            'User-Agent': f'{BOT_NAME}/{BOT_VERSION}',
            'Accept': 'application/json, text/plain, */*'
        })
        
        logger.info("CallMeBotAPI initialized")
    
    async def make_call(self, target: str, message: str, user_settings: Dict[str, Any] = None) -> bool:
        """
        Make a voice call using CallMeBot API
        
        Args:
            target (str): Username (@username) or phone number (+1234567890)
            message (str): Message to be spoken during the call
            user_settings (dict): User's call preferences
            
        Returns:
            bool: True if call was initiated successfully
        """
        try:
            # Prepare call parameters
            call_params = self._prepare_call_params(target, message, user_settings)
            
            logger.info(f"Making call to {target[:10]}... with message: {message[:30]}...")
            
            # Make async HTTP request
            success, response_data = await self._make_api_request(call_params)
            
            if success:
                logger.info(f"Call initiated successfully to {target[:10]}...")
                return True
            else:
                logger.error(f"Call failed to {target[:10]}...: {response_data}")
                return False
                
        except Exception as e:
            logger.error(f"Error making call: {e}")
            return False
    
    def _prepare_call_params(self, target: str, message: str, user_settings: Dict[str, Any] = None) -> Dict[str, str]:
        """Prepare API call parameters"""
        if user_settings is None:
            user_settings = {}
        
        # Get settings with defaults
        language = user_settings.get('language', 'en-US-Standard-B')  # Use specific voice
        repeat = user_settings.get('repeat', DEFAULT_CALL_SETTINGS['repeat'])
        timeout = user_settings.get('timeout', DEFAULT_CALL_SETTINGS['timeout'])
        send_text_copy = user_settings.get('send_text_copy', DEFAULT_CALL_SETTINGS['send_text_copy'])
        
        # Clean inputs
        clean_target = self._clean_target(target)
        clean_message = self._clean_message(message)
        encoded_message = urllib.parse.quote(clean_message)
        
        # Text copy setting
        cc = "yes" if send_text_copy else "no"
        
        # Build parameters with source=web
        params = {
            'source': 'web',  # ADD THIS
            'user': clean_target,
            'text': encoded_message,
            'lang': language,  # Now uses en-US-Standard-B
            'rpt': str(repeat),
            'cc': cc,
            'timeout': str(timeout)
        }
        
        return params
    
    def _clean_target(self, target: str) -> str:
        """Clean and validate target username or phone"""
        target = target.strip()
        
        # If it looks like a username, ensure it starts with @
        if not target.startswith('@') and not target.startswith('+'):
            if target.isalpha() or '_' in target:
                target = f"@{target}"
        
        return target
    
    def _clean_message(self, message: str) -> str:
        """Clean and validate message text"""
        # Remove excessive whitespace
        message = ' '.join(message.split())
        
        # Ensure message length is within limits
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH-3] + "..."
            logger.warning(f"Message truncated to {MAX_MESSAGE_LENGTH} characters")
        
        return message
    
    async def _make_api_request(self, params: Dict[str, str]) -> Tuple[bool, str]:
        """Make async HTTP request to CallMeBot API"""
        try:
            # BUILD THE FULL URL FOR DEBUGGING (handle encoding)
            full_url = f"{self.api_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
            print(f"DEBUG URL: {full_url}")  # Use print instead of logger
            
            # Run the synchronous request in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.get(self.api_url, params=params, timeout=30)
            )
            
            # Log response with print
            print(f"DEBUG Response: {response.status_code}")
            print(f"DEBUG Text: {response.text}")
            
            # Check response
            if response.status_code == 200:
                return True, response.text
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except Exception as e:
            print(f"Request error: {str(e)}")
            return False, f"Request error: {str(e)}"
    
    async def test_call(self, target: str, test_message: str = None) -> Tuple[bool, str]:
        """
        Make a test call to verify functionality
        
        Args:
            target: Target username or phone
            test_message: Optional custom test message
            
        Returns:
            Tuple of (success, status_message)
        """
        if test_message is None:
            test_message = "This is a test call from your Telegram Call Scheduler Bot. If you hear this message, everything is working correctly!"
        
        try:
            logger.info(f"Making test call to {target[:10]}...")
            
            # Use default settings for test
            test_settings = {
                'language': 'en',
                'repeat': 1,
                'timeout': 30,
                'send_text_copy': True
            }
            
            success = await self.make_call(target, test_message, test_settings)
            
            if success:
                return True, "Test call initiated successfully! Check your phone."
            else:
                return False, "Test call failed. Please check your CallMeBot authorization and target."
                
        except Exception as e:
            logger.error(f"Test call error: {e}")
            return False, f"Test call error: {str(e)}"
    
    def validate_target(self, target: str) -> Tuple[bool, str]:
        """
        Validate target username or phone number
        
        Args:
            target: Target to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not target or not target.strip():
            return False, "Target cannot be empty"
        
        target = target.strip()
        
        # Check if it's a username
        if target.startswith('@'):
            username = target[1:]
            if len(username) < 3:
                return False, "Username too short (minimum 3 characters)"
            if len(username) > 32:
                return False, "Username too long (maximum 32 characters)"
            if not username.replace('_', '').isalnum():
                return False, "Username can only contain letters, numbers, and underscores"
            return True, ""
        
        # Check if it's a phone number
        elif target.startswith('+'):
            phone = target[1:]
            if not phone.isdigit():
                return False, "Phone number can only contain digits after +"
            if len(phone) < 7 or len(phone) > 15:
                return False, "Phone number must be 7-15 digits"
            return True, ""
        
        # Try to determine type
        else:
            if target.isdigit():
                return False, "Phone numbers must start with + (e.g., +1234567890)"
            else:
                return False, "Usernames must start with @ (e.g., @username)"
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get available languages for text-to-speech"""
        return AVAILABLE_LANGUAGES.copy()
    
    def validate_language(self, language: str) -> bool:
        """Check if language code is valid"""
        return language in AVAILABLE_LANGUAGES.values()
    
    async def check_api_status(self) -> Tuple[bool, str]:
        """
        Check if CallMeBot API is accessible
        
        Returns:
            Tuple of (is_accessible, status_message)
        """
        try:
            # Make a simple request to check connectivity
            test_params = {
                'user': '@test',
                'text': 'test',
                'lang': 'en'
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.get(self.api_url, params=test_params, timeout=10)
            )
            
            if response.status_code in [200, 400, 403]:  # API is responding
                return True, "CallMeBot API is accessible"
            else:
                return False, f"API returned status {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "API request timeout"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to CallMeBot API"
        except Exception as e:
            return False, f"API check error: {str(e)}"
    
    def get_call_stats(self) -> Dict[str, Any]:
        """Get API usage statistics (basic implementation)"""
        # This is a basic implementation - could be enhanced
        # to track actual usage statistics
        return {
            "api_url": self.api_url,
            "session_active": True,
            "default_language": DEFAULT_CALL_SETTINGS['language'],
            "available_languages": len(AVAILABLE_LANGUAGES),
            "max_message_length": MAX_MESSAGE_LENGTH
        }
    
    def close(self):
        """Close the HTTP session"""
        try:
            self.session.close()
            logger.info("CallMeBot API session closed")
        except Exception as e:
            logger.error(f"Error closing API session: {e}")

# Utility functions for testing and validation
async def test_callmebot_api():
    """Test function for CallMeBot API"""
    print("Testing CallMeBot API...")
    
    api = CallMeBotAPI()
    
    # Test API status
    accessible, status = await api.check_api_status()
    print(f"API Status: {status}")
    
    # Test target validation
    valid_targets = ["@testuser", "+1234567890"]
    invalid_targets = ["testuser", "1234567890", "@ab", ""]
    
    print("\nTesting target validation:")
    for target in valid_targets + invalid_targets:
        is_valid, error = api.validate_target(target)
        print(f"  {target}: {'✅' if is_valid else '❌'} {error}")
    
    # Test language validation
    print(f"\nAvailable languages: {len(api.get_available_languages())}")
    print(f"Language 'en' valid: {api.validate_language('en')}")
    print(f"Language 'invalid' valid: {api.validate_language('invalid')}")
    
    # Get stats
    stats = api.get_call_stats()
    print(f"\nAPI Stats: {stats}")
    
    api.close()
    print("Test complete")

if __name__ == "__main__":
    asyncio.run(test_callmebot_api())