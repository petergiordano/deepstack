#!/bin/bash
"""
DeepStack Collector Shell Launcher

This shell script provides a convenient way to run the DeepStack Collector
from the root directory while the actual implementation is in src/

Usage:
    ./deepstack.sh -u https://example.com
    ./deepstack.sh  # For batch analysis
    bash deepstack.sh -u https://example.com
"""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script directory to ensure relative paths work correctly
cd "$SCRIPT_DIR"

# Execute the deepstack collector with all passed arguments
python3 src/deepstack_collector.py "$@"