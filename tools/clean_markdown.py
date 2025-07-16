#!/usr/bin/env python3
"""
CLI script to clean escaped markdown syntax from Google Docs downloads.
"""

import sys
import argparse
from pathlib import Path
from markdown_cleaner import clean_escaped_markdown


def main():
    parser = argparse.ArgumentParser(
        description="Clean escaped markdown syntax from Google Docs downloads"
    )
    parser.add_argument(
        "input_file", 
        help="Input markdown file with escaped syntax"
    )
    parser.add_argument(
        "output_file", 
        nargs="?",
        help="Output file (defaults to input_file if not specified)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be changed without writing to file"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    output_path = Path(args.output_file) if args.output_file else input_path
    
    # Check if input file exists
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        return 1
    
    # Read input file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading '{input_path}': {e}", file=sys.stderr)
        return 1
    
    # Clean the content
    cleaned_content = clean_escaped_markdown(content)
    
    # Show changes if dry run
    if args.dry_run:
        if content == cleaned_content:
            print("No changes needed.")
        else:
            print("Changes that would be made:")
            print("=" * 50)
            print(cleaned_content)
            print("=" * 50)
        return 0
    
    # Write output file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        if content == cleaned_content:
            print(f"No changes needed in '{input_path}'")
        else:
            if output_path == input_path:
                print(f"Cleaned escaped markdown in '{input_path}'")
            else:
                print(f"Cleaned markdown written to '{output_path}'")
                
    except Exception as e:
        print(f"Error writing '{output_path}': {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())