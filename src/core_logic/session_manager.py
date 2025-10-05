# src/core_logic/session_manager.py

import os
import json
import logging
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd


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
class BatchResult:
    """Data class untuk menyimpan hasil processing batch"""
    batch_id: str
    start_index: int
    end_index: int
    start_time: float
    end_time: float
    duration: float
    success: bool
    items_processed: int
    items_failed: int
    error_message: Optional[str] = None
    label_distribution: Optional[Dict[str, int]] = None
    model_used: Optional[str] = None
    api_key_index: Optional[int] = None

@dataclass
class SessionMetrics:
    """Data class untuk menyimpan metrics keseluruhan session"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    total_items: int = 0
    items_processed: int = 0
    items_failed: int = 0
    success_rate: float = 0.0
    total_batches: int = 0
    successful_batches: int = 0
    failed_batches: int = 0
    batch_success_rate: float = 0.0
    dataset_name: Optional[str] = None
    batch_size: Optional[int] = None
    model_sequence_used: Optional[List[str]] = None
    api_keys_used: Optional[List[int]] = None
    
class SessionManager:
    """
    Manager untuk mengelola session logging dan metrics tracking
    """
    
    def __init__(self, dataset_name: str, batch_size: int):
        """
        Inisialisasi session manager
        
        Args:
            dataset_name: Nama dataset yang diproses
            batch_size: Ukuran batch yang digunakan
        """
        # Generate session ID berdasarkan timestamp
        self.session_start = time.time()
        self.session_id = datetime.fromtimestamp(self.session_start).strftime("%Y%m%d_%H%M%S")
        
        # Session info
        self.dataset_name = dataset_name
        self.batch_size = batch_size
        
        # Create session directory structure
        self.base_log_dir = "logs"
        self.session_dir = os.path.join(self.base_log_dir, "sessions", f"session_{self.session_id}")
        self._create_session_directory()
        
        # Initialize session metrics
        self.metrics = SessionMetrics(
            session_id=self.session_id,
            start_time=self.session_start,
            dataset_name=dataset_name,
            batch_size=batch_size,
            model_sequence_used=[],
            api_keys_used=[]
        )
        
        # Batch results storage
        self.batch_results: List[BatchResult] = []
        
        # Setup session logger
        self.session_logger = self._setup_session_logger()
        
        # Log session start
        self._log_session_start()
    
    def _create_session_directory(self):
        """Membuat struktur direktori untuk session"""
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Subdirectories
        subdirs = ["batch_logs", "batch_results", "metrics", "errors"]
        for subdir in subdirs:
            os.makedirs(os.path.join(self.session_dir, subdir), exist_ok=True)
    
    def _setup_session_logger(self) -> logging.Logger:
        """Setup logger khusus untuk session ini"""
        logger = logging.getLogger(f"session_{self.session_id}")
        logger.setLevel(logging.INFO)
        
        # File handler untuk session log
        session_log_file = os.path.join(self.session_dir, f"session_{self.session_id}.log")
        file_handler = logging.FileHandler(session_log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler jika belum ada
        if not logger.handlers:
            logger.addHandler(file_handler)
        
        return logger
    
    def _log_session_start(self):
        """Log informasi start session"""
        self.session_logger.info("="*80)
        self.session_logger.info(f"🚀 SESSION START: {self.session_id}")
        self.session_logger.info("="*80)
        self.session_logger.info(f"📂 Dataset: {self.dataset_name}")
        self.session_logger.info(f"📦 Batch Size: {self.batch_size}")
        self.session_logger.info(f"🕐 Start Time: {datetime.fromtimestamp(self.session_start).strftime('%Y-%m-%d %H:%M:%S')}")
        self.session_logger.info(f"📁 Session Directory: {self.session_dir}")
        self.session_logger.info("-"*80)
    
    def start_batch(self, batch_id: str, start_index: int, end_index: int) -> Dict[str, Any]:
        """
        Memulai tracking untuk batch baru
        
        Args:
            batch_id: ID batch (contoh: "batch_1_50")
            start_index: Index mulai
            end_index: Index akhir
            
        Returns:
            Dict dengan informasi batch tracking
        """
        batch_start_time = time.time()
        
        batch_info = {
            'batch_id': batch_id,
            'start_index': start_index,
            'end_index': end_index,
            'start_time': batch_start_time,
            'items_count': end_index - start_index + 1
        }
        
        self.session_logger.info(f"📦 BATCH START: {batch_id}")
        self.session_logger.info(f"   └─ Range: {start_index} - {end_index} ({batch_info['items_count']} items)")
        self.session_logger.info(f"   └─ Start Time: {datetime.fromtimestamp(batch_start_time).strftime('%H:%M:%S')}")
        
        return batch_info
    
    def end_batch(
        self,
        batch_info: Dict[str, Any],
        success: bool,
        items_processed: int = 0,
        items_failed: int = 0,
        label_distribution: Optional[Dict[str, int]] = None,
        model_used: Optional[str] = None,
        api_key_index: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        Mengakhiri tracking untuk batch dan menyimpan hasil
        
        Args:
            batch_info: Info batch dari start_batch()
            success: Apakah batch berhasil diproses
            items_processed: Jumlah item yang berhasil diproses
            items_failed: Jumlah item yang gagal
            label_distribution: Distribusi label hasil
            model_used: Model yang digunakan
            api_key_index: Index API key yang digunakan  
            error_message: Pesan error jika ada
        """
        batch_end_time = time.time()
        duration = batch_end_time - batch_info['start_time']
        
        # Create batch result
        batch_result = BatchResult(
            batch_id=batch_info['batch_id'],
            start_index=batch_info['start_index'],
            end_index=batch_info['end_index'],
            start_time=batch_info['start_time'],
            end_time=batch_end_time,
            duration=duration,
            success=success,
            items_processed=items_processed,
            items_failed=items_failed,
            error_message=error_message,
            label_distribution=label_distribution,
            model_used=model_used,
            api_key_index=api_key_index
        )
        
        # Add to results
        self.batch_results.append(batch_result)
        
        # Update session metrics
        self._update_session_metrics(batch_result)
        
        # Log batch completion
        self._log_batch_completion(batch_result)
        
        # Save batch result to file
        self._save_batch_result(batch_result)
        
        # Update session summary
        self._save_session_summary()
    
    def _update_session_metrics(self, batch_result: BatchResult):
        """Update metrics session berdasarkan hasil batch"""
        self.metrics.total_batches += 1
        self.metrics.items_processed += batch_result.items_processed
        self.metrics.items_failed += batch_result.items_failed
        
        if batch_result.success:
            self.metrics.successful_batches += 1
        else:
            self.metrics.failed_batches += 1
        
        # Update model dan API key usage tracking
        if batch_result.model_used and batch_result.model_used not in self.metrics.model_sequence_used:
            self.metrics.model_sequence_used.append(batch_result.model_used)
        
        if batch_result.api_key_index and batch_result.api_key_index not in self.metrics.api_keys_used:
            self.metrics.api_keys_used.append(batch_result.api_key_index)
        
        # Calculate rates
        total_items = self.metrics.items_processed + self.metrics.items_failed
        if total_items > 0:
            self.metrics.success_rate = (self.metrics.items_processed / total_items) * 100
        
        if self.metrics.total_batches > 0:
            self.metrics.batch_success_rate = (self.metrics.successful_batches / self.metrics.total_batches) * 100
    
    def _log_batch_completion(self, batch_result: BatchResult):
        """Log informasi completion batch"""
        status = "✅ SUCCESS" if batch_result.success else "❌ FAILED"
        
        self.session_logger.info(f"📦 BATCH END: {batch_result.batch_id} - {status}")
        self.session_logger.info(f"   └─ Duration: {batch_result.duration:.2f}s")
        self.session_logger.info(f"   └─ Processed: {batch_result.items_processed}/{batch_result.items_processed + batch_result.items_failed}")
        
        if batch_result.label_distribution:
            self.session_logger.info(f"   └─ Labels: {batch_result.label_distribution}")
        
        if batch_result.model_used:
            self.session_logger.info(f"   └─ Model: {batch_result.model_used}")
        
        if batch_result.api_key_index:
            self.session_logger.info(f"   └─ API Key: #{batch_result.api_key_index}")
        
        if batch_result.error_message:
            self.session_logger.error(f"   └─ Error: {batch_result.error_message}")
        
        # Current session stats
        self.session_logger.info(f"   └─ Session Progress: {self.metrics.successful_batches}/{self.metrics.total_batches} batches ({self.metrics.batch_success_rate:.1f}%)")
    
    def _save_batch_result(self, batch_result: BatchResult):
        """Simpan hasil batch ke file JSON"""
        batch_file = os.path.join(
            self.session_dir, "batch_results", 
            f"{batch_result.batch_id}.json"
        )
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(batch_result), f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
    
    def _save_session_summary(self):
        """Simpan summary session ke file JSON"""
        summary_file = os.path.join(self.session_dir, "session_summary.json")
        
        # Calculate additional metrics
        if self.batch_results:
            total_duration = time.time() - self.session_start
            avg_batch_duration = sum(b.duration for b in self.batch_results) / len(self.batch_results)
            
            # Estimate remaining time jika masih berjalan
            successful_batches = len([b for b in self.batch_results if b.success])
            if successful_batches > 0:
                avg_successful_duration = sum(b.duration for b in self.batch_results if b.success) / successful_batches
            else:
                avg_successful_duration = 0
        else:
            total_duration = 0
            avg_batch_duration = 0
            avg_successful_duration = 0
        
        summary = {
            "session_info": asdict(self.metrics),
            "runtime_stats": {
                "total_session_duration": total_duration,
                "average_batch_duration": avg_batch_duration,
                "average_successful_batch_duration": avg_successful_duration,
                "estimated_completion_time": None  # Will be calculated by caller if needed
            },
            "batch_summary": {
                "total_batches": len(self.batch_results),
                "successful_batches": len([b for b in self.batch_results if b.success]),
                "failed_batches": len([b for b in self.batch_results if not b.success]),
                "batch_details": [asdict(b) for b in self.batch_results[-10:]]  # Last 10 batches
            }
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
    
    def end_session(self, total_items: int):
        """
        Mengakhiri session dan generate final report
        
        Args:
            total_items: Total item yang seharusnya diproses
        """
        self.metrics.end_time = time.time()
        self.metrics.total_duration = self.metrics.end_time - self.metrics.start_time
        self.metrics.total_items = total_items
        
        # Final logging
        self.session_logger.info("-"*80)
        self.session_logger.info("🏁 SESSION COMPLETED")
        self.session_logger.info("-"*80)
        self._log_final_summary()
        self.session_logger.info("="*80)
        
        # Save final summary
        self._save_session_summary()
        
        # Generate session report
        self._generate_session_report()
    
    def _log_final_summary(self):
        """Log final summary statistics"""
        self.session_logger.info(f"📊 FINAL STATISTICS:")
        self.session_logger.info(f"   └─ Total Duration: {self.metrics.total_duration:.2f}s ({self.metrics.total_duration/60:.1f}m)")
        self.session_logger.info(f"   └─ Total Items: {self.metrics.total_items}")
        self.session_logger.info(f"   └─ Items Processed: {self.metrics.items_processed}")
        self.session_logger.info(f"   └─ Items Failed: {self.metrics.items_failed}")
        self.session_logger.info(f"   └─ Success Rate: {self.metrics.success_rate:.2f}%")
        self.session_logger.info(f"   └─ Total Batches: {self.metrics.total_batches}")
        self.session_logger.info(f"   └─ Successful Batches: {self.metrics.successful_batches}")
        self.session_logger.info(f"   └─ Batch Success Rate: {self.metrics.batch_success_rate:.2f}%")
        
        if self.metrics.model_sequence_used:
            self.session_logger.info(f"   └─ Models Used: {', '.join(self.metrics.model_sequence_used)}")
        
        if self.metrics.api_keys_used:
            self.session_logger.info(f"   └─ API Keys Used: {', '.join(map(str, self.metrics.api_keys_used))}")
        
        # Performance metrics
        if self.metrics.total_batches > 0:
            avg_batch_time = self.metrics.total_duration / self.metrics.total_batches
            avg_item_time = self.metrics.total_duration / max(1, self.metrics.items_processed)
            self.session_logger.info(f"   └─ Avg Batch Time: {avg_batch_time:.2f}s")
            self.session_logger.info(f"   └─ Avg Item Time: {avg_item_time:.2f}s")
    
    def _generate_session_report(self):
        """Generate comprehensive session report"""
        report_file = os.path.join(self.session_dir, "SESSION_REPORT.md")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Session Report: {self.session_id}\n\n")
            f.write(f"## Session Information\n")
            f.write(f"- **Session ID**: {self.session_id}\n")
            f.write(f"- **Dataset**: {self.dataset_name}\n")
            f.write(f"- **Batch Size**: {self.batch_size}\n")
            f.write(f"- **Start Time**: {datetime.fromtimestamp(self.metrics.start_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            if self.metrics.end_time:
                f.write(f"- **End Time**: {datetime.fromtimestamp(self.metrics.end_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- **Total Duration**: {self.metrics.total_duration:.2f}s ({self.metrics.total_duration/60:.1f}m)\n")
            
            f.write(f"\n## Processing Statistics\n")
            f.write(f"- **Total Items**: {self.metrics.total_items}\n")
            f.write(f"- **Items Processed**: {self.metrics.items_processed}\n")
            f.write(f"- **Items Failed**: {self.metrics.items_failed}\n")
            f.write(f"- **Success Rate**: {self.metrics.success_rate:.2f}%\n")
            
            f.write(f"\n## Batch Statistics\n")
            f.write(f"- **Total Batches**: {self.metrics.total_batches}\n")
            f.write(f"- **Successful Batches**: {self.metrics.successful_batches}\n")
            f.write(f"- **Failed Batches**: {self.metrics.failed_batches}\n")
            f.write(f"- **Batch Success Rate**: {self.metrics.batch_success_rate:.2f}%\n")
            
            if self.metrics.model_sequence_used:
                f.write(f"\n## Models Used\n")
                for model in self.metrics.model_sequence_used:
                    f.write(f"- {model}\n")
            
            if self.metrics.api_keys_used:
                f.write(f"\n## API Keys Used\n")
                for key_idx in self.metrics.api_keys_used:
                    f.write(f"- API Key #{key_idx}\n")
            
            # Performance section
            if self.metrics.total_batches > 0 and self.metrics.total_duration:
                avg_batch_time = self.metrics.total_duration / self.metrics.total_batches
                avg_item_time = self.metrics.total_duration / max(1, self.metrics.items_processed)
                
                f.write(f"\n## Performance Metrics\n")
                f.write(f"- **Average Batch Time**: {avg_batch_time:.2f}s\n")
                f.write(f"- **Average Item Processing Time**: {avg_item_time:.2f}s\n")
                f.write(f"- **Items per Hour**: {(self.metrics.items_processed / self.metrics.total_duration) * 3600:.0f}\n")
            
            # Recent batches
            if self.batch_results:
                f.write(f"\n## Recent Batch Results\n")
                for batch in self.batch_results[-5:]:  # Last 5 batches
                    status = "✅" if batch.success else "❌"
                    f.write(f"- **{batch.batch_id}** {status} - {batch.duration:.2f}s - {batch.items_processed}/{batch.items_processed + batch.items_failed} items\n")
    
    def get_current_stats(self) -> Dict[str, Any]:
        """
        Mendapatkan statistik session saat ini
        
        Returns:
            Dict dengan statistik terkini
        """
        current_duration = time.time() - self.session_start
        
        return {
            "session_id": self.session_id,
            "session_dir": self.session_dir,
            "current_duration": current_duration,
            "total_batches": self.metrics.total_batches,
            "successful_batches": self.metrics.successful_batches,
            "failed_batches": self.metrics.failed_batches,
            "items_processed": self.metrics.items_processed,
            "items_failed": self.metrics.items_failed,
            "success_rate": self.metrics.success_rate,
            "batch_success_rate": self.metrics.batch_success_rate,
            "models_used": self.metrics.model_sequence_used,
            "api_keys_used": self.metrics.api_keys_used
        }


# Global session manager instance
_current_session: Optional[SessionManager] = None

def get_current_session() -> Optional[SessionManager]:
    """Get current active session"""
    return _current_session

def start_session(dataset_name: str, batch_size: int) -> SessionManager:
    """
    Start new labeling session
    
    Args:
        dataset_name: Nama dataset
        batch_size: Ukuran batch
        
    Returns:
        SessionManager instance
    """
    global _current_session
    _current_session = SessionManager(dataset_name, batch_size)
    return _current_session

def end_current_session(total_items: int):
    """End current session jika ada"""
    global _current_session
    if _current_session:
        _current_session.end_session(total_items)
        _current_session = None