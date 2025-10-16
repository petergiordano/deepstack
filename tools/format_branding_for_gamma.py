#!/usr/bin/env python3
"""
Format DeepStack Branding Output for Gamma.app

Converts branding JSON output into a color palette format compatible with Gamma.app's interface.

Usage:
    python3 tools/format_branding_for_gamma.py output/deepstack_branding-example.com.json
    python3 tools/format_branding_for_gamma.py output/deepstack_branding-example.com.json --output gamma_palette.txt
"""

import json
import argparse
import sys
from pathlib import Path
from collections import Counter
import re


def is_valid_hex(hex_color):
    """Check if string is a valid hex color."""
    if not hex_color:
        return False
    hex_color = hex_color.lstrip('#')
    if len(hex_color) not in [3, 6, 8]:
        return False
    try:
        int(hex_color, 16)
        return True
    except ValueError:
        return False


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    if not is_valid_hex(hex_color):
        return (0, 0, 0)
    hex_color = hex_color.lstrip('#')
    # Handle 3-digit hex
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def calculate_brightness(hex_color):
    """Calculate perceived brightness of a color (0-255)."""
    r, g, b = hex_to_rgb(hex_color)
    # Using perceived brightness formula
    return (0.299 * r + 0.587 * g + 0.114 * b)


def is_dark_color(hex_color):
    """Check if color is dark (brightness < 128)."""
    return calculate_brightness(hex_color) < 128


def is_neutral(hex_color):
    """Check if color is neutral (grayscale)."""
    r, g, b = hex_to_rgb(hex_color)
    # If RGB values are close to each other, it's neutral
    return max(r, g, b) - min(r, g, b) < 30


def categorize_colors(data_payload):
    """
    Categorize colors using intelligent classification from branding collector.
    Uses the color_classification and color_confidence_scores from the JSON.
    """

    # Get classification data
    color_classification = data_payload.get('color_classification', {})
    computed = data_payload.get('color_palette', {}).get('computed_colors', {})

    # Get classified accent colors
    classified_accents = color_classification.get('accents', [])
    classified_primary = color_classification.get('primary', [])

    # Primary accent: Use first primary if available, otherwise first accent
    if classified_primary:
        primary_accent = classified_primary[0].upper()
    elif classified_accents:
        primary_accent = classified_accents[0].upper()
    else:
        primary_accent = '#0000FF'  # Fallback blue

    # Secondary accents: Use remaining accents (up to 8 total)
    if classified_primary and classified_accents:
        # If we have a primary, use all accents for secondary
        secondary_accents = [c.upper() for c in classified_accents[:8]]
    elif classified_accents:
        # If no primary, use remaining accents (skip first which became primary)
        secondary_accents = [c.upper() for c in classified_accents[1:8]]
    else:
        secondary_accents = []

    # Pad with placeholders if needed to show 8 slots
    while len(secondary_accents) < 8:
        secondary_accents.append(None)

    # Extract text colors from computed styles
    heading_color = '#000000'
    body_color = '#272525'

    # Look for heading colors
    for selector in ['h1', 'h2', 'h3']:
        if selector in computed and 'color' in computed[selector]:
            heading_color = computed[selector]['color']
            break

    # Look for body color
    if 'body' in computed and 'color' in computed['body']:
        body_color = computed['body']['color']

    # Extract background colors
    card_bg = '#FFFFFF'
    page_bg = None

    if 'body' in computed and 'backgroundColor' in computed['body']:
        bg = computed['body']['backgroundColor']
        if bg and bg != 'rgba(0, 0, 0, 0)':
            page_bg = bg

    return {
        'primary_accent': primary_accent,
        'secondary_accents': secondary_accents,
        'heading_color': heading_color,
        'body_color': body_color,
        'card_background': card_bg,
        'page_background': page_bg
    }


def format_for_gamma(branding_json_path, output_path=None):
    """
    Read branding JSON and format it for Gamma.app.

    Args:
        branding_json_path: Path to the branding JSON file
        output_path: Optional path to save the formatted output

    Returns:
        Formatted string ready for Gamma.app
    """

    # Read the JSON file
    with open(branding_json_path, 'r') as f:
        data = json.load(f)

    # Get the first URL result
    if not data.get('url_analysis_results'):
        print("ERROR: No URL analysis results found in JSON")
        return None

    result = data['url_analysis_results'][0]

    if result['fetch_status'] != 'success':
        print(f"ERROR: Fetch failed for {result['url']}")
        return None

    url = result['url']
    page_title = result.get('page_title', 'Unknown')
    data_payload = result['data']
    color_data = data_payload['color_palette']

    # Categorize colors using classification data
    palette = categorize_colors(data_payload)

    # Format output
    output_lines = []
    output_lines.append("=" * 70)
    output_lines.append(f"GAMMA.APP COLOR PALETTE")
    output_lines.append("=" * 70)
    output_lines.append(f"Generated from: {url}")
    output_lines.append(f"Page Title: {page_title}")
    output_lines.append(f"Generated: {data['collection_metadata']['collection_timestamp_utc']}")
    output_lines.append("=" * 70)
    output_lines.append("")

    # Theme palette section
    output_lines.append("THEME PALETTE")
    output_lines.append("-" * 70)
    output_lines.append("")
    output_lines.append(f"Primary accent color:")
    output_lines.append(f"  {palette['primary_accent']}")
    output_lines.append("")

    output_lines.append(f"Secondary accent colors (optional):")
    for i, color in enumerate(palette['secondary_accents'], 1):
        if color:
            output_lines.append(f"  {i}. {color}")
        else:
            output_lines.append(f"  {i}. (empty)")
    output_lines.append("")

    # Text section
    output_lines.append("TEXT")
    output_lines.append("-" * 70)
    output_lines.append("")
    output_lines.append(f"Heading color:")
    output_lines.append(f"  {palette['heading_color']}")
    output_lines.append("")
    output_lines.append(f"Body color:")
    output_lines.append(f"  {palette['body_color']}")
    output_lines.append("")

    # Fonts section
    font_classification = data_payload.get('font_classification', {})
    font_confidence = data_payload.get('font_confidence_scores', {})

    if font_classification:
        output_lines.append("FONTS")
        output_lines.append("-" * 70)
        output_lines.append("")

        # Primary heading font
        heading_font = font_classification.get('primary_heading')
        if heading_font:
            output_lines.append(f"Heading font:")
            output_lines.append(f"  {heading_font}")
            # Add confidence info if available
            if heading_font in font_confidence:
                conf = font_confidence[heading_font]
                output_lines.append(f"  ({int(conf.get('confidence', 0) * 100)}% confidence - {conf.get('role', 'unknown')})")
        else:
            output_lines.append(f"Heading font:")
            output_lines.append(f"  (not detected)")
        output_lines.append("")

        # Body text font
        body_font = font_classification.get('body_text')
        if body_font:
            output_lines.append(f"Body font:")
            output_lines.append(f"  {body_font}")
            # Add confidence info if available
            if body_font in font_confidence:
                conf = font_confidence[body_font]
                output_lines.append(f"  ({int(conf.get('confidence', 0) * 100)}% confidence - {conf.get('role', 'unknown')})")
        else:
            output_lines.append(f"Body font:")
            output_lines.append(f"  (not detected)")
        output_lines.append("")

        # Accent/display fonts
        accent_fonts = font_classification.get('accent_display', [])
        if accent_fonts:
            output_lines.append(f"Accent/Display fonts:")
            for font in accent_fonts:
                output_lines.append(f"  • {font}")
            output_lines.append("")

        # Monospace/code font
        mono_font = font_classification.get('monospace_code')
        if mono_font:
            output_lines.append(f"Code/Monospace font:")
            output_lines.append(f"  {mono_font}")
            output_lines.append("")

    # Accessibility note
    output_lines.append("ACCESSIBILITY")
    output_lines.append("-" * 70)
    output_lines.append("☑ Adjust colors for contrast and accessibility (recommended)")
    output_lines.append("")

    # Background section
    output_lines.append("BACKGROUND")
    output_lines.append("-" * 70)
    output_lines.append("")
    output_lines.append(f"Card background color:")
    output_lines.append(f"  {palette['card_background']}")
    output_lines.append("")
    output_lines.append(f"Page background:")
    if palette['page_background']:
        output_lines.append(f"  {palette['page_background']}")
    else:
        output_lines.append(f"  None")
    output_lines.append("")

    # Additional brand colors (for reference)
    output_lines.append("=" * 70)
    output_lines.append("FULL BRAND COLOR PALETTE (from CSS variables)")
    output_lines.append("=" * 70)

    css_vars = color_data.get('css_custom_properties', {})
    if css_vars:
        # Group by color family
        output_lines.append("")
        for var_name, color_value in sorted(css_vars.items()):
            if is_valid_hex(color_value):
                output_lines.append(f"  {var_name}: {color_value.upper()}")

    output_lines.append("")
    output_lines.append("=" * 70)

    formatted_output = '\n'.join(output_lines)

    # Save to file if output path specified
    if output_path:
        with open(output_path, 'w') as f:
            f.write(formatted_output)
        print(f"Formatted palette saved to: {output_path}")

    return formatted_output


def main():
    parser = argparse.ArgumentParser(
        description="Format DeepStack Branding output for Gamma.app"
    )
    parser.add_argument(
        'json_file',
        help='Path to DeepStack branding JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (optional, prints to stdout if not specified)',
        default=None
    )

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.json_file).exists():
        print(f"ERROR: File not found: {args.json_file}")
        sys.exit(1)

    # Format the branding data
    formatted = format_for_gamma(args.json_file, args.output)

    if formatted:
        if not args.output:
            print(formatted)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
