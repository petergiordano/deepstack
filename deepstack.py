#!/usr/bin/env python3
"""
DeepStack Collector Launcher Script

This script provides a convenient way to run the DeepStack Collector from the root directory
while the actual implementation is located in the src/ directory.

Output Files:
    - Single URL mode: output/deepstack_output-{domain}.json (e.g., output/deepstack_output-example.com.json)
    - Batch mode: output/deepstack_output.json

Usage:
    Single URL Mode:
        python3 deepstack.py -u https://example.com
        # Output: output/deepstack_output-example.com.json

        python3 deepstack.py -u https://www.google.com
        # Output: output/deepstack_output-google.com.json

        python3 deepstack.py -u https://subdomain.example.com:8080
        # Output: output/deepstack_output-subdomain.example.com_8080.json

    Batch Mode:
        python3 deepstack.py
        # Output: output/deepstack_output.json (reads from urls_to_analyze.txt)
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