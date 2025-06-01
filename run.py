#!/usr/bin/env python3
"""
Convenient run script for PhotosSorter.

This script provides an easy way to run the PhotosSorter application
without needing to navigate to the src directory.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

try:
    from photos_sorter import main

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"Error importing PhotosSorter modules: {e}")
    print("Make sure you have installed the required dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error running PhotosSorter: {e}")
    sys.exit(1)
