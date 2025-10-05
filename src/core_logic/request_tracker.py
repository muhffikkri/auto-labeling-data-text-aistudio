#!/usr/bin/env python3
"""
request_tracker.py - Advanced Request Tracking and Monitoring System

Sistem untuk melacak semua request ke Google Generative AI dengan detail:
- Counter per API key dan per model
- Response time tracking
- Success/failure rate
- Quota usage monitoring
- Request statistics dan reporting

Author: Auto-generated for auto-labeling-data-text-aistudio project
Date: October 2025
"""

import os
import json
import time
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder untuk menangani tipe data numpy/pandas
    yang tidak bisa di-serialize secara default
    """
    def default(self, obj):
        # Handle numpy data types
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, np.bool8)):
            return bool(obj)
        # Handle pandas data types
        elif hasattr(obj, 'item'):  # pandas scalars
            return obj.item()
        elif hasattr(obj, 'to_dict'):  # pandas objects with to_dict method
            return obj.to_dict()
        # Handle datetime objects
        elif isinstance(obj, datetime):
            return obj.isoformat()
        # Default behavior
        return super().default(obj)

@dataclass
class RequestMetrics:
    """Data class untuk menyimpan metrics setiap request"""
    request_id: int
    timestamp: str
    api_key_index: int
    model_name: str
    success: bool
    response_time: float
    error_message: Optional[str] = None
    batch_info: Optional[str] = None
    tokens_used: Optional[int] = None

class RequestTracker:
    """
    Class untuk tracking semua request dengan statistik detail
    """
    
    def __init__(self, stats_file: str = "logs/request_stats.json"):
        self.stats_file = stats_file
        self.current_session_requests = []
        self.session_start_time = datetime.now()
        
        # Counters per session
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Counters per API key
        self.requests_per_api_key = defaultdict(int)
        self.success_per_api_key = defaultdict(int)
        
        # Counters per model
        self.requests_per_model = defaultdict(int)
        self.success_per_model = defaultdict(int)
        
        # API stats tracking - NEW
        self.api_stats = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0
        })
        
        # Response time tracking
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Load historical data if exists
        self._load_historical_stats()
        
        # Create logs directory if not exists
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
    
    def record_request(self, 
                      api_key_index: int, 
                      model_name: str, 
                      success: bool, 
                      response_time: float, 
                      error_message: Optional[str] = None,
                      batch_info: Optional[str] = None,
                      tokens_used: Optional[int] = None) -> int:
        """
        Record sebuah request dengan semua metrics
        
        Returns:
            int: Request ID untuk tracking
        """
        with self.lock:
            self.total_requests += 1
            request_id = self.total_requests
            
            # Create metrics object
            metrics = RequestMetrics(
                request_id=request_id,
                timestamp=datetime.now().isoformat(),
                api_key_index=api_key_index,
                model_name=model_name,
                success=success,
                response_time=response_time,
                error_message=error_message,
                batch_info=batch_info,
                tokens_used=tokens_used
            )
            
            # Update counters
            if success:
                self.successful_requests += 1
                self.success_per_api_key[api_key_index] += 1
                self.success_per_model[model_name] += 1
                self.api_stats[api_key_index]['successful_requests'] += 1
            else:
                self.failed_requests += 1
                self.api_stats[api_key_index]['failed_requests'] += 1
            
            self.requests_per_api_key[api_key_index] += 1
            self.requests_per_model[model_name] += 1
            self.response_times.append(response_time)
            
            # Update API stats
            self.api_stats[api_key_index]['total_requests'] += 1
            if tokens_used:
                self.api_stats[api_key_index]['total_tokens'] += tokens_used
                # Estimate cost - rough calculation for Gemini models
                estimated_cost = tokens_used * 0.000002  # Rough estimate
                self.api_stats[api_key_index]['total_cost'] += estimated_cost
            
            # Store in session requests
            self.current_session_requests.append(metrics)
            
            # Auto-save every 10 requests
            if request_id % 10 == 0:
                self._save_session_stats()
            
            return request_id
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for current session"""
        import time
        stats_start_time = time.time()
        STATS_TIMEOUT = 5  # 5 seconds timeout
        
        try:
            logging.info(f"🔄 Acquiring lock for stats calculation...")
            
            # Try to acquire lock with timeout
            lock_acquired = self.lock.acquire(blocking=False)
            lock_attempts = 0
            LOCK_TIMEOUT = 3  # 3 seconds for lock acquisition
            
            while not lock_acquired and lock_attempts < 30:  # 30 attempts * 0.1s = 3s timeout
                time.sleep(0.1)  # Wait 100ms between attempts
                lock_acquired = self.lock.acquire(blocking=False)
                lock_attempts += 1
                
                if lock_attempts % 10 == 0:  # Log every 1 second
                    logging.warning(f"⏳ Still waiting for lock... attempt {lock_attempts}/30")
            
            if not lock_acquired:
                logging.error(f"⏰ TIMEOUT: Could not acquire lock after {LOCK_TIMEOUT} seconds")
                return {"error": "timeout_acquiring_lock"}
            
            try:
                logging.info(f"🔒 Lock acquired successfully after {lock_attempts * 0.1:.1f} seconds")
                
                # Check timeout
                if time.time() - stats_start_time > STATS_TIMEOUT:
                    logging.error(f"⏰ TIMEOUT: Stats calculation exceeded {STATS_TIMEOUT} seconds")
                    return {"error": "timeout_during_stats_calculation"}
                
                session_duration = (datetime.now() - self.session_start_time).total_seconds()
                logging.info(f"📊 Building stats dictionary...")
                
                stats = {
                    'session_duration': session_duration,
                    'total_requests': sum(self.api_stats[key]['total_requests'] for key in self.api_stats),
                    'successful_requests': sum(self.api_stats[key]['successful_requests'] for key in self.api_stats),
                    'failed_requests': sum(self.api_stats[key]['failed_requests'] for key in self.api_stats),
                    'total_tokens': sum(self.api_stats[key]['total_tokens'] for key in self.api_stats),
                    'total_cost': sum(self.api_stats[key]['total_cost'] for key in self.api_stats),
                    'requests_per_minute': (sum(self.api_stats[key]['total_requests'] for key in self.api_stats) / session_duration * 60) if session_duration > 0 else 0,
                    'api_stats': dict(self.api_stats)  # Make a copy
                }
                
                logging.info(f"✅ Stats calculation completed successfully")
                return stats
                
            finally:
                # Always release the lock
                self.lock.release()
                logging.info(f"🔓 Lock released")
        
        except Exception as e:
            logging.error(f"❌ Error in get_current_stats: {str(e)}")
            return {"error": f"stats_calculation_error: {str(e)}"}
    
    def get_quota_predictions(self, known_limits: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Prediksi penggunaan quota berdasarkan pattern request
        
        Args:
            known_limits: Dict dengan format {"model_name": daily_limit}
        """
        if known_limits is None:
            # Default limits berdasarkan dokumentasi
            known_limits = {
                "gemini-2.5-pro": 100,
                "gemini-2.5-flash": 250,
                "gemini-2.5-flash-lite": 1000,
                "gemini-2.0-flash": 200,
                "gemini-2.0-flash-lite": 200
            }
        
        predictions = {}
        current_time = datetime.now()
        
        for model_name, daily_limit in known_limits.items():
            if model_name in self.requests_per_model:
                used_requests = self.requests_per_model[model_name]
                remaining_requests = daily_limit - used_requests
                
                # Hitung rata-rata request per jam dalam session ini
                session_hours = (current_time - self.session_start_time).total_seconds() / 3600
                if session_hours > 0:
                    requests_per_hour = used_requests / session_hours
                    
                    # Prediksi kapan akan habis
                    if requests_per_hour > 0:
                        hours_to_limit = remaining_requests / requests_per_hour
                        estimated_limit_time = current_time + timedelta(hours=hours_to_limit)
                    else:
                        hours_to_limit = float('inf')
                        estimated_limit_time = None
                else:
                    requests_per_hour = 0
                    hours_to_limit = float('inf')
                    estimated_limit_time = None
                
                predictions[model_name] = {
                    "daily_limit": daily_limit,
                    "used_requests": used_requests,
                    "remaining_requests": remaining_requests,
                    "usage_percentage": (used_requests / daily_limit * 100),
                    "current_rate_per_hour": requests_per_hour,
                    "estimated_hours_to_limit": hours_to_limit if hours_to_limit != float('inf') else None,
                    "estimated_limit_time": estimated_limit_time.isoformat() if estimated_limit_time else None,
                    "status": "warning" if used_requests / daily_limit > 0.8 else "safe"
                }
        
        return predictions
    
    def generate_report(self, detailed: bool = True) -> str:
        """Generate formatted report"""
        stats = self.get_current_stats()
        
        # Handle potential errors in stats
        if isinstance(stats, dict) and "error" in stats:
            return f"❌ Error retrieving stats: {stats.get('error', 'Unknown error')}"
        
        # Format session duration
        session_duration = stats.get('session_duration', 0)
        duration_str = str(timedelta(seconds=int(session_duration)))
        
        # Calculate success rate
        total_requests = stats.get('total_requests', 0)
        successful_requests = stats.get('successful_requests', 0)
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate average response time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        report_lines = [
            "=" * 80,
            "🔍 REQUEST TRACKING REPORT",
            "=" * 80,
            "",
            f"📅 Session Duration: {duration_str}",
            f"📊 Total Requests: {total_requests}",
            f"✅ Success Rate: {success_rate:.1f}% ({successful_requests}/{total_requests})",
            f"❌ Failed Requests: {stats.get('failed_requests', 0)}",
            f"⚡ Avg Response Time: {avg_response_time:.2f}s",
            f"🚀 Request Rate: {stats.get('requests_per_minute', 0):.1f} req/min",
            f"🪙 Total Tokens: {stats.get('total_tokens', 0):,}",
            f"💰 Total Cost: ${stats.get('total_cost', 0):.6f}",
            "",
            "🔑 API KEY STATISTICS:",
            "-" * 40
        ]
        
        # Add API stats if available
        api_stats = stats.get('api_stats', {})
        if api_stats:
            for api_key, api_data in api_stats.items():
                total_req = api_data.get('total_requests', 0)
                success_req = api_data.get('successful_requests', 0)
                api_success_rate = (success_req / total_req * 100) if total_req > 0 else 0
                report_lines.append(f"API {api_key}: {total_req} requests ({api_success_rate:.1f}% success)")
        else:
            report_lines.append("No API key statistics available")
        
        report_lines.extend([
            "",
            "🤖 MODEL STATISTICS:",
            "-" * 40
        ])
        
        # Add model statistics if available
        if hasattr(self, 'requests_per_model') and self.requests_per_model:
            for model_name, count in self.requests_per_model.items():
                success_count = self.success_per_model.get(model_name, 0)
                model_success_rate = (success_count / count * 100) if count > 0 else 0
                report_lines.append(f"{model_name}: {count} requests ({model_success_rate:.1f}% success)")
        else:
            report_lines.append("No model statistics available")
        
        # Add recent requests if available and detailed view requested
        if detailed and hasattr(self, 'current_session_requests') and len(self.current_session_requests) > 0:
            report_lines.extend([
                "",
                "📝 RECENT REQUESTS (Last 10):",
                "-" * 40
            ])
            
            recent_requests = self.current_session_requests[-10:]
            for req in recent_requests:
                status = "✅" if req.success else "❌"
                report_lines.append(f"#{req.request_id:3d} {status} {req.model_name} (API#{req.api_key_index}) - {req.response_time:.2f}s")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def _save_session_stats(self):
        """Save current session statistics to file"""
        import time
        save_start_time = time.time()
        SAVE_TIMEOUT = 10  # 10 seconds timeout for file operations
        
        try:
            logging.info(f"🔄 Starting session stats save...")
            
            # Check timeout before expensive operations
            if time.time() - save_start_time > SAVE_TIMEOUT:
                logging.error(f"⏰ TIMEOUT: Session stats save exceeded {SAVE_TIMEOUT} seconds")
                return
            
            logging.info(f"📊 Generating stats data...")
            stats_data = {
                "session_info": {
                    "start_time": self.session_start_time.isoformat(),
                    "last_update": datetime.now().isoformat()
                },
                "current_stats": self.get_current_stats(),
                "recent_requests": [asdict(req) for req in self.current_session_requests[-100:]]  # Keep last 100
            }
            
            # Check timeout before file write
            if time.time() - save_start_time > SAVE_TIMEOUT:
                logging.error(f"⏰ TIMEOUT: Session stats save exceeded {SAVE_TIMEOUT} seconds before file write")
                return
            
            logging.info(f"💾 Writing stats to file: {self.stats_file}")
            with open(self.stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2, cls=CustomJSONEncoder)
            
            save_duration = time.time() - save_start_time
            logging.info(f"✅ Session stats saved successfully in {save_duration:.2f} seconds")
                
        except Exception as e:
            save_duration = time.time() - save_start_time
            logging.error(f"❌ Failed to save session stats after {save_duration:.2f}s: {e}")
            import traceback
            logging.error(f"   └─ Traceback: {traceback.format_exc()}")
    
    def _load_historical_stats(self):
        """Load historical statistics if available"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load session requests from historical data
                    if 'recent_requests' in data:
                        for req_data in data['recent_requests']:
                            metrics = RequestMetrics(**req_data)
                            self.current_session_requests.append(metrics)
                            
                            # Update counters
                            if metrics.success:
                                self.successful_requests += 1
                                self.success_per_api_key[metrics.api_key_index] += 1
                                self.success_per_model[metrics.model_name] += 1
                            else:
                                self.failed_requests += 1
                            
                            self.total_requests += 1
                            self.requests_per_api_key[metrics.api_key_index] += 1
                            self.requests_per_model[metrics.model_name] += 1
                            self.response_times.append(metrics.response_time)
                    
                    logging.info(f"Loaded {self.total_requests} requests from historical stats")
        except Exception as e:
            logging.warning(f"Could not load historical stats: {e}")
    
    def save_and_close(self):
        """Save final statistics before closing"""
        self._save_session_stats()
        logging.info(f"Final session stats saved to {self.stats_file}")

# Global instance
_request_tracker = None

def get_request_tracker() -> RequestTracker:
    """Get global request tracker instance"""
    global _request_tracker
    if _request_tracker is None:
        _request_tracker = RequestTracker()
    return _request_tracker

def log_request(api_key_index: int, 
               model_name: str, 
               success: bool, 
               response_time: float, 
               error_message: Optional[str] = None,
               batch_info: Optional[str] = None,
               tokens_used: Optional[int] = None) -> int:
    """
    Convenience function untuk logging request
    
    Returns:
        int: Request ID
    """
    tracker = get_request_tracker()
    request_id = tracker.record_request(
        api_key_index=api_key_index,
        model_name=model_name,
        success=success,
        response_time=response_time,
        error_message=error_message,
        batch_info=batch_info,
        tokens_used=tokens_used
    )
    
    # Log to standard logging system as well
    status = "SUCCESS" if success else "FAILED"
    logging.info(f"🔢 Request #{request_id:03d}: {status} | {model_name} | API#{api_key_index} | {response_time:.2f}s")
    
    if not success and error_message:
        logging.error(f"   └─ Error: {error_message}")
    
    return request_id

# CLI untuk testing dan reporting
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Request Tracker - Statistics and Monitoring")
    parser.add_argument("--report", action="store_true", help="Generate current session report")
    parser.add_argument("--detailed", action="store_true", help="Include detailed request list in report")
    parser.add_argument("--clear", action="store_true", help="Clear saved statistics")
    
    args = parser.parse_args()
    
    tracker = get_request_tracker()
    
    if args.clear:
        if os.path.exists(tracker.stats_file):
            os.remove(tracker.stats_file)
            print("✅ Statistics cleared.")
    
    if args.report:
        print(tracker.generate_report(detailed=args.detailed))
    else:
        print("Request Tracker initialized. Use --report to see statistics.")