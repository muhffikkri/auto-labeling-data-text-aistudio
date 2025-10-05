#!/usr/bin/env python3
"""
request_stats.py - Request Statistics Viewer Tool

Tool command-line untuk melihat statistik request yang telah tercatat
dalam sistem auto-labeling dengan tracking detail.

Usage:
    python -m src.core_logic.request_stats
    python -m src.core_logic.request_stats --detailed
    python -m src.core_logic.request_stats --monitor

Author: Auto-generated for auto-labeling-data-text-aistudio project
Date: October 2025
"""

import argparse
import time
import os
import sys
from datetime import datetime

# Add parent directory to path untuk import lokal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .request_tracker import get_request_tracker
except ImportError:
    from src.core_logic.request_tracker import get_request_tracker


def display_live_stats(refresh_interval: int = 5):
    """Display live updating statistics"""
    try:
        while True:
            # Clear screen (Windows dan Unix compatible)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            tracker = get_request_tracker()
            report = tracker.generate_report(detailed=True)
            
            print(report)
            print(f"\n🔄 Live monitoring (refresh every {refresh_interval}s) - Press Ctrl+C to exit")
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n👋 Live monitoring stopped.")


def display_quota_warnings():
    """Display quota warnings and predictions"""
    tracker = get_request_tracker()
    predictions = tracker.get_quota_predictions()
    
    warnings = []
    for model, pred in predictions.items():
        if pred['used_requests'] > 0:
            if pred['status'] == 'warning':
                warnings.append(f"⚠️  {model}: {pred['usage_percentage']:.1f}% used ({pred['used_requests']}/{pred['daily_limit']})")
                if pred['estimated_hours_to_limit'] and pred['estimated_hours_to_limit'] < 24:
                    warnings.append(f"   └─ 🚨 Will hit limit in ~{pred['estimated_hours_to_limit']:.1f} hours!")
    
    if warnings:
        print("🚨 QUOTA WARNINGS:")
        print("-" * 40)
        for warning in warnings:
            print(warning)
        print()
    else:
        print("✅ No quota warnings - all models within safe limits.\n")


def display_performance_summary():
    """Display performance metrics summary"""
    tracker = get_request_tracker()
    stats = tracker.get_current_stats()
    
    print("⚡ PERFORMANCE SUMMARY:")
    print("-" * 40)
    print(f"📊 Success Rate: {stats['request_counts']['success_rate']:.1f}%")
    print(f"⏱️  Avg Response Time: {stats['performance']['avg_response_time']:.2f}s")
    print(f"🚀 Request Rate: {stats['performance']['requests_per_minute']:.1f} req/min")
    print(f"⏳ Total Session Time: {stats['session_info']['duration_formatted']}")
    print()


def export_stats_to_file(filename: str = None):
    """Export statistics to file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"request_stats_export_{timestamp}.txt"
    
    tracker = get_request_tracker()
    report = tracker.generate_report(detailed=True)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ Statistics exported to: {filename}")
    except Exception as e:
        print(f"❌ Failed to export statistics: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Request Statistics Viewer for Auto-Labeling System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.core_logic.request_stats              # Show basic stats
  python -m src.core_logic.request_stats --detailed   # Show detailed stats
  python -m src.core_logic.request_stats --monitor    # Live monitoring
  python -m src.core_logic.request_stats --warnings   # Show quota warnings only
  python -m src.core_logic.request_stats --export     # Export to file
        """
    )
    
    parser.add_argument(
        "--detailed", "-d", 
        action="store_true", 
        help="Show detailed statistics including recent requests"
    )
    
    parser.add_argument(
        "--monitor", "-m", 
        action="store_true", 
        help="Live monitoring mode with auto-refresh"
    )
    
    parser.add_argument(
        "--refresh", "-r", 
        type=int, 
        default=5, 
        help="Refresh interval for live monitoring (default: 5 seconds)"
    )
    
    parser.add_argument(
        "--warnings", "-w", 
        action="store_true", 
        help="Show only quota warnings and predictions"
    )
    
    parser.add_argument(
        "--performance", "-p", 
        action="store_true", 
        help="Show only performance metrics summary"
    )
    
    parser.add_argument(
        "--export", "-e", 
        nargs="?", 
        const="auto", 
        help="Export statistics to file (optional filename)"
    )
    
    args = parser.parse_args()
    
    # Handle live monitoring mode
    if args.monitor:
        print("🔄 Starting live monitoring mode...")
        print("Press Ctrl+C to exit")
        time.sleep(1)
        display_live_stats(args.refresh)
        return
    
    # Handle export mode
    if args.export:
        filename = args.export if args.export != "auto" else None
        export_stats_to_file(filename)
        return
    
    # Show header
    print("🔍 REQUEST STATISTICS VIEWER")
    print("=" * 50)
    print()
    
    # Handle warnings only mode
    if args.warnings:
        display_quota_warnings()
        return
    
    # Handle performance only mode
    if args.performance:
        display_performance_summary()
        return
    
    # Default: show comprehensive report
    try:
        tracker = get_request_tracker()
        
        # Check if there are any recorded requests
        stats = tracker.get_current_stats()
        if stats['request_counts']['total_requests'] == 0:
            print("📭 No requests recorded yet.")
            print("💡 Start using the auto-labeling system to see statistics here.")
            return
        
        # Show quota warnings first
        display_quota_warnings()
        
        # Show performance summary
        display_performance_summary()
        
        # Show full report
        report = tracker.generate_report(detailed=args.detailed)
        print(report)
        
        # Show helpful tips
        print("\n💡 Tips:")
        print("  • Use --monitor for live updates")
        print("  • Use --warnings to check quota status")
        print("  • Use --export to save statistics to file")
        
    except Exception as e:
        print(f"❌ Error generating statistics: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()