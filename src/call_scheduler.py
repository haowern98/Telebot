#!/usr/bin/env python3
"""
call_scheduler.py - Background Call Scheduler

This file handles the background scheduling and execution of calls.
Monitors scheduled calls and triggers them at the appropriate times.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import schedule
import pytz

from config import *

# Configure logging
logger = logging.getLogger(__name__)

class CallScheduler:
    """Manages background scheduling and execution of calls"""
    
    def __init__(self, storage_manager, callmebot_api=None):
        """
        Initialize the call scheduler
        
        Args:
            storage_manager: StorageManager instance
            callmebot_api: CallMeBotAPI instance (will be set later)
        """
        self.storage = storage_manager
        self.callmebot = callmebot_api
        
        # Threading control
        self._scheduler_thread = None
        self._running = False
        self._stop_event = threading.Event()
        
        # Track scheduled jobs
        self._scheduled_jobs = {}
        
        logger.info("CallScheduler initialized")
        
    def _get_user_timezone(self, user_id: int) -> pytz.timezone:
        """Get user's timezone"""
        try:
            user_settings = self.storage.get_user_settings(user_id)
            tz_name = user_settings.get('timezone', DEFAULT_USER_TIMEZONE)
            return pytz.timezone(tz_name)
        except:
            return pytz.timezone(DEFAULT_USER_TIMEZONE)

    def _schedule_call_job(self, call_id: str, call):
        """Schedule a single call job with timezone awareness"""
        try:
            call_time = call.time
            call_type = call.type
            user_tz = self._get_user_timezone(call.user_id)
            
            # Create job function
            def job():
                asyncio.create_task(self._execute_call(call_id))
            
            # Schedule based on call type with timezone awareness
            if call_type == "daily":
                schedule.every().day.at(call_time).do(job).tag(call_id)
                logger.debug(f"Scheduled daily call {call_id} at {call_time} ({user_tz})")
                
            elif call_type == "weekly":
                weekday = call.weekday.lower()
                if weekday in VALID_WEEKDAYS:
                    getattr(schedule.every(), weekday).at(call_time).do(job).tag(call_id)
                    logger.debug(f"Scheduled weekly call {call_id} on {weekday} at {call_time} ({user_tz})")
                else:
                    logger.error(f"Invalid weekday for call {call_id}: {weekday}")
                    return
                    
            elif call_type == "once":
                if call.date:
                    # Parse date and time in user's timezone
                    call_datetime_str = f"{call.date} {call_time}"
                    call_datetime = datetime.strptime(call_datetime_str, f"{DATE_FORMAT} {TIME_FORMAT}")
                    
                    # Localize to user's timezone
                    call_datetime = user_tz.localize(call_datetime)
                    now_user_tz = datetime.now(user_tz)
                    
                    if call_datetime > now_user_tz:
                        schedule.every().day.at(call_time).do(job).tag(call_id)
                        logger.debug(f"Scheduled one-time call {call_id} for {call.date} at {call_time} ({user_tz})")
                    else:
                        # Time has passed, mark as inactive
                        self.storage.update_scheduled_call(call_id, {"active": False})
                        logger.info(f"One-time call {call_id} time has passed, marked inactive")
                        return
                else:
                    logger.error(f"One-time call {call_id} missing date")
                    return
            
            # Track the job
            self._scheduled_jobs[call_id] = {
                "type": call_type,
                "time": call_time,
                "weekday": getattr(call, 'weekday', None),
                "date": getattr(call, 'date', None),
                "user_timezone": str(user_tz)
            }
            
        except Exception as e:
            logger.error(f"Error scheduling call {call_id}: {e}")
    
    def set_callmebot_api(self, callmebot_api):
        """Set the CallMeBot API instance (used for dependency injection)"""
        self.callmebot = callmebot_api
        logger.info("CallMeBot API instance set in scheduler")
    
    def start(self):
        """Start the background scheduler"""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting call scheduler...")
        self._running = True
        self._stop_event.clear()
        
        # Load existing scheduled calls
        self._load_scheduled_calls()
        
        # Start scheduler thread
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        logger.info("Call scheduler started successfully")
    
    def stop(self):
        """Stop the background scheduler"""
        if not self._running:
            return
        
        logger.info("Stopping call scheduler...")
        self._running = False
        self._stop_event.set()
        
        # Clear all scheduled jobs
        schedule.clear()
        self._scheduled_jobs.clear()
        
        # Wait for thread to finish
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)
        
        logger.info("Call scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop that runs in background thread"""
        logger.info("Scheduler loop started")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Run pending scheduled jobs
                schedule.run_pending()
                
                # Check for any missed calls (in case bot was down)
                self._check_missed_calls()
                
                # Sleep for the configured interval
                time.sleep(SCHEDULER_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        logger.info("Scheduler loop ended")
    
    def _load_scheduled_calls(self):
        """Load all active scheduled calls and set up jobs"""
        if not self.storage:
            logger.warning("No storage manager available")
            return
        
        try:
            active_calls = self.storage.get_all_active_calls()
            logger.info(f"Loading {len(active_calls)} active calls")
            
            for call_id, call in active_calls.items():
                self._schedule_call_job(call_id, call)
            
            logger.info(f"Loaded {len(self._scheduled_jobs)} scheduled jobs")
            
        except Exception as e:
            logger.error(f"Error loading scheduled calls: {e}")
    
    def _schedule_call_job(self, call_id: str, call):
        """Schedule a single call job"""
        try:
            call_time = call.time
            call_type = call.type
            
            # Create job function
            def job():
                asyncio.create_task(self._execute_call(call_id))
            
            # Schedule based on call type
            if call_type == "daily":
                schedule.every().day.at(call_time).do(job).tag(call_id)
                logger.debug(f"Scheduled daily call {call_id} at {call_time}")
                
            elif call_type == "weekly":
                weekday = call.weekday.lower()
                if weekday in VALID_WEEKDAYS:
                    getattr(schedule.every(), weekday).at(call_time).do(job).tag(call_id)
                    logger.debug(f"Scheduled weekly call {call_id} on {weekday} at {call_time}")
                else:
                    logger.error(f"Invalid weekday for call {call_id}: {weekday}")
                    return
                    
            elif call_type == "once":
                # For one-time calls, we need to check if the time has passed
                if call.date:
                    call_datetime = datetime.strptime(f"{call.date} {call_time}", f"{DATE_FORMAT} {TIME_FORMAT}")
                    if call_datetime > datetime.now():
                        # Schedule for specific date/time
                        schedule.every().day.at(call_time).do(job).tag(call_id)
                        logger.debug(f"Scheduled one-time call {call_id} for {call.date} at {call_time}")
                    else:
                        # Time has passed, mark as inactive
                        self.storage.update_scheduled_call(call_id, {"active": False})
                        logger.info(f"One-time call {call_id} time has passed, marked inactive")
                        return
                else:
                    logger.error(f"One-time call {call_id} missing date")
                    return
            
            # Track the job
            self._scheduled_jobs[call_id] = {
                "type": call_type,
                "time": call_time,
                "weekday": getattr(call, 'weekday', None),
                "date": getattr(call, 'date', None)
            }
            
        except Exception as e:
            logger.error(f"Error scheduling call {call_id}: {e}")
    
    async def _execute_call(self, call_id: str):
        """Execute a scheduled call"""
        try:
            logger.info(f"Executing scheduled call {call_id}")
            
            # Get call details from storage
            call = self.storage.get_scheduled_call(call_id)
            if not call:
                logger.error(f"Call {call_id} not found in storage")
                return
            
            if not call.active:
                logger.info(f"Call {call_id} is inactive, skipping")
                return
            
            # Get user settings
            user_settings = self.storage.get_user_settings(call.user_id)
            
            # Determine target (username or phone)
            target = user_settings.get('username') or user_settings.get('phone')
            if not target:
                logger.error(f"No username or phone configured for user {call.user_id}")
                return
            
            # Make the call
            if self.callmebot:
                success = await self.callmebot.make_call(target, call.message, user_settings)
                
                if success:
                    logger.info(f"Call {call_id} executed successfully")
                    # Mark call as executed
                    self.storage.mark_call_executed(call_id)
                    
                    # For one-time calls, remove from scheduler
                    if call.type == "once":
                        self._remove_call_job(call_id)
                        
                else:
                    logger.error(f"Call {call_id} execution failed")
                    
                    # Retry logic
                    if RETRY_FAILED_CALLS:
                        await self._retry_call(call_id, call)
            else:
                logger.error("CallMeBot API not available")
                
        except Exception as e:
            logger.error(f"Error executing call {call_id}: {e}")
    
    async def _retry_call(self, call_id: str, call, retry_count: int = 1):
        """Retry a failed call"""
        if retry_count > MAX_CALL_RETRIES:
            logger.error(f"Call {call_id} failed after {MAX_CALL_RETRIES} retries")
            return
        
        logger.info(f"Retrying call {call_id} (attempt {retry_count})")
        
        # Wait before retry
        await asyncio.sleep(30 * retry_count)  # Exponential backoff
        
        try:
            user_settings = self.storage.get_user_settings(call.user_id)
            target = user_settings.get('username') or user_settings.get('phone')
            
            if target and self.callmebot:
                success = await self.callmebot.make_call(target, call.message, user_settings)
                
                if success:
                    logger.info(f"Call {call_id} retry successful")
                    self.storage.mark_call_executed(call_id)
                else:
                    # Try again
                    await self._retry_call(call_id, call, retry_count + 1)
            
        except Exception as e:
            logger.error(f"Error retrying call {call_id}: {e}")
    
    def _check_missed_calls(self):
        """Check for calls that might have been missed while bot was down"""
        try:
            # This is a simple implementation - could be enhanced
            # to track and execute missed calls
            pass
            
        except Exception as e:
            logger.error(f"Error checking missed calls: {e}")
    
    def add_call(self, user_id: int, call_id: str, call_data: Dict[str, Any]):
        """Add a new call to the scheduler"""
        try:
            # Get the full call object from storage
            call = self.storage.get_scheduled_call(call_id)
            if call:
                self._schedule_call_job(call_id, call)
                logger.info(f"Added call {call_id} to scheduler")
            else:
                logger.error(f"Call {call_id} not found in storage")
                
        except Exception as e:
            logger.error(f"Error adding call {call_id} to scheduler: {e}")
    
    def remove_call(self, call_id: str):
        """Remove a call from the scheduler"""
        try:
            self._remove_call_job(call_id)
            logger.info(f"Removed call {call_id} from scheduler")
            
        except Exception as e:
            logger.error(f"Error removing call {call_id} from scheduler: {e}")
    
    def _remove_call_job(self, call_id: str):
        """Remove a specific call job from schedule"""
        try:
            # Remove from schedule
            schedule.clear(call_id)
            
            # Remove from tracking
            if call_id in self._scheduled_jobs:
                del self._scheduled_jobs[call_id]
            
        except Exception as e:
            logger.error(f"Error removing call job {call_id}: {e}")
    
    def update_call(self, call_id: str, call_data: Dict[str, Any]):
        """Update an existing scheduled call"""
        try:
            # Remove old job
            self._remove_call_job(call_id)
            
            # Add updated job
            call = self.storage.get_scheduled_call(call_id)
            if call and call.active:
                self._schedule_call_job(call_id, call)
                logger.info(f"Updated call {call_id} in scheduler")
            
        except Exception as e:
            logger.error(f"Error updating call {call_id} in scheduler: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return {
            "running": self._running,
            "scheduled_jobs": len(self._scheduled_jobs),
            "schedule_jobs": len(schedule.jobs),
            "jobs_by_type": self._get_jobs_by_type()
        }
    
    def _get_jobs_by_type(self) -> Dict[str, int]:
        """Get count of jobs by type"""
        job_counts = {"daily": 0, "weekly": 0, "once": 0}
        
        for job_info in self._scheduled_jobs.values():
            job_type = job_info.get("type", "unknown")
            if job_type in job_counts:
                job_counts[job_type] += 1
        
        return job_counts
    
    def list_scheduled_jobs(self) -> Dict[str, Any]:
        """List all currently scheduled jobs"""
        return dict(self._scheduled_jobs)

# Utility functions for testing and development
def test_scheduler():
    """Test function for the scheduler"""
    print("Testing CallScheduler...")
    
    # Mock storage manager
    class MockStorage:
        def get_all_active_calls(self):
            return {}
        
        def get_scheduled_call(self, call_id):
            return None
        
        def get_user_settings(self, user_id):
            return {}
        
        def mark_call_executed(self, call_id):
            pass
    
    # Create scheduler
    storage = MockStorage()
    scheduler = CallScheduler(storage)
    
    # Test start/stop
    scheduler.start()
    print("Scheduler started")
    
    time.sleep(2)
    
    scheduler.stop()
    print("Scheduler stopped")
    
    print("Test complete")

if __name__ == "__main__":
    test_scheduler()