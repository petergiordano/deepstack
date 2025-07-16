#!/bin/bash
"""
DeepStack Collector Shell Launcher

This shell script provides a convenient way to run the DeepStack Collector
from the root directory while the actual implementation is in src/

Output Files:
    - Single URL mode: output/deepstack_output-{domain}.json (e.g., output/deepstack_output-example.com.json)
    - Batch mode: output/deepstack_output.json

Usage:
    Single URL Mode:
        ./deepstack.sh -u https://example.com
        # Output: output/deepstack_output-example.com.json

        ./deepstack.sh -u https://www.google.com
        # Output: output/deepstack_output-google.com.json

        ./deepstack.sh -u https://subdomain.example.com:8080
        # Output: output/deepstack_output-subdomain.example.com_8080.json

    Batch Mode:
        ./deepstack.sh
        # Output: output/deepstack_output.json (reads from urls_to_analyze.txt)

    Alternative execution:
        bash deepstack.sh -u https://example.com
"""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script directory to ensure relative paths work correctly
cd "$SCRIPT_DIR"

# Execute the deepstack collector with all passed arguments
python3 src/deepstack_collector.py "$@"