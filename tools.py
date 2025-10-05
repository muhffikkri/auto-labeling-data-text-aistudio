#!/usr/bin/env python3
"""
Tool wrapper untuk menjalankan utilitas analisis dari command line

Usage:
    python tools.py check-tokens --dataset my_data --column text --batch-size 300
    python tools.py list-models
    python tools.py list-models --show-details
    python tools.py list-models --generate-config
"""

import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tools.py check-tokens --dataset DATASET --column COLUMN [--batch-size SIZE]")
        print("  python tools.py list-models [--show-details] [--check-access] [--generate-config]")
        print("  python tools.py request-stats [--detailed] [--monitor] [--warnings] [--export]")
        print("  python tools.py sessions [--list] [--show SESSION_ID] [--summary] [--recent N]")
        print("")
        print("Examples:")
        print("  python tools.py check-tokens --dataset my_tweets --column tweet_text")
        print("  python tools.py list-models --show-details")
        print("  python tools.py request-stats --monitor")
        print("  python tools.py sessions --list")
        print("  python tools.py sessions --show 20251005_142030")
        print("  python tools.py sessions --recent 5")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == "check-tokens":
        subprocess.run([sys.executable, "-m", "src.core_logic.check_tokens"] + args)
    elif command == "list-models":
        subprocess.run([sys.executable, "-m", "src.core_logic.list_models"] + args)
    elif command == "request-stats":
        subprocess.run([sys.executable, "-m", "src.core_logic.request_stats"] + args)
    elif command == "sessions":
        subprocess.run([sys.executable, "-m", "src.core_logic.session_viewer"] + args)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: check-tokens, list-models, request-stats, sessions")
        sys.exit(1)

if __name__ == "__main__":
    main()