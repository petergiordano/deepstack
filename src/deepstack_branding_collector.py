"""
DeepStack Branding Collector - Website Brand Identity Analysis Tool

Analyzes websites for brand identity and visual design elements including:
- Color palettes (CSS variables, computed colors, dominant colors)
- Typography (font families, web font services, custom fonts)
- Visual assets (logos, favicons, Open Graph images)
- Design patterns (button styles, spacing, borders)

Output Files:
    - Single URL mode (-u): output/deepstack_branding-{domain}.json
    - Batch mode: output/deepstack_branding.json

Usage:
    Single URL Mode:
        python3 deepstack_branding_collector.py -u https://example.com
        # Output: output/deepstack_branding-example.com.json

    Batch Mode:
        python3 deepstack_branding_collector.py
        # Output: output/deepstack_branding.json (reads from urls_to_analyze.txt)
"""

from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timezone
import random
import argparse
from urllib.parse import urlparse
import os


# -----------------------------------------------------------------------------
# --- CONFIGURATION & SIGNATURES ---
# -----------------------------------------------------------------------------

# --- Font Service Signatures Definition ---
FONT_SERVICE_SIGNATURES = {
    "GoogleFonts": [
        r"fonts\.googleapis\.com",
        r"fonts\.gstatic\.com"
    ],
    "AdobeFonts": [
        r"use\.typekit\.net",
        r"typekit\.com",
        r"use\.edgefonts\.net"
    ],
    "FontAwesome": [
        r"fontawesome\.com",
        r"pro\.fontawesome\.com",
        r"kit\.fontawesome\.com"
    ],
    "Fonts.com": [
        r"fast\.fonts\.net"
    ],
    "Hoefler&Co": [
        r"cloud\.typography\.com"
    ],
    "MyFonts": [
        r"hello\.myfonts\.net"
    ],
    "CustomWebFonts": [
        r"\.woff2?(\?|$)",
        r"\.ttf(\?|$)",
        r"\.otf(\?|$)",
        r"\.eot(\?|$)"
    ]
}

# --- URLs to Analyze ---
URL_INPUT_FILE = "urls_to_analyze.txt"


def load_urls_from_file(filename):
    """Loads URLs from a specified file, one URL per line."""
    urls = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith("#"):
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    urls.append(url)
        if not urls:
            print(f"WARNING: No URLs found in {filename}.")
        else:
            print(f"Loaded {len(urls)} URL(s) from {filename}.")
    except FileNotFoundError:
        print(f"ERROR: URL input file '{filename}' not found.")
        with open(filename, 'w') as f:
            f.write("# Add URLs here, one per line (e.g., https://www.example.com)\n")
        print(f"An empty '{filename}' has been created.")
    except Exception as e:
        print(f"ERROR: Could not read URLs from '{filename}': {e}")
    return urls


# -----------------------------------------------------------------------------
# --- HELPER FUNCTIONS ---
# -----------------------------------------------------------------------------

def extract_color_from_rgb(rgb_string):
    """Convert RGB/RGBA string to hex color."""
    if not rgb_string or rgb_string == 'transparent':
        return None

    # Match rgb(r, g, b) or rgba(r, g, b, a)
    match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)', rgb_string)
    if match:
        r, g, b = match.groups()
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    return rgb_string


def is_color_value(value):
    """Check if a string value represents a color."""
    if not value or not isinstance(value, str):
        return False

    value = value.strip().lower()

    # Check for hex colors
    if re.match(r'^#[0-9a-f]{3,8}$', value):
        return True

    # Check for rgb/rgba
    if value.startswith(('rgb(', 'rgba(')):
        return True

    # Check for hsl/hsla
    if value.startswith(('hsl(', 'hsla(')):
        return True

    # Check for named colors (basic check)
    named_colors = ['red', 'blue', 'green', 'yellow', 'black', 'white',
                    'gray', 'grey', 'purple', 'orange', 'pink', 'brown']
    if value in named_colors:
        return True

    return False


# -----------------------------------------------------------------------------
# --- CLASSIFICATION FUNCTIONS ---
# -----------------------------------------------------------------------------

def classify_colors(color_palette, computed_colors_dict):
    """
    Classify colors into primary, accent, neutral, and utility categories.

    Args:
        color_palette: Dict containing css_custom_properties, primary_colors, color_frequency
        computed_colors_dict: Dict of computed colors from elements

    Returns:
        Dict with color_classification and confidence_scores
    """

    classification = {
        "primary": [],
        "accents": [],
        "neutrals": [],
        "utility": {
            "success": None,
            "error": None,
            "warning": None,
            "info": None
        }
    }

    confidence_scores = {}

    css_vars = color_palette.get('css_custom_properties', {})
    frequency = color_palette.get('color_frequency', {})

    # Analyze CSS variable names for semantic meaning
    primary_patterns = [r'primary', r'brand', r'main', r'hero']
    accent_patterns = [r'accent', r'secondary', r'highlight', r'alt']
    neutral_patterns = [r'gray', r'grey', r'black', r'white', r'neutral']
    # More specific utility patterns to avoid false matches with color names
    success_patterns = [r'success', r'positive']
    error_patterns = [r'error', r'danger', r'negative']
    warning_patterns = [r'warning', r'caution', r'alert']
    info_patterns = [r'info', r'notice']

    # Color name patterns - these are accents unless matched to utility patterns first
    color_name_patterns = [r'color-red', r'color-orange', r'color-yellow', r'color-green',
                          r'color-blue', r'color-purple', r'color-pink', r'color-teal',
                          r'color-magenta', r'color-cyan']

    # Track colors we've already classified
    classified_colors = set()

    # Pass 1: Classify by CSS variable names (highest confidence)
    for var_name, color_value in css_vars.items():
        var_lower = var_name.lower()
        confidence = 0.0
        role = None
        evidence = [f"CSS variable name: {var_name}"]

        # Check for primary
        if any(re.search(pattern, var_lower) for pattern in primary_patterns):
            role = "primary"
            confidence = 0.95
            if color_value not in classified_colors:
                classification["primary"].append(color_value)
                classified_colors.add(color_value)

        # Check for accent
        elif any(re.search(pattern, var_lower) for pattern in accent_patterns):
            role = "accent"
            confidence = 0.90
            if color_value not in classified_colors:
                classification["accents"].append(color_value)
                classified_colors.add(color_value)

        # Check for neutrals
        elif any(re.search(pattern, var_lower) for pattern in neutral_patterns):
            role = "neutral"
            confidence = 0.95
            if color_value not in classified_colors:
                classification["neutrals"].append(color_value)
                classified_colors.add(color_value)

        # Check for utility colors
        elif any(re.search(pattern, var_lower) for pattern in success_patterns):
            classification["utility"]["success"] = color_value
            confidence = 0.90
            role = "utility_success"
            classified_colors.add(color_value)

        elif any(re.search(pattern, var_lower) for pattern in error_patterns):
            classification["utility"]["error"] = color_value
            confidence = 0.90
            role = "utility_error"
            classified_colors.add(color_value)

        elif any(re.search(pattern, var_lower) for pattern in warning_patterns):
            classification["utility"]["warning"] = color_value
            confidence = 0.90
            role = "utility_warning"
            classified_colors.add(color_value)

        elif any(re.search(pattern, var_lower) for pattern in info_patterns):
            classification["utility"]["info"] = color_value
            confidence = 0.85
            role = "utility_info"
            classified_colors.add(color_value)

        # Check for color name patterns (e.g., --color-blue, --color-orange)
        # These are accents unless already classified as utility
        elif any(re.search(pattern, var_lower) for pattern in color_name_patterns):
            # Only add base color names, not light/dark/opacity variations
            # Exclude: -light, -dark, -lighter, -darker, -5, -10, -15, etc.
            if not any(modifier in var_lower for modifier in ['-light', '-dark', '-lighter', '-darker']) \
               and not re.search(r'-\d+$', var_lower):
                role = "accent"
                confidence = 0.85
                evidence.append("Named color variable")
                if color_value not in classified_colors:
                    classification["accents"].append(color_value)
                    classified_colors.add(color_value)

        # Record confidence if classified
        if role and color_value not in confidence_scores:
            confidence_scores[color_value] = {
                "role": role,
                "confidence": confidence,
                "evidence": evidence
            }

    # Pass 2: Analyze frequency and element hierarchy
    for selector, styles in computed_colors_dict.items():
        for prop, color_value in styles.items():
            if color_value in classified_colors:
                continue  # Already classified

            evidence = [f"Found in {selector}.{prop}"]
            confidence = 0.5
            role = None

            # Colors in important elements with high frequency = primary
            important_selectors = ['h1', 'h2', 'button', '[class*="primary"]', '.hero']
            if selector in important_selectors:
                freq_count = frequency.get(color_value, 0)
                if freq_count >= 5:  # Used 5+ times
                    evidence.append(f"High frequency: {freq_count} uses")
                    evidence.append(f"Used in important element: {selector}")
                    confidence = 0.75
                    role = "primary"
                    if color_value not in classification["primary"]:
                        classification["primary"].append(color_value)
                        classified_colors.add(color_value)

            # Colors in secondary/accent elements
            accent_selectors = ['[class*="secondary"]', 'a']
            if selector in accent_selectors and not role:
                freq_count = frequency.get(color_value, 0)
                if 2 <= freq_count < 10:  # Used moderately
                    evidence.append(f"Moderate frequency: {freq_count} uses")
                    evidence.append(f"Used in accent element: {selector}")
                    confidence = 0.65
                    role = "accent"
                    if color_value not in classification["accents"]:
                        classification["accents"].append(color_value)
                        classified_colors.add(color_value)

            # Record confidence if classified
            if role and color_value not in confidence_scores:
                confidence_scores[color_value] = {
                    "role": role,
                    "confidence": confidence,
                    "evidence": evidence
                }

    # Limit to reasonable numbers
    classification["primary"] = classification["primary"][:2]  # Max 2 primary colors
    classification["accents"] = classification["accents"][:8]  # Max 8 accents
    classification["neutrals"] = classification["neutrals"][:5]  # Max 5 neutrals

    return {
        "color_classification": classification,
        "confidence_scores": confidence_scores
    }


def classify_fonts(typography, typography_data):
    """
    Classify fonts into primary heading, body, accent, and monospace categories.

    Args:
        typography: Dict containing font service info and typeface hierarchy
        typography_data: Dict of computed typography from elements

    Returns:
        Dict with font_classification and confidence_scores
    """

    classification = {
        "primary_heading": None,
        "body_text": None,
        "accent_display": [],
        "monospace_code": None
    }

    confidence_scores = {}

    typeface_hierarchy = typography.get('typeface_hierarchy', {})

    # Track fonts we've classified
    classified_fonts = set()

    # Analyze font usage by element type
    for selector, styles in typography_data.items():
        font_family = styles.get('fontFamily', '')
        if not font_family or font_family in classified_fonts:
            continue

        # Clean up font family string (remove quotes, fallbacks)
        font_clean = font_family.split(',')[0].strip().strip('"').strip("'")

        evidence = [f"Used in: {selector}"]
        confidence = 0.0
        role = None

        # Primary heading font (h1, h2, h3)
        if selector in ['h1', 'h2', 'h3'] and not classification["primary_heading"]:
            classification["primary_heading"] = font_clean
            confidence = 0.90
            role = "primary_heading"
            evidence.append("Used in primary headings")
            classified_fonts.add(font_clean)

        # Body text font
        elif selector in ['body', 'p'] and not classification["body_text"]:
            classification["body_text"] = font_clean
            confidence = 0.95
            role = "body_text"
            evidence.append("Used in body text")
            classified_fonts.add(font_clean)

        # Monospace/code font
        elif 'mono' in font_family.lower() or 'code' in font_family.lower():
            classification["monospace_code"] = font_clean
            confidence = 0.90
            role = "monospace"
            evidence.append("Monospace font family detected")
            classified_fonts.add(font_clean)

        # Accent/display fonts (used sparingly, in special elements)
        elif selector in ['button', '.btn', 'nav', 'strong'] and font_clean not in classified_fonts:
            if font_clean not in [classification["primary_heading"], classification["body_text"]]:
                classification["accent_display"].append(font_clean)
                confidence = 0.70
                role = "accent"
                evidence.append(f"Used in special element: {selector}")
                classified_fonts.add(font_clean)

        # Record confidence
        if role and font_clean not in confidence_scores:
            confidence_scores[font_clean] = {
                "role": role,
                "confidence": confidence,
                "evidence": evidence
            }

    # Limit accent fonts
    classification["accent_display"] = classification["accent_display"][:3]

    # Add usage information from typeface hierarchy
    for font_family, usage_info in typeface_hierarchy.items():
        font_clean = font_family.split(',')[0].strip().strip('"').strip("'")
        if font_clean in confidence_scores:
            confidence_scores[font_clean]["used_in_elements"] = usage_info.get('used_in', [])
            confidence_scores[font_clean]["sample_size"] = usage_info.get('sample_size')

    return {
        "font_classification": classification,
        "confidence_scores": confidence_scores
    }


# -----------------------------------------------------------------------------
# --- MAIN FUNCTION ---
# -----------------------------------------------------------------------------

def main():
    """Main execution function for branding analysis."""

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="DeepStack Branding Collector: Analyze website brand identity."
    )
    parser.add_argument(
        "-u", "--url",
        help="A single URL to analyze. If provided, urls_to_analyze.txt will be ignored."
    )
    args = parser.parse_args()

    urls_to_process = []

    if args.url:
        single_url = args.url
        if not single_url.startswith(('http://', 'https://')):
            single_url = 'https://' + single_url
        urls_to_process = [single_url]
        print(f"INFO: Analyzing single URL: {single_url}")
    else:
        urls_to_process = load_urls_from_file(URL_INPUT_FILE)

    if not urls_to_process:
        print("INFO: No URLs to analyze. Exiting.")
        return

    print("DeepStack Branding Collector starting...")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
            ignore_https_errors=True
        )
        print("Browser launched.")

        collection_start_time_utc = datetime.now(timezone.utc)
        processed_urls_results_list = []
        successful_fetches = 0
        failed_fetches = 0

        for current_url in urls_to_process:
            time.sleep(random.uniform(2, 5))
            print(f"\nAttempting to navigate to: {current_url}")

            requests_log = []
            page = None

            try:
                page = context.new_page()
                page.on("request", lambda request: requests_log.append(request.url))

                print(f"  Navigating to {current_url}...")
                page.goto(current_url, wait_until="networkidle", timeout=90000)
                print(f"  Page navigation completed.")

                # Basic Cloudflare detection
                initial_title = page.title()
                cloudflare_indicators = [
                    "Just a moment...",
                    "Checking your browser",
                    "Please wait"
                ]

                if any(indicator in initial_title for indicator in cloudflare_indicators):
                    print(f"    INFO: Cloudflare detected. Waiting...")
                    try:
                        page.wait_for_timeout(5000)
                        print(f"    INFO: Cloudflare resolved.")
                    except Exception as e_cf:
                        print(f"    WARNING: Cloudflare wait failed: {e_cf}")

                page.wait_for_selector("body", timeout=10000)
                print(f"Successfully navigated to: {current_url}")

                html_content = page.content()
                soup = BeautifulSoup(html_content, "html.parser")

                # ============================================================
                # === BRANDING ANALYSIS: COLOR PALETTE ===
                # ============================================================

                color_palette = {
                    "css_custom_properties": {},
                    "computed_colors": {},
                    "primary_colors": [],
                    "color_frequency": {}
                }

                # Extract CSS custom properties (CSS variables)
                print(f"  Extracting CSS variables...")
                try:
                    css_variables = page.evaluate("""
                        () => {
                            const vars = {};

                            // Try to get from :root computed style
                            const rootStyle = getComputedStyle(document.documentElement);

                            // Get all CSS custom properties from stylesheets
                            for (let sheet of document.styleSheets) {
                                try {
                                    for (let rule of sheet.cssRules || sheet.rules) {
                                        if (rule.selectorText === ':root' && rule.style) {
                                            for (let i = 0; i < rule.style.length; i++) {
                                                const prop = rule.style[i];
                                                if (prop.startsWith('--')) {
                                                    vars[prop] = rule.style.getPropertyValue(prop).trim();
                                                }
                                            }
                                        }
                                    }
                                } catch(e) { /* CORS or invalid rule */ }
                            }

                            return vars;
                        }
                    """)

                    if css_variables:
                        # Filter for color-related variables
                        for prop, value in css_variables.items():
                            if is_color_value(value):
                                color_palette["css_custom_properties"][prop] = value

                    print(f"    Found {len(color_palette['css_custom_properties'])} color variables")

                except Exception as e:
                    print(f"    Could not extract CSS variables: {e}")

                # Extract computed colors from key elements
                print(f"  Extracting computed colors from elements...")
                try:
                    computed_colors = page.evaluate("""
                        () => {
                            const selectors = [
                                'body',
                                'header',
                                'nav',
                                'h1', 'h2', 'h3',
                                'a',
                                'button',
                                '.btn', '.button',
                                'footer',
                                '.hero', '.banner',
                                '[class*="primary"]',
                                '[class*="secondary"]'
                            ];

                            const colors = {};

                            selectors.forEach(selector => {
                                const el = document.querySelector(selector);
                                if (el) {
                                    const style = getComputedStyle(el);
                                    colors[selector] = {
                                        color: style.color,
                                        backgroundColor: style.backgroundColor,
                                        borderColor: style.borderTopColor
                                    };
                                }
                            });

                            return colors;
                        }
                    """)

                    if computed_colors:
                        # Process and normalize colors
                        all_colors = []
                        for selector, styles in computed_colors.items():
                            processed = {}
                            for prop, value in styles.items():
                                if value and value != 'rgba(0, 0, 0, 0)' and value != 'transparent':
                                    hex_color = extract_color_from_rgb(value)
                                    if hex_color:
                                        processed[prop] = hex_color
                                        all_colors.append(hex_color)

                            if processed:
                                color_palette["computed_colors"][selector] = processed

                        # Count color frequency
                        color_freq = {}
                        for color in all_colors:
                            color_freq[color] = color_freq.get(color, 0) + 1

                        # Sort by frequency and take top colors
                        sorted_colors = sorted(
                            color_freq.items(),
                            key=lambda x: x[1],
                            reverse=True
                        )

                        color_palette["primary_colors"] = [c[0] for c in sorted_colors[:10]]
                        color_palette["color_frequency"] = dict(sorted_colors[:15])

                        print(f"    Extracted {len(all_colors)} color values from {len(computed_colors)} elements")

                except Exception as e:
                    print(f"    Could not extract computed colors: {e}")

                # ============================================================
                # === BRANDING ANALYSIS: TYPOGRAPHY ===
                # ============================================================

                typography = {
                    "web_font_services": [],
                    "font_families_used": {},
                    "custom_fonts_loaded": [],
                    "google_fonts_detected": [],
                    "typeface_hierarchy": {}
                }

                # Detect font services from network requests
                print(f"  Detecting font services...")
                for req_url in requests_log:
                    for service_name, patterns in FONT_SERVICE_SIGNATURES.items():
                        for pattern in patterns:
                            if re.search(pattern, req_url, re.IGNORECASE):
                                if service_name == "CustomWebFonts":
                                    # Store the actual font file URL
                                    if req_url not in typography["custom_fonts_loaded"]:
                                        typography["custom_fonts_loaded"].append(req_url)
                                elif service_name == "GoogleFonts":
                                    # Extract font family names from Google Fonts URLs
                                    family_match = re.search(r'family=([^&]+)', req_url)
                                    if family_match:
                                        fonts = family_match.group(1).split('|')
                                        for font in fonts:
                                            font_name = font.split(':')[0].replace('+', ' ')
                                            if font_name not in typography["google_fonts_detected"]:
                                                typography["google_fonts_detected"].append(font_name)

                                if service_name not in typography["web_font_services"]:
                                    typography["web_font_services"].append(service_name)
                                break

                print(f"    Found {len(typography['web_font_services'])} font services")

                # Extract computed fonts from key elements
                print(f"  Extracting typography from elements...")
                try:
                    typography_data = page.evaluate("""
                        () => {
                            const elements = {
                                'body': document.body,
                                'h1': document.querySelector('h1'),
                                'h2': document.querySelector('h2'),
                                'h3': document.querySelector('h3'),
                                'h4': document.querySelector('h4'),
                                'p': document.querySelector('p'),
                                'a': document.querySelector('a'),
                                'button': document.querySelector('button'),
                                'nav': document.querySelector('nav'),
                                '.btn': document.querySelector('.btn'),
                                'strong': document.querySelector('strong'),
                                'em': document.querySelector('em')
                            };

                            const fonts = {};

                            for (let [key, el] of Object.entries(elements)) {
                                if (el) {
                                    const style = getComputedStyle(el);
                                    fonts[key] = {
                                        fontFamily: style.fontFamily,
                                        fontSize: style.fontSize,
                                        fontWeight: style.fontWeight,
                                        fontStyle: style.fontStyle,
                                        lineHeight: style.lineHeight,
                                        letterSpacing: style.letterSpacing,
                                        textTransform: style.textTransform
                                    };
                                }
                            }

                            return fonts;
                        }
                    """)

                    if typography_data:
                        typography["font_families_used"] = typography_data

                        # Extract unique font families for hierarchy
                        unique_fonts = {}
                        for selector, styles in typography_data.items():
                            family = styles.get('fontFamily', '')
                            if family and family not in unique_fonts:
                                unique_fonts[family] = {
                                    'used_in': [selector],
                                    'sample_size': styles.get('fontSize'),
                                    'sample_weight': styles.get('fontWeight')
                                }
                            elif family:
                                unique_fonts[family]['used_in'].append(selector)

                        typography["typeface_hierarchy"] = unique_fonts
                        print(f"    Extracted typography from {len(typography_data)} elements")

                except Exception as e:
                    print(f"    Could not extract typography data: {e}")

                # ============================================================
                # === BRANDING ANALYSIS: VISUAL ASSETS ===
                # ============================================================

                visual_assets = {
                    "logo": {
                        "url": None,
                        "alt_text": None,
                        "dimensions": None
                    },
                    "favicon": {
                        "url": None,
                        "type": None
                    },
                    "og_image": None,
                    "touch_icons": [],
                    "svg_logos": []
                }

                # Extract logo
                print(f"  Extracting visual assets...")
                logo_selectors = [
                    'img[class*="logo" i]',
                    'img[id*="logo" i]',
                    'a[class*="logo" i] img',
                    '.logo img',
                    '#logo img',
                    'header img',
                    'nav img'
                ]

                for selector in logo_selectors:
                    logo = soup.select_one(selector)
                    if logo and logo.get('src'):
                        visual_assets["logo"]["url"] = logo.get('src')
                        visual_assets["logo"]["alt_text"] = logo.get('alt', '')

                        # Try to get dimensions
                        try:
                            dims = page.evaluate(f"""
                                () => {{
                                    const img = document.querySelector('{selector}');
                                    if (img) {{
                                        return {{
                                            width: img.naturalWidth || img.width,
                                            height: img.naturalHeight || img.height
                                        }};
                                    }}
                                    return null;
                                }}
                            """)
                            if dims:
                                visual_assets["logo"]["dimensions"] = dims
                        except:
                            pass

                        break

                # Look for SVG logos
                svg_logos = soup.select('svg[class*="logo" i], svg[id*="logo" i]')
                if svg_logos:
                    for svg in svg_logos[:3]:  # Limit to first 3
                        visual_assets["svg_logos"].append({
                            "class": svg.get('class', []),
                            "id": svg.get('id', ''),
                            "viewBox": svg.get('viewBox', '')
                        })

                # Favicon
                favicon_selectors = [
                    'link[rel="icon"]',
                    'link[rel="shortcut icon"]',
                    'link[rel="apple-touch-icon"]'
                ]

                for selector in favicon_selectors:
                    for link in soup.select(selector):
                        href = link.get('href')
                        if href:
                            if 'apple-touch-icon' in link.get('rel', []):
                                visual_assets["touch_icons"].append({
                                    "url": href,
                                    "sizes": link.get('sizes', '')
                                })
                            else:
                                visual_assets["favicon"]["url"] = href
                                visual_assets["favicon"]["type"] = link.get('type', '')
                                break

                # Open Graph image
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    visual_assets["og_image"] = og_image.get('content')

                # Twitter card image (fallback)
                if not visual_assets["og_image"]:
                    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
                    if twitter_image and twitter_image.get('content'):
                        visual_assets["og_image"] = twitter_image.get('content')

                print(f"    Extracted logo: {visual_assets['logo']['url']}")
                print(f"    Extracted favicon: {visual_assets['favicon']['url']}")

                # ============================================================
                # === BRANDING ANALYSIS: DESIGN PATTERNS ===
                # ============================================================

                design_patterns = {
                    "button_styles": {},
                    "spacing_system": {},
                    "border_radius": {},
                    "shadows": []
                }

                print(f"  Analyzing design patterns...")
                try:
                    design_data = page.evaluate("""
                        () => {
                            const patterns = {
                                buttons: {},
                                spacing: {},
                                borders: {},
                                shadows: []
                            };

                            // Analyze buttons
                            const buttons = document.querySelectorAll('button, .btn, .button, [role="button"]');
                            if (buttons.length > 0) {
                                const firstBtn = buttons[0];
                                const style = getComputedStyle(firstBtn);
                                patterns.buttons = {
                                    padding: style.padding,
                                    borderRadius: style.borderRadius,
                                    backgroundColor: style.backgroundColor,
                                    color: style.color,
                                    fontSize: style.fontSize,
                                    fontWeight: style.fontWeight,
                                    border: style.border,
                                    textTransform: style.textTransform,
                                    boxShadow: style.boxShadow
                                };
                            }

                            // Analyze spacing (from container elements)
                            const containers = document.querySelectorAll('section, .container, main');
                            if (containers.length > 0) {
                                const style = getComputedStyle(containers[0]);
                                patterns.spacing = {
                                    padding: style.padding,
                                    margin: style.margin,
                                    gap: style.gap
                                };
                            }

                            // Collect border radius values
                            const elementsWithRadius = document.querySelectorAll('*');
                            const radiusValues = new Set();
                            for (let i = 0; i < Math.min(elementsWithRadius.length, 100); i++) {
                                const el = elementsWithRadius[i];
                                const radius = getComputedStyle(el).borderRadius;
                                if (radius && radius !== '0px') {
                                    radiusValues.add(radius);
                                }
                            }
                            patterns.borders = {
                                radiusValues: Array.from(radiusValues).slice(0, 10)
                            };

                            // Collect shadow values
                            const shadowValues = new Set();
                            for (let i = 0; i < Math.min(elementsWithRadius.length, 100); i++) {
                                const el = elementsWithRadius[i];
                                const shadow = getComputedStyle(el).boxShadow;
                                if (shadow && shadow !== 'none') {
                                    shadowValues.add(shadow);
                                }
                            }
                            patterns.shadows = Array.from(shadowValues).slice(0, 10);

                            return patterns;
                        }
                    """)

                    if design_data:
                        design_patterns["button_styles"] = design_data.get("buttons", {})
                        design_patterns["spacing_system"] = design_data.get("spacing", {})
                        design_patterns["border_radius"] = design_data.get("borders", {})
                        design_patterns["shadows"] = design_data.get("shadows", [])

                        print(f"    Extracted design patterns")

                except Exception as e:
                    print(f"    Could not extract design patterns: {e}")

                # ============================================================
                # === INTELLIGENT CLASSIFICATION ===
                # ============================================================

                print(f"  Classifying colors and fonts...")

                # --- Color Classification ---
                color_classification = classify_colors(
                    color_palette,
                    computed_colors
                )

                # --- Font Classification ---
                font_classification = classify_fonts(
                    typography,
                    typography_data if 'typography_data' in locals() else {}
                )

                # ============================================================
                # === COMPILE RESULTS ===
                # ============================================================

                page_fetch_time_utc = datetime.now(timezone.utc)
                page_title_val = page.title()

                data_for_json = {
                    "color_palette": color_palette,
                    "color_classification": color_classification.get("color_classification", {}),
                    "color_confidence_scores": color_classification.get("confidence_scores", {}),
                    "typography": typography,
                    "font_classification": font_classification.get("font_classification", {}),
                    "font_confidence_scores": font_classification.get("confidence_scores", {}),
                    "visual_assets": visual_assets,
                    "design_patterns": design_patterns
                }

                url_result_object = {
                    "url": current_url,
                    "fetch_status": "success",
                    "error_details": None,
                    "fetch_timestamp_utc": page_fetch_time_utc.isoformat(),
                    "page_title": page_title_val,
                    "data": data_for_json
                }

                processed_urls_results_list.append(url_result_object)
                successful_fetches += 1

            except Exception as e:
                print(f"Could not process {current_url}. Error: {e}")
                page_fetch_time_utc = datetime.now(timezone.utc)
                url_result_object = {
                    "url": current_url,
                    "fetch_status": "error",
                    "error_details": str(e),
                    "fetch_timestamp_utc": page_fetch_time_utc.isoformat(),
                    "page_title": None,
                    "data": None
                }
                processed_urls_results_list.append(url_result_object)
                failed_fetches += 1

            finally:
                try:
                    if page and not page.is_closed():
                        page.close()
                except:
                    pass
                time.sleep(1)

        # =====================================================================
        # === FINAL OUTPUT ===
        # =====================================================================

        final_json_output = {
            "collection_metadata": {
                "collector_version": "1.0.0",
                "collector_type": "branding",
                "collection_timestamp_utc": collection_start_time_utc.isoformat(),
                "total_urls_processed": len(urls_to_process),
                "total_urls_successful": successful_fetches,
                "total_urls_failed": failed_fetches
            },
            "url_analysis_results": processed_urls_results_list
        }

        # Create output directory
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}/")

        # Generate output filename
        if args.url:
            parsed_url = urlparse(args.url)
            domain = parsed_url.netloc.replace('www.', '').replace(':', '_')
            output_filename = os.path.join(output_dir, f"deepstack_branding-{domain}.json")
        else:
            output_filename = os.path.join(output_dir, "deepstack_branding.json")

        try:
            with open(output_filename, 'w') as f:
                json.dump(final_json_output, f, indent=2)
            print(f"\nResults successfully saved to {output_filename}")
        except IOError as e:
            print(f"\nError writing results to {output_filename}: {e}")
        except TypeError as e:
            print(f"\nError serializing data to JSON: {e}")

        # Console output summary
        print("\n--- Branding Analysis Summary ---")
        for result_item in processed_urls_results_list:
            print(f"\nBranding analysis for {result_item['url']}:")

            if result_item['fetch_status'] == "error":
                print(f"  Error: {result_item['error_details']}")
                continue

            data_payload = result_item.get('data')
            if not data_payload:
                print("  Error: No data payload found.")
                continue

            print(f"  Page Title: {result_item.get('page_title', 'Not found')}")

            # Color Palette
            colors = data_payload.get('color_palette', {})
            print(f"  Color Palette:")
            print(f"    CSS Variables: {len(colors.get('css_custom_properties', {}))} found")
            print(f"    Primary Colors: {colors.get('primary_colors', [])[:5]}")

            # Typography
            typo = data_payload.get('typography', {})
            print(f"  Typography:")
            print(f"    Font Services: {typo.get('web_font_services', [])}")
            print(f"    Google Fonts: {typo.get('google_fonts_detected', [])}")
            print(f"    Unique Typefaces: {len(typo.get('typeface_hierarchy', {}))}")

            # Visual Assets
            assets = data_payload.get('visual_assets', {})
            print(f"  Visual Assets:")
            print(f"    Logo URL: {assets.get('logo', {}).get('url', 'Not found')}")
            print(f"    Favicon: {assets.get('favicon', {}).get('url', 'Not found')}")
            print(f"    OG Image: {assets.get('og_image', 'Not found')}")

            # Design Patterns
            patterns = data_payload.get('design_patterns', {})
            print(f"  Design Patterns:")
            button_styles = patterns.get('button_styles', {})
            if button_styles:
                print(f"    Button Border Radius: {button_styles.get('borderRadius', 'N/A')}")
                print(f"    Button Padding: {button_styles.get('padding', 'N/A')}")
            print(f"    Shadow Styles: {len(patterns.get('shadows', []))} variations")

        print("\nAttempting to close browser resources...")
        try:
            if context:
                context.close()
                print("Browser context closed.")
            if browser and browser.is_connected():
                browser.close()
                print("Browser closed.")
        except Exception as e_close:
            print(f"Error during browser close: {e_close}")


if __name__ == "__main__":
    main()
