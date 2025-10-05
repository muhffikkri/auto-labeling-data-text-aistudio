# src/core_logic/__main__.py

import sys

def main():
    print("Available tools in src.core_logic:")
    print("  python -m src.core_logic.check_tokens --dataset DATASET --column COLUMN")
    print("  python -m src.core_logic.list_models [--show-details] [--check-access]")
    print("")
    print("Or use the wrapper:")
    print("  python tools.py check-tokens --dataset DATASET --column COLUMN")
    print("  python tools.py list-models --show-details")

if __name__ == "__main__":
    main()