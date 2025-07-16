#!/usr/bin/env python3
"""
DeepStack Collector Launcher Script

This script provides a convenient way to run the DeepStack Collector from the root directory
while the actual implementation is located in the src/ directory.

Usage:
    python3 deepstack.py -u https://example.com
    python3 deepstack.py  # For batch analysis
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Change working directory to maintain relative path compatibility
original_cwd = os.getcwd()
os.chdir(Path(__file__).parent)

try:
    # Import and run the main deepstack collector
    from deepstack_collector import main
    
    if __name__ == "__main__":
        main()
finally:
    # Restore original working directory
    os.chdir(original_cwd)