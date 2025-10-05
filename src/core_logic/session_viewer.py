# src/core_logic/session_viewer.py

"""
Session Viewer Tool - Command line interface untuk melihat session logs

Usage:
    python -m src.core_logic.session_viewer --list
    python -m src.core_logic.session_viewer --show SESSION_ID
    python -m src.core_logic.session_viewer --summary
    python -m src.core_logic.session_viewer --recent 5
"""

import argparse
import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

def list_sessions() -> List[Dict[str, Any]]:
    """List semua session yang tersedia"""
    sessions_dir = "logs/sessions"
    if not os.path.exists(sessions_dir):
        return []
    
    sessions = []
    session_dirs = glob.glob(os.path.join(sessions_dir, "session_*"))
    
    for session_dir in session_dirs:
        session_id = os.path.basename(session_dir).replace("session_", "")
        summary_file = os.path.join(session_dir, "session_summary.json")
        
        session_info = {
            "session_id": session_id,
            "session_dir": session_dir,
            "has_summary": os.path.exists(summary_file)
        }
        
        if session_info["has_summary"]:
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                    session_info.update({
                        "dataset_name": summary["session_info"].get("dataset_name"),
                        "start_time": summary["session_info"].get("start_time"),
                        "end_time": summary["session_info"].get("end_time"),
                        "total_batches": summary["session_info"].get("total_batches", 0),
                        "success_rate": summary["session_info"].get("success_rate", 0),
                        "items_processed": summary["session_info"].get("items_processed", 0)
                    })
            except Exception as e:
                session_info["error"] = str(e)
        
        sessions.append(session_info)
    
    # Sort by session_id (timestamp) descending
    sessions.sort(key=lambda x: x["session_id"], reverse=True)
    return sessions

def show_session_summary():
    """Tampilkan ringkasan semua sessions"""
    sessions = list_sessions()
    
    if not sessions:
        print("🔍 Tidak ada session ditemukan di logs/sessions/")
        return
    
    print("="*80)
    print("📋 RINGKASAN SEMUA SESSIONS")
    print("="*80)
    
    total_sessions = len(sessions)
    completed_sessions = len([s for s in sessions if s.get("end_time")])
    total_items = sum(s.get("items_processed", 0) for s in sessions)
    avg_success_rate = sum(s.get("success_rate", 0) for s in sessions) / max(1, total_sessions)
    
    print(f"📊 Total Sessions: {total_sessions}")
    print(f"✅ Completed Sessions: {completed_sessions}")
    print(f"📝 Total Items Processed: {total_items:,}")
    print(f"🎯 Average Success Rate: {avg_success_rate:.2f}%")
    print()
    
    # Recent sessions table
    print("🕐 RECENT SESSIONS:")
    print("-"*80)
    print(f"{'Session ID':<15} {'Dataset':<20} {'Batches':<8} {'Success%':<9} {'Items':<8} {'Status':<10}")
    print("-"*80)
    
    for session in sessions[:10]:  # Show last 10
        dataset = session.get("dataset_name", "Unknown")[:18]
        batches = session.get("total_batches", 0)
        success_rate = session.get("success_rate", 0)
        items = session.get("items_processed", 0)
        status = "✅ Done" if session.get("end_time") else "🔄 Running"
        
        print(f"{session['session_id']:<15} {dataset:<20} {batches:<8} {success_rate:<8.1f}% {items:<8} {status:<10}")
    
    print("-"*80)

def show_session_details(session_id: str):
    """Tampilkan detail session tertentu"""
    session_dir = f"logs/sessions/session_{session_id}"
    
    if not os.path.exists(session_dir):
        print(f"❌ Session {session_id} tidak ditemukan!")
        return
    
    summary_file = os.path.join(session_dir, "session_summary.json")
    session_log = os.path.join(session_dir, f"session_{session_id}.log")
    
    print("="*80)
    print(f"📋 SESSION DETAILS: {session_id}")
    print("="*80)
    
    # Load and display summary
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        session_info = summary["session_info"]
        runtime_stats = summary.get("runtime_stats", {})
        batch_summary = summary.get("batch_summary", {})
        
        # Session information
        print("📊 SESSION INFORMATION:")
        print(f"   Dataset: {session_info.get('dataset_name', 'Unknown')}")
        print(f"   Batch Size: {session_info.get('batch_size', 'Unknown')}")
        
        if session_info.get('start_time'):
            start_time = datetime.fromtimestamp(session_info['start_time'])
            print(f"   Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if session_info.get('end_time'):
            end_time = datetime.fromtimestamp(session_info['end_time'])
            duration = session_info['end_time'] - session_info['start_time']
            print(f"   End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Duration: {duration:.2f}s ({duration/60:.1f}m)")
        else:
            print("   Status: 🔄 Running or Interrupted")
        
        print(f"   Session Directory: {session_dir}")
        
        # Processing statistics
        print("\n📈 PROCESSING STATISTICS:")
        print(f"   Total Items: {session_info.get('total_items', 0):,}")
        print(f"   Items Processed: {session_info.get('items_processed', 0):,}")
        print(f"   Items Failed: {session_info.get('items_failed', 0):,}")
        print(f"   Success Rate: {session_info.get('success_rate', 0):.2f}%")
        
        # Batch statistics  
        print("\n📦 BATCH STATISTICS:")
        print(f"   Total Batches: {session_info.get('total_batches', 0)}")
        print(f"   Successful Batches: {session_info.get('successful_batches', 0)}")
        print(f"   Failed Batches: {session_info.get('failed_batches', 0)}")
        print(f"   Batch Success Rate: {session_info.get('batch_success_rate', 0):.2f}%")
        
        # Models and API keys used
        if session_info.get('model_sequence_used'):
            print("\n🤖 MODELS USED:")
            for model in session_info['model_sequence_used']:
                print(f"   - {model}")
        
        if session_info.get('api_keys_used'):
            print("\n🔑 API KEYS USED:")
            for key_idx in session_info['api_keys_used']:
                print(f"   - API Key #{key_idx}")
        
        # Performance metrics
        if runtime_stats:
            print("\n⚡ PERFORMANCE METRICS:")
            if runtime_stats.get('average_batch_duration'):
                print(f"   Average Batch Time: {runtime_stats['average_batch_duration']:.2f}s")
            if runtime_stats.get('average_successful_batch_duration'):
                print(f"   Average Successful Batch Time: {runtime_stats['average_successful_batch_duration']:.2f}s")
            
            # Calculate throughput
            if session_info.get('total_duration') and session_info.get('items_processed'):
                items_per_hour = (session_info['items_processed'] / session_info['total_duration']) * 3600
                print(f"   Items per Hour: {items_per_hour:.0f}")
        
        # Recent batch results
        if batch_summary.get('batch_details'):
            print("\n📋 RECENT BATCH RESULTS:")
            print(f"   {'Batch ID':<15} {'Status':<7} {'Duration':<10} {'Items':<7} {'Labels'}")
            print("   " + "-"*65)
            
            for batch in batch_summary['batch_details'][-5:]:  # Last 5 batches
                batch_id = batch.get('batch_id', 'Unknown')[:13]
                status = "✅ OK" if batch.get('success') else "❌ FAIL"
                duration = f"{batch.get('duration', 0):.1f}s"
                items = f"{batch.get('items_processed', 0)}/{batch.get('items_processed', 0) + batch.get('items_failed', 0)}"
                
                # Label distribution summary
                label_dist = batch.get('label_distribution', {})
                if label_dist:
                    labels = " ".join([f"{k}:{v}" for k, v in list(label_dist.items())[:3]])
                else:
                    labels = "-"
                
                print(f"   {batch_id:<15} {status:<7} {duration:<10} {items:<7} {labels}")
    
    else:
        print("⚠️ Session summary tidak ditemukan")
    
    # Show log tail if available
    if os.path.exists(session_log):
        print("\n📜 RECENT LOG ENTRIES:")
        print("-"*60)
        try:
            with open(session_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Show last 10 lines
                for line in lines[-10:]:
                    print(f"   {line.rstrip()}")
        except Exception as e:
            print(f"   Error reading log: {e}")
    
    print("\n" + "="*80)

def list_sessions_table():
    """Tampilkan daftar sessions dalam format tabel"""
    sessions = list_sessions()
    
    if not sessions:
        print("🔍 Tidak ada session ditemukan di logs/sessions/")
        return
    
    print("="*80)
    print("📋 DAFTAR SESSIONS")
    print("="*80)
    print(f"{'Session ID':<15} {'Dataset':<20} {'Start Time':<19} {'Batches':<8} {'Success%':<9} {'Status'}")
    print("-"*80)
    
    for session in sessions:
        session_id = session['session_id']
        dataset = session.get('dataset_name', 'Unknown')[:18] 
        
        if session.get('start_time'):
            start_time = datetime.fromtimestamp(session['start_time']).strftime('%Y-%m-%d %H:%M:%S')
        else:
            start_time = 'Unknown'
        
        batches = session.get('total_batches', 0)
        success_rate = session.get('success_rate', 0)
        status = "✅ Completed" if session.get('end_time') else "🔄 Incomplete"
        
        print(f"{session_id:<15} {dataset:<20} {start_time:<19} {batches:<8} {success_rate:<8.1f}% {status}")
    
    print("-"*80)
    print(f"Total sessions: {len(sessions)}")

def show_recent_sessions(count: int = 5):
    """Tampilkan sessions terbaru"""
    sessions = list_sessions()
    
    if not sessions:
        print("🔍 Tidak ada session ditemukan")
        return
    
    recent_sessions = sessions[:count]
    
    print("="*60)
    print(f"🕐 {count} SESSIONS TERBARU")
    print("="*60)
    
    for i, session in enumerate(recent_sessions, 1):
        print(f"\n{i}. Session: {session['session_id']}")
        print(f"   Dataset: {session.get('dataset_name', 'Unknown')}")
        
        if session.get('start_time'):
            start_time = datetime.fromtimestamp(session['start_time'])
            print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"   Batches: {session.get('total_batches', 0)}")
        print(f"   Success Rate: {session.get('success_rate', 0):.1f}%")
        print(f"   Items Processed: {session.get('items_processed', 0):,}")
        print(f"   Status: {'✅ Completed' if session.get('end_time') else '🔄 Incomplete'}")

def main():
    parser = argparse.ArgumentParser(
        description="Session Viewer - Analyze labeling session logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.core_logic.session_viewer --list
  python -m src.core_logic.session_viewer --show 20251005_142030
  python -m src.core_logic.session_viewer --summary
  python -m src.core_logic.session_viewer --recent 3
        """
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available sessions'
    )
    
    parser.add_argument(
        '--show',
        type=str,
        metavar='SESSION_ID',
        help='Show detailed information for specific session'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary of all sessions'
    )
    
    parser.add_argument(
        '--recent',
        type=int,
        metavar='COUNT',
        default=5,
        help='Show N most recent sessions (default: 5)'
    )
    
    args = parser.parse_args()
    
    # Default action jika tidak ada argumen
    if not any([args.list, args.show, args.summary]):
        args.recent = args.recent or 5
    
    try:
        if args.list:
            list_sessions_table()
        elif args.show:
            show_session_details(args.show)
        elif args.summary:
            show_session_summary()
        elif args.recent is not None:
            show_recent_sessions(args.recent)
        else:
            show_recent_sessions(5)  # Default
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()