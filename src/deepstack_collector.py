"""
DeepStack Collector - Website MarTech Analysis Tool

Analyzes websites for marketing technology stacks, conversion tracking, and competitive intelligence.
Uses Playwright for web automation and BeautifulSoup for HTML parsing.

Output Files:
    - Single URL mode (-u): output/deepstack_output-{domain}.json (e.g., output/deepstack_output-example.com.json)
    - Batch mode: output/deepstack_output.json (reads from urls_to_analyze.txt)

Usage:
    Single URL Mode:
        python3 deepstack_collector.py -u https://example.com
        # Output: output/deepstack_output-example.com.json

        python3 deepstack_collector.py -u https://www.google.com
        # Output: output/deepstack_output-google.com.json

        python3 deepstack_collector.py -u https://subdomain.example.com:8080
        # Output: output/deepstack_output-subdomain.example.com_8080.json

    Batch Mode:
        python3 deepstack_collector.py
        # Output: output/deepstack_output.json (reads from urls_to_analyze.txt)
"""

from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup
import re
import json  # Ensure this is present
from datetime import datetime, timezone  # For timestamps
import random  # For random delays between requests
from playwright_stealth import stealth_sync  # For avoiding detection
import argparse  # For command-line argument parsing
from urllib.parse import urlparse  # For extracting domain names
import os  # For directory operations


# -----------------------------------------------------------------------------
# --- CONFIGURATION & SIGNATURES ---
# -----------------------------------------------------------------------------

# --- MarTech Signatures Definition ---
# Each key is the MarTech tool name.
# The value is a list of regex patterns to search for.
MARTECH_SIGNATURES = {
    "GoogleAnalytics": [
        r"google-analytics\.com/ga\.js",
        r"googletagmanager\.com/gtag/js",
        r"UA-\d{4,10}-\d{1,4}",
        r"G-[A-Z0-9]{10}"
    ],
    "GoogleTagManager": [
        r"googletagmanager\.com/gtm\.js",
        r"GTM-[A-Z0-9]{7}"
    ],
    "HubSpot": [
        r"js\.hs-scripts\.com",
        r"js\.hs-analytics\.net",
        r"forms.hsforms.com",
        r"track.hubspot.com",
        r"window._hsq"
    ],
    "MetaPixel": [
        r"connect\.facebook\.net",
        r"fbq\s*\("
    ],
    "Marketo": [
        r"munchkin\.marketo\.net",
        r"Munchkin\.init"
    ],
    "LinkedInInsightTag": [
        r"snap\.licdn\.com/li\.lms-analytics",
        r"linkedin_partner_id"
    ],
    "Segment": [
        r"cdn\.segment\.com/analytics\.js",
        r"analytics\.writeKey"
    ],
    "Hotjar": [
        r"static\.hotjar\.com",
        r"window.hj"
    ],
    "Optimizely": [
        r"cdn\.optimizely\.com",
        r"window\.optimizely"
    ]
    # Add more signatures here as needed
}

# --- URLs to Analyze ---
# URLs will be read from an external file.
# Define the name of the file containing URLs, one URL per line.
URL_INPUT_FILE = "urls_to_analyze.txt"

def load_urls_from_file(filename):
    """Loads URLs from a specified file, one URL per line."""
    urls = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith("#"): # Ignore empty lines and comments
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url # Add https if no scheme
                    urls.append(url)
        if not urls:
            print(f"WARNING: No URLs found in {filename}. Please check the file.")
        else:
            print(f"Loaded {len(urls)} URL(s) from {filename}.")
    except FileNotFoundError:
        print(f"ERROR: URL input file '{filename}' not found. Please create it and add URLs.")
        # Create an empty file to prevent further errors if user wants to run and then populate
        with open(filename, 'w') as f:
            f.write("# Add URLs here, one per line (e.g., https://www.example.com)\n")
        print(f"An empty '{filename}' has been created for you. Please populate it and rerun the script.")
        # Exiting or returning empty list are options. For now, let it proceed with empty list
        # and the main loop won't run for URLs, but JSON metadata will still be generated.
    except Exception as e:
        print(f"ERROR: Could not read URLs from '{filename}': {e}")
    return urls

# URLS_TO_ANALYZE = load_urls_from_file(URL_INPUT_FILE)

# --- Cookie Consent Signatures Definition ---
# Keywords or patterns to identify common Cookie Consent Management Platforms (CMPs)
# These can be found in script URLs, global JS variables, or specific HTML element attributes/classes
COOKIE_CONSENT_SIGNATURES = {
    "OneTrust": [
        r"onetrust",
        r"optanon",
        r"cdn\.cookielaw\.org",
        r"cookie-cdn\.cookiepro\.com",
        r"OptanonConsent"  # Cookie name
    ],
    "Cookiebot": [
        r"cookiebot",
        r"consent\.cookiebot\.com/uc\.js",
        r"data-cbid="
    ],
    "TrustArc": [
        r"trustarc",
        r"truste\.com",  # truste.com is often part of their script/service URLs
        r"TAconsentID"  # Cookie name
    ],
    "Osano": [r"osano"],  # Keep existing
    "Usercentrics": [
        r"usercentrics",
        r"app\.usercentrics\.eu",
        r"uc_settings"  # localStorage key
    ],
    "CookieYes": [r"cookieyes"],  # Keep existing
    "Complianz": [r"complianz"],  # Keep existing
    "QuantcastChoice": [
        r"quantserve\.com/choice",
        r"window\.__cmp",  # Common IAB CMP function
        r"window\.__tcfapi"  # Common IAB TCF v2 function
    ],
    "Iubenda": [
        r"iubenda\.com/cs/iubenda_cs\.js",
        r"window._iub"
    ],
    "Crownpeak (Evidon)": [
        r"evidon\.com",
        r"evidon-sitenotice-tag\.js",
        r"window\.evidon"
    ],
    "CivicUK": [
        r"cc\.cdn\.civiccomputing\.com",
        r"CookieControl"  # JS object
    ],
    "TermsFeed": [
        r"termsfeed\.com/public/cookie-consent",
        r"cookieconsent\.run"
    ]
    # Generic IAB TCFv2 signal could be just window.__tcfapi
}

# --- CDN Domain Patterns (for heuristic check) ---
# Common patterns found in CDN URLs. This is not exhaustive.
CDN_DOMAIN_PATTERNS = [
    r"cdn\.jsdelivr\.net",
    r"cdnjs\.cloudflare\.com",
    r"ajax\.googleapis\.com",  # Google Hosted Libraries
    r"cdn\.datatables\.net",
    r"maxcdn\.bootstrapcdn\.com",
    r"stackpath\.bootstrapcdn\.com",  # Successor to MaxCDN
    r"unpkg\.com",  # Often used for NPM packages
    r"code\.jquery\.com",
    # Cloud Provider CDNs
    r"cloudfront\.net",  # AWS CloudFront
    r"akamaized\.net",  # Akamai
    r"akamaihd\.net",  # Akamai
    r"azureedge\.net",  # Azure CDN
    r"app\.netdna-cdn\.com",  # MaxCDN/StackPath
    r"stackpathcdn\.com",  # StackPath
    r"fastly\.net",  # Fastly
    r"cdn\.shopify\.com",  # Shopify's CDN
    r"wp\.com",  # WordPress/Jetpack CDN for images/assets
    r"static\.squarespace\.com",  # Squarespace
    r"static\.wixstatic\.com",  # Wix
    # Company-specific CDNs (examples, can be expanded)
    r"static\.hubspot\.com",
    r"sfdcstatic\.com",  # Salesforce
    r"qsf\.fs\.qualtrics\.com"  # Qualtrics
]
# --- Feature Flag Signatures Definition ---
# Patterns to identify common client-side feature flag tools or practices
FEATURE_FLAG_SIGNATURES = {
    "LaunchDarkly": [
        r"ldclient", # LaunchDarkly client object
        r"launchdarkly\.com", # SDK host
        r"clientstream\.launchdarkly\.com"
    ],
    "Optimizely_Feature_Flags_API": [ # Specific Optimizely Feature Flag API usage in inline scripts
         r"optimizely\.isFeatureEnabled\(",
         r"optimizely\.getFeatureVariables\("
    ],
    "SplitIO": [
        r"split\.io", # SDK host
        r"SplitFactory" # Main object for Split.io
    ],
    "Flagsmith": [
        r"flagsmith\.com", # SDK host or API
        r"window\.Flagsmith" # Global object
    ],
    "Statsig": [
        r"statsig\.com", # SDK host
        r"StatsigClient" # Client object
    ],
    "PostHog_Feature_Flags_API": [ # Specific PostHog Feature Flag API usage
        r"posthog.*feature_flags",
        r"posthog.*isFeatureEnabled\("
    ],
    "Generic_Feature_Flag_Object": [
        r"window\.featureFlags", # Common global object pattern
        r"window\.ftToggle" # Another common pattern (feature toggles)
    ]
}

# --- Conversion Event Signatures Definition ---
# Patterns to identify common client-side conversion tracking events in inline scripts
CONVERSION_EVENT_SIGNATURES = {
    "MetaPixel_Conversion": [
        r"fbq\s*\(\s*['\"]track['\"]\s*,\s*['\"](Lead|CompleteRegistration|Purchase|AddToCart|InitiateCheckout|ViewContent|Search|Contact|Subscribe)['\"]"
    ],
    "Google_Conversion": [ # Google Ads, GA4
        r"gtag\s*\(\s*['\"]event['\"]\s*,\s*['\"](conversion|sign_up|purchase|begin_checkout|add_to_cart|generate_lead|view_item|search)['\"]",
        r"send_to\s*:\s*['\"](AW-[^\s'\"/]+|G-[^\s'\"/]+)/[^\s'\"}]+['\"]" # More specific send_to with IDs
    ],
    "LinkedIn_Conversion": [
        r"lintrk\s*\(\s*['\"]track['\"]\s*,\s*\{\s*conversion_id:\s*\d+"
    ],
    "HubSpot_Conversion_Event": [ # More specific than general HubSpot tracking
        r"_hsq\.push\(\s*\[\s*['\"]trackEvent['\"]\s*,\s*\{\s*id:\s*['\"][^'\"]+['\"]"
    ],
    "Twitter_Conversion": [
        r"twq\s*\(\s*['\"]event['\"]\s*,\s*['\"]tw-[a-zA-Z0-9]+-[a-zA-Z0-9]+['\"]" # General event structure
        # Add specific Twitter event names if needed, e.g., 'twq(\'track\',\'Purchase\''
    ]
}
# --- Main Function ---
def main():
    # --- Argument Parsing for Command-Line URL ---
    parser = argparse.ArgumentParser(description="DeepStack Collector: Analyze website(s) for MarTech and other signals.")
    parser.add_argument("-u", "--url", help="A single URL to analyze. If provided, urls_to_analyze.txt will be ignored.")
    args = parser.parse_args()

    urls_to_process = [] # This will hold the URLs the script will iterate over

    if args.url:
        single_url = args.url
        # Ensure the URL has a scheme
        if not single_url.startswith(('http://', 'https://')):
            single_url = 'https://' + single_url
        urls_to_process = [single_url]
        print(f"INFO: Analyzing single URL provided via command line: {single_url}")
    else:
        # URL_INPUT_FILE is still a global constant
        urls_to_process = load_urls_from_file(URL_INPUT_FILE)
        # load_urls_from_file already prints messages about loaded URLs or errors

    if not urls_to_process:
        print("INFO: No URLs to analyze (neither from command line nor from file). Exiting.")
        return # Exit if there are no URLs

    print("DeepStack Collector starting...") # Moved this message here

    # The rest of your main() function (with sync_playwright() as p: ...) follows from here
    # Ensure the main processing loop uses 'urls_to_process'

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Set to False for testing, can be True later
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-web-security",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            java_script_enabled=True,
            accept_downloads=False,
            ignore_https_errors=True
        )
        print("Browser launched.")

        collection_start_time_utc = datetime.now(timezone.utc)
        processed_urls_results_list = [] # This will store the structured data for each URL
        successful_fetches = 0
        failed_fetches = 0

        for current_url in urls_to_process:
            # Add random delay before processing the URL to appear more human-like
            time.sleep(random.uniform(2, 5)) # Waits for a random duration between 2 and 5 seconds
            print(f"\nAttempting to navigate to: {current_url}")

            requests_log = []
            identified_martech_on_page = set()
            data_layer_content_summary = None
            data_layer_exists_on_page = False

            try:
                page = context.new_page()
                stealth_sync(page) # APPLY STEALTH AFTER PAGE CREATION
                page.on("request", lambda request: requests_log.append(request.url))
                # Modified wait strategy with better Cloudflare handling
                page.goto(current_url, wait_until="domcontentloaded", timeout=60000) # Increased timeout for Cloudflare
                
                # --- Enhanced Cloudflare Challenge Detection & Wait ---
                initial_title = page.title()
                
                # Check for various Cloudflare challenge indicators
                cloudflare_indicators = [
                    "Just a moment...",
                    "Checking your browser",
                    "Please wait",
                    "One more step",
                    "Verifying you are human"
                ]
                
                cloudflare_detected = any(indicator in initial_title for indicator in cloudflare_indicators)
                
                if cloudflare_detected or "cf-browser-verification" in page.content():
                    print(f"    INFO: Detected Cloudflare challenge page for {current_url} (Title: '{initial_title}'). Waiting for it to resolve...")
                    
                    try:
                        # Strategy 1: Wait for title change (works for most Cloudflare challenges)
                        # Convert Python list to JavaScript array string
                        js_indicators = str(cloudflare_indicators).replace("'", '"')
                        page.wait_for_function(
                            f"() => !{js_indicators}.some(indicator => document.title.includes(indicator))",
                            timeout=45000
                        )
                        
                        # Strategy 2: Wait for the actual content to load
                        # After challenge, wait for typical page elements
                        try:
                            page.wait_for_selector("h1, h2, p, main, article, [role='main']", timeout=15000)
                        except:
                            # If no semantic elements, just wait for body to have content
                            page.wait_for_function("() => document.body.textContent.trim().length > 100", timeout=15000)
                        
                        # Give the page a moment to fully settle
                        page.wait_for_timeout(2000)
                        
                        print(f"    INFO: Cloudflare challenge resolved for {current_url}. Current title: '{page.title()}'")
                        print(f"Successfully navigated to: {current_url} (after Cloudflare challenge)")
                        
                    except Exception as e_cf:
                        print(f"    WARNING: Cloudflare challenge resolution failed for {current_url}: {e_cf}")
                        
                        # Last resort: Try to wait a bit more and check if content loaded anyway
                        page.wait_for_timeout(5000)
                        final_title = page.title()
                        
                        if final_title != initial_title and not any(indicator in final_title for indicator in cloudflare_indicators):
                            print(f"    INFO: Page title changed, attempting to continue. New title: '{final_title}'")
                        else:
                            raise Exception(f"Cloudflare challenge not resolved: {e_cf}") from e_cf
                else:
                    # Standard page load without Cloudflare
                    page.wait_for_selector("body", timeout=10000)
                    print(f"Successfully navigated to: {current_url} (no Cloudflare challenge detected)")

                # --- End of Cloudflare Challenge Logic ---

                html_content = page.content()
                soup = BeautifulSoup(html_content, "html.parser")
                script_tags = soup.find_all("script") # Define script_tags once here for reuse

                # =====================================================================
                # === CORE ANALYSIS AREA 1: Marketing Technology & Data Foundation ===
                # =====================================================================
                # This area focuses on identifying the tools forming a company's 
                # marketing/sales engine and the infrastructure supporting their data strategy. [cite: 1, 5]

                # -------------------------------------------------------------
                # --- SECTION 1: MarTech Identification from <script> tags ---
                # -------------------------------------------------------------
                # print(f"Analyzing <script> tags for {current_url}...") # Optional debug
                for script_tag in script_tags:
                    script_content_to_check = ""
                    if script_tag.get("src"):
                        script_content_to_check += script_tag.get("src") + " "
                    script_content_to_check += script_tag.string if script_tag.string else ""
                    if script_content_to_check.strip():
                        for tech_name, patterns in MARTECH_SIGNATURES.items():
                            for pattern in patterns:
                                try:
                                    if re.search(pattern, script_content_to_check, re.IGNORECASE):
                                        identified_martech_on_page.add(tech_name)
                                except re.error:
                                    pass
                # print(f"MarTech from scripts: {identified_martech_on_page}") # Optional debug

                # -----------------------------------------------------------------
                # --- SECTION 2: MarTech Identification from Network Requests ---
                # -----------------------------------------------------------------
                # print(f"Analyzing {len(requests_log)} network requests for {current_url}...") # Optional debug
                for req_url in requests_log:
                    for tech_name, patterns in MARTECH_SIGNATURES.items():
                        for pattern in patterns:
                            if r"\." in pattern or r"/" in pattern or "http" in pattern.lower():
                                try:
                                    if re.search(pattern, req_url, re.IGNORECASE):
                                        identified_martech_on_page.add(tech_name)
                                except re.error:
                                    pass
                # print(f"MarTech after network requests: {identified_martech_on_page}") # Optional debug
                
                # -----------------------------------------------------------------
                # --- SECTION 3: Extract window.dataLayer content ---
                # -----------------------------------------------------------------
                # print(f"Attempting to extract dataLayer for {current_url}...") # Optional debug
                try:
                    data_layer_raw = page.evaluate("() => window.dataLayer")
                    if data_layer_raw:
                        data_layer_exists_on_page = True
                        summary_items = []
                        pushes_to_sample = min(len(data_layer_raw), 5)
                        for i, item in enumerate(data_layer_raw[:pushes_to_sample]):
                            if isinstance(item, dict):
                                summary_items.append(f"Push {i+1} (keys): {sorted(list(item.keys()))}")
                            else:
                                summary_items.append(f"Push {i+1} (type): {type(item).__name__}")
                        data_layer_content_summary = {
                            "total_pushes": len(data_layer_raw),
                            "sample_pushes_structure": summary_items
                        }
                    # else: # Optional debug
                        # print("DataLayer not found or empty.")
                except Exception as e:
                    # print(f"Could not evaluate dataLayer for {current_url}: {e}") # Optional debug
                    data_layer_content_summary = {"error": f"Could not evaluate dataLayer: {str(e)}"}

                # -----------------------------------------------------------------
                # --- SECTION 4: Identify Cookie Consent Mechanisms ---
                # -----------------------------------------------------------------
                # print(f"Identifying cookie consent mechanisms for {current_url}...") # Optional debug
                identified_cookie_consent_tools = set()
                for script_tag in script_tags:
                    script_content_to_check = ""
                    if script_tag.get("src"):
                        script_content_to_check += script_tag.get("src") + " "
                    script_content_to_check += script_tag.string if script_tag.string else ""
                    if script_content_to_check.strip():
                        for tool_name, patterns in COOKIE_CONSENT_SIGNATURES.items():
                            for pattern in patterns:
                                try:
                                    if re.search(pattern, script_content_to_check, re.IGNORECASE):
                                        identified_cookie_consent_tools.add(tool_name)
                                except re.error:
                                    pass
                for req_url in requests_log:
                    for tool_name, patterns in COOKIE_CONSENT_SIGNATURES.items():
                        for pattern in patterns:
                            if r"\." in pattern or r"/" in pattern or "http" in pattern.lower():
                                try:
                                    if re.search(pattern, req_url, re.IGNORECASE):
                                        identified_cookie_consent_tools.add(tool_name)
                                except re.error:
                                    pass
                for tool_name, patterns in COOKIE_CONSENT_SIGNATURES.items():
                    for pattern in patterns:
                        try:
                            if re.search(pattern, html_content, re.IGNORECASE):
                                identified_cookie_consent_tools.add(tool_name)
                        except re.error:
                            pass
                # print(f"Cookie consent tools found: {identified_cookie_consent_tools}") # Optional debug

                # =====================================================================
                # === CORE ANALYSIS AREA 2: Organic Presence & Content Signals ===
                # =====================================================================
                # This area evaluates efforts to attract organic traffic and how 
                # content is structured for search engines. [cite: 1, 7]
                
                # -----------------------------------------------------------------
                # --- SECTION 5: Organic Presence & Content Signals ---
                # -----------------------------------------------------------------
                # print(f"Extracting Organic Presence signals for {current_url}...") # Optional debug
                organic_signals = {
                    "meta_title": None, "meta_description": None, "meta_keywords": None,
                    "canonical_url": None, "h1_tags": [], "h2_tags": [],
                    "json_ld_scripts": [], "robots_meta": None, "hreflang_tags": []
                }
                title_tag = soup.find("title")
                if title_tag and title_tag.string:
                    organic_signals["meta_title"] = title_tag.string.strip()
                meta_tags = soup.find_all("meta")
                for tag in meta_tags:
                    if tag.get("name", "").lower() == "description" and tag.get("content"):
                        organic_signals["meta_description"] = tag.get("content").strip()
                    elif tag.get("name", "").lower() == "keywords" and tag.get("content"):
                        organic_signals["meta_keywords"] = tag.get("content").strip()
                    elif tag.get("name", "").lower() == "robots" and tag.get("content"):
                        organic_signals["robots_meta"] = tag.get("content").strip()
                canonical_link = soup.find("link", rel=lambda x: x and x.lower() == "canonical")
                if canonical_link and canonical_link.get("href"):
                    organic_signals["canonical_url"] = canonical_link.get("href")
                h1_tags_found = soup.find_all("h1")
                for tag in h1_tags_found:
                    text_content = tag.get_text(separator=' ', strip=True)
                    if text_content: organic_signals["h1_tags"].append(text_content)
                h2_tags_found = soup.find_all("h2")
                for tag in h2_tags_found:
                    text_content = tag.get_text(separator=' ', strip=True)
                    if text_content: organic_signals["h2_tags"].append(text_content)
                json_ld_scripts_found = soup.find_all("script", type="application/ld+json")
                for script in json_ld_scripts_found:
                    if script.string:
                        try:
                            json_content = json.loads(script.string)
                            organic_signals["json_ld_scripts"].append(json_content)
                        except json.JSONDecodeError:
                            organic_signals["json_ld_scripts"].append({"error": "Invalid JSON", "content": script.string.strip()})
                hreflang_links = soup.find_all("link", rel="alternate", hreflang=True)
                for link in hreflang_links:
                    if link.get("href"):
                        organic_signals["hreflang_tags"].append({"lang": link.get("hreflang"), "href": link.get("href")})
                # print(f"Organic signals extracted: {organic_signals}") # Optional debug

                # ============================================================================================
                # === CORE ANALYSIS AREA 3: User Experience & Website Performance (Client-Side Clues) ===
                # ============================================================================================
                # This area identifies client-side factors impacting user perception and interaction. [cite: 1, 11]

                # -----------------------------------------------------------------
                # --- SECTION 6: User Experience & Website Performance Clues ---
                # -----------------------------------------------------------------
                # print(f"Extracting UX & Performance clues for {current_url}...") # Optional debug
                ux_performance_clues = {
                    "viewport_meta_content": None, "identified_cdn_domains": set(),
                    "lazy_loading_images": {"sampled_images": 0, "with_lazy_loading": 0},
                    "alt_text_images": {"sampled_images": 0, "with_alt_text": 0}
                }
                viewport_meta = soup.find("meta", attrs={"name": "viewport"})
                if viewport_meta and viewport_meta.get("content"):
                    ux_performance_clues["viewport_meta_content"] = viewport_meta.get("content").strip()
                for script_tag in script_tags:
                    src = script_tag.get("src")
                    if src:
                        for pattern in CDN_DOMAIN_PATTERNS:
                            if re.search(pattern, src, re.IGNORECASE):
                                match = re.search(r"://([^/]+)", src)
                                if match: ux_performance_clues["identified_cdn_domains"].add(match.group(1))
                                break
                css_links = soup.find_all("link", rel="stylesheet", href=True)
                for link_tag in css_links:
                    href = link_tag.get("href")
                    if href:
                        for pattern in CDN_DOMAIN_PATTERNS:
                            if re.search(pattern, href, re.IGNORECASE):
                                match = re.search(r"://([^/]+)", href)
                                if match: ux_performance_clues["identified_cdn_domains"].add(match.group(1))
                                break
                ux_performance_clues["identified_cdn_domains"] = sorted(list(ux_performance_clues["identified_cdn_domains"]))
                img_tags = soup.find_all("img")
                sample_size = min(len(img_tags), 20)
                ux_performance_clues["lazy_loading_images"]["sampled_images"] = sample_size
                ux_performance_clues["alt_text_images"]["sampled_images"] = sample_size
                for i in range(sample_size):
                    img = img_tags[i]
                    if img.get("loading") == "lazy":
                        ux_performance_clues["lazy_loading_images"]["with_lazy_loading"] += 1
                    alt_attr = img.get("alt")
                    if alt_attr is not None:
                        ux_performance_clues["alt_text_images"]["with_alt_text"] += 1
                # print(f"UX/Performance signals extracted: {ux_performance_clues}") # Optional debug

                # =====================================================================
                # === CORE ANALYSIS AREA 4: Conversion & Funnel Effectiveness (Planned) ===
                # =====================================================================
                # This area aims to understand how user progression towards goals is tracked 
                # and how leads are captured. [cite: 1, 9]
                # (Code for this section to be added here)
                # E.g., identify conversion pixel calls, analyze form tags

                conversion_funnel_effectiveness = {
                    "identified_conversion_events": set(),
                    "forms_analysis": []
                }

                # 1. Identify specific conversion pixel function calls
                # Search inline script content primarily
                for script_tag in script_tags: # script_tags is already defined
                    if script_tag.string: # Only check inline scripts
                        inline_script_content = script_tag.string
                        for event_type, patterns in CONVERSION_EVENT_SIGNATURES.items():
                            for pattern in patterns:
                                try:
                                    if re.search(pattern, inline_script_content, re.IGNORECASE):
                                        # Extract the specific event name if possible (e.g., 'Lead' from fbq('track','Lead'))
                                        match = re.search(pattern, inline_script_content, re.IGNORECASE)
                                        if match and len(match.groups()) > 0 and match.group(1):
                                            conversion_funnel_effectiveness["identified_conversion_events"].add(f"{event_type}: {match.group(1)}")
                                        else:
                                            conversion_funnel_effectiveness["identified_conversion_events"].add(event_type)
                                except re.error:
                                    pass
                conversion_funnel_effectiveness["identified_conversion_events"] = sorted(list(conversion_funnel_effectiveness["identified_conversion_events"]))

                # 2. Analyze <form> tags using page.evaluate() for better dynamic content handling
                print(f"    Analyzing forms for {current_url} using page.evaluate()...") # Optional debug
                js_get_forms_script = """
                () => {
                  const forms = Array.from(document.forms);
                  return forms.map(form => {
                    const formDetails = {
                      form_id: form.id || null,
                      form_name: form.name || null,
                      form_classes: Array.from(form.classList),
                      form_action: form.action || null, // This will be the fully resolved URL
                      form_method: form.method ? form.method.toUpperCase() : 'GET',
                      handler_attributes: {},
                      input_fields_summary: []
                    };

                    // Check for common data-* attributes used by form handlers
                    if (form.dataset.netlify === 'true') formDetails.handler_attributes.netlify_form = true;
                    // Note: dataset access converts kebab-case (data-hs-cf-bound) to camelCase (hsCfBound)
                    if (form.dataset.hsCfBound === 'true') formDetails.handler_attributes.hubspot_form_indicator = true;
                    if (form.dataset.marketoFormId) formDetails.handler_attributes.marketo_form_id = form.dataset.marketoFormId;
                    // Add other specific data-attribute checks if needed, e.g., data-pardot-form-id, etc.

                    const inputs = Array.from(form.elements); // form.elements gets all form controls
                    // Define key input types and names to look for - keep these consistent with previous logic or refine
                    const keyInputTypes = ["email", "text", "tel", "submit", "hidden", "password", "search", "url", "number", "checkbox", "radio", "date", "select-one", "select-multiple", "textarea"];
                    const keyInputNames = ["email", "name", "firstname", "first_name", "last_name", "lastname", "phone", "tel", "mobile", "company", "website", "job_title", "query", "q", "search", "address", "city", "state", "zip", "postal", "country", "utm_"];

                    inputs.forEach(input => {
                      const inputName = (input.name || '').toLowerCase();
                      const inputType = (input.type || input.tagName.toLowerCase()).toLowerCase();
                      const inputId = (input.id || '').toLowerCase();
                      let isKeyField = false;

                      if (keyInputTypes.includes(inputType)) {
                        isKeyField = true;
                      } else {
                        for (const keyNamePart of keyInputNames) {
                          if (inputName.includes(keyNamePart) || inputId.includes(keyNamePart)) {
                            isKeyField = true;
                            break;
                          }
                        }
                      }
                      
                      // Always consider submit buttons as key fields
                      if (inputType === 'submit' || (input.tagName.toLowerCase() === 'button' && input.type === 'submit')) {
                        isKeyField = true;
                      }

                      if (isKeyField) {
                        const fieldSummary = { 
                            name: input.name || null, 
                            type: inputType, 
                            id: input.id || null,
                            value: input.value || null, // Capture value for some input types
                            placeholder: input.placeholder || null // Capture placeholder
                        };
                        if (input.tagName.toLowerCase() === 'button' || inputType === 'submit') {
                          fieldSummary.text = input.textContent ? input.textContent.trim() : (input.value || '');
                        }
                        // For select, capture options if desired (can be verbose)
                        // if (inputType === 'select-one' || inputType === 'select-multiple') {
                        //   fieldSummary.options = Array.from(input.options).map(opt => ({value: opt.value, text: opt.text}));
                        // }
                        formDetails.input_fields_summary.push(fieldSummary);
                      }
                    });
                    return formDetails;
                  });
                }
                """
                try:
                    forms_data = page.evaluate(js_get_forms_script)
                    if forms_data:
                        conversion_funnel_effectiveness["forms_analysis"] = forms_data
                        # print(f"    Found {len(forms_data)} forms using page.evaluate().") # Optional debug
                    # else: # Optional debug
                        # print(f"    No forms found using page.evaluate().")
                except Exception as e_form:
                    print(f"    Error during form analysis with page.evaluate(): {e_form}")
                    # conversion_funnel_effectiveness["forms_analysis"] will remain empty or you can add an error entry
                    conversion_funnel_effectiveness["forms_analysis"].append({"error": f"Form analysis failed: {str(e_form)}"})
                # --- Attempt to find forms within iframes ---
                # print(f"    DEBUG: Starting iframe analysis for {current_url}...") # Keep this commented for now
                iframes = page.frames[1:] 

                if not iframes:
                    # print(f"    DEBUG: No iframes found on {current_url}.") # Keep this commented
                    pass 
                else:
                    print(f"    INFO: Found {len(iframes)} iframe(s) on {current_url}. Analyzing relevant ones...") # Changed to INFO and summarized
                    processed_iframes_count = 0
                    forms_found_in_iframes_count = 0

                    for i, frame_handler in enumerate(iframes):
                        iframe_name_str = f"'{frame_handler.name}'" if frame_handler.name else "N/A"
                        iframe_url_str = f"'{frame_handler.url}'"
                        
                        # Optional: print only if processing an iframe, not for every single one
                        # print(f"      DEBUG: Considering iframe {i+1} - Name: {iframe_name_str}, URL: {iframe_url_str}")
                        
                        if frame_handler.is_detached():
                            # print(f"        DEBUG: Skipping detached iframe {i+1}.")
                            continue 

                        if not frame_handler.url or frame_handler.url == "about:blank":
                            # print(f"        DEBUG: Skipping iframe {i+1} (Name: {iframe_name_str}) due to blank or no URL (URL: {iframe_url_str}).")
                            continue
                        
                        processed_iframes_count +=1
                        try:
                            # print(f"        DEBUG: Attempting to evaluate js_get_forms_script in iframe {i+1} (URL: {iframe_url_str})")
                            iframe_forms_data_raw = frame_handler.evaluate(js_get_forms_script) 
                            # print(f"        DEBUG: Raw forms data from iframe {i+1} (URL: {iframe_url_str}): {iframe_forms_data_raw}")

                            if iframe_forms_data_raw and isinstance(iframe_forms_data_raw, list):
                                if len(iframe_forms_data_raw) > 0:
                                    forms_found_in_iframes_count += len(iframe_forms_data_raw)
                                    # print(f"          DEBUG: Found {len(iframe_forms_data_raw)} form object(s) in iframe {i+1} (URL: {iframe_url_str}).")
                                    for form_item in iframe_forms_data_raw:
                                        form_item["found_in_iframe"] = True
                                        form_item["iframe_url"] = frame_handler.url 
                                        form_item["iframe_name"] = frame_handler.name if frame_handler.name else None
                                        conversion_funnel_effectiveness["forms_analysis"].append(form_item)
                                # else:
                                    # print(f"          DEBUG: Empty list returned (no forms found) from iframe {i+1} (URL: {iframe_url_str}).")
                            # else:
                                # print(f"          DEBUG: No form objects returned (or unexpected data type: {type(iframe_forms_data_raw).__name__}) from iframe {i+1} (URL: {iframe_url_str}).")
                        
                        except Exception as e_iframe:
                            error_type_iframe = type(e_iframe).__name__
                            current_iframe_url_for_error = "N/A"
                            current_iframe_name_for_error = "N/A"
                            try:
                                current_iframe_url_for_error = frame_handler.url if not frame_handler.is_detached() else "detached"
                                current_iframe_name_for_error = frame_handler.name if not frame_handler.is_detached() and frame_handler.name else "N/A"
                            except: pass 
                            error_message_iframe = f"Error evaluating forms in iframe {i+1} (URL: {current_iframe_url_for_error}, Name: {current_iframe_name_for_error}): {error_type_iframe} - {str(e_iframe)}"
                            print(f"    WARNING: {error_message_iframe}") # Changed to WARNING, this is important to keep
                    
                    if processed_iframes_count > 0:
                        print(f"    INFO: Attempted to analyze {processed_iframes_count} relevant iframe(s). Found {forms_found_in_iframes_count} forms within them.")
                    elif len(iframes) > 0 : # All iframes were skipped
                        print(f"    INFO: All {len(iframes)} found iframe(s) were skipped (e.g. detached or about:blank).")
                # print(f"Conversion/Funnel clues: {conversion_funnel_effectiveness}") # Optional debug

                # ===================================================================================
                # === CORE ANALYSIS AREA 5: Competitive Posture & Strategic Tests (Planned) ===
                # ===================================================================================
                # This area uncovers client-side evidence of iteration, differentiation, or focus. [cite: 1, 13]
                # (Code for this section to be added here)
                # E.g., identify A/B testing clues, feature flags, unique MarTech usage

                competitive_strategic_clues = {
                    "ab_testing_tools_present": [],
                    "feature_flags_systems_identified": set(),
                    "advanced_martech_indicators": [] # e.g., CDPs
                }

                # 1. A/B Testing Tool Presence
                # Check from already identified MarTech tools (from identified_martech_on_page)
                known_ab_testing_tools = ["Optimizely"] # Add other known A/B tools if in MARTECH_SIGNATURES
                for tool in identified_martech_on_page: # This set is populated in MarTech sections
                    if tool in known_ab_testing_tools:
                        competitive_strategic_clues["ab_testing_tools_present"].append(tool)

                # 2. Feature Flag Systems Identification
                # Check script tags (src and inline content)
                for script_tag in script_tags: # script_tags is already defined
                    script_content_to_check = ""
                    if script_tag.get("src"):
                        script_content_to_check += script_tag.get("src").lower() + " " # Lowercase for case-insensitive match
                    script_content_to_check += script_tag.string.lower() if script_tag.string else ""

                    if script_content_to_check.strip():
                        for tool_name, patterns in FEATURE_FLAG_SIGNATURES.items():
                            for pattern in patterns:
                                try:
                                    if re.search(pattern, script_content_to_check, re.IGNORECASE):
                                        competitive_strategic_clues["feature_flags_systems_identified"].add(tool_name)
                                except re.error:
                                    pass
                
                # Check Network Requests (some SDKs might load resources this way)
                for req_url in requests_log: # requests_log is defined from page.on("request")
                    req_url_lower = req_url.lower()
                    for tool_name, patterns in FEATURE_FLAG_SIGNATURES.items():
                        for pattern in patterns:
                            if r"\." in pattern or r"/" in pattern or "http" in pattern.lower(): # URL-like patterns
                                try:
                                    if re.search(pattern, req_url_lower, re.IGNORECASE):
                                        competitive_strategic_clues["feature_flags_systems_identified"].add(tool_name)
                                except re.error:
                                    pass
                
                # Check full HTML for global JS variables (basic check)
                html_content_lower = html_content.lower() # Search in lowercase
                for tool_name, patterns in FEATURE_FLAG_SIGNATURES.items():
                    if "window." in "".join(patterns).lower(): # Only check patterns explicitly looking for window objects
                        for pattern in patterns:
                             if "window." in pattern.lower():
                                try:
                                    js_object_pattern = pattern.replace(r"window.", r"window\.") # Escape dot for regex
                                    if re.search(js_object_pattern, html_content_lower, re.IGNORECASE):
                                        competitive_strategic_clues["feature_flags_systems_identified"].add(tool_name)
                                except re.error:
                                    pass

                competitive_strategic_clues["feature_flags_systems_identified"] = sorted(list(competitive_strategic_clues["feature_flags_systems_identified"]))

                # 3. Advanced MarTech Indicators
                # Example: Check for CDPs like Segment from identified_martech_on_page
                if "Segment" in identified_martech_on_page: # Segment is a key in MARTECH_SIGNATURES
                    competitive_strategic_clues["advanced_martech_indicators"].append("Segment (CDP)")
                # Add other advanced tool checks here as needed

                # print(f"Competitive/Strategic clues: {competitive_strategic_clues}") # Optional debug

                # -----------------------------------------------------------------
                # --- Compile Extracted Information for this URL for JSON Output ---
                # -----------------------------------------------------------------
                page_fetch_time_utc = datetime.now(timezone.utc)
                page_title_val = page.title() # Capture page title separately

                # This data_for_json will be the content of the "data": {} field in the JSON
                data_for_json = {
                    "marketing_technology_data_foundation": {
                        "martech_identified": sorted(list(identified_martech_on_page)),
                        "dataLayer_summary": { # Standardizing dataLayer output
                            "exists": data_layer_exists_on_page,
                            "total_pushes": data_layer_content_summary.get("total_pushes") if data_layer_exists_on_page and data_layer_content_summary else None,
                            "sample_pushes_structure": data_layer_content_summary.get("sample_pushes_structure") if data_layer_exists_on_page and data_layer_content_summary else None,
                            "error": data_layer_content_summary.get("error") if data_layer_content_summary and "error" in data_layer_content_summary else None
                        },
                        "cookie_consent_tools_identified": sorted(list(identified_cookie_consent_tools))
                    },
                    "organic_presence_content_signals": organic_signals, # organic_signals is already a dict
                    "user_experience_performance_clues": ux_performance_clues, # ux_performance_clues is already a dict
                    "conversion_funnel_effectiveness": conversion_funnel_effectiveness, # this is already a dict
                    "competitive_posture_strategic_tests": competitive_strategic_clues # this is already a dict
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
                page.close()

            except Exception as e:
                print(f"Could not process {current_url}. Error: {e}")
                page_fetch_time_utc = datetime.now(timezone.utc) # Capture error time
                url_result_object = {
                    "url": current_url,
                    "fetch_status": "error",
                    "error_details": str(e),
                    "fetch_timestamp_utc": page_fetch_time_utc.isoformat(),
                    "page_title": None,
                    "data": None # Or provide a default empty structure for "data" if preferred
                }
                processed_urls_results_list.append(url_result_object)
                failed_fetches += 1
                # Ensure page is closed if it was opened before the error
                if 'page' in locals() and page and not page.is_closed():
                    page.close()
            time.sleep(1)

        # --- End of URL Processing Loop ---

        # ---------------------------------------------------------------------
        # --- FINAL OUTPUT SECTION ---
        # ---------------------------------------------------------------------
        # --- End of URL Processing Loop ---

        # Construct the final JSON object
        final_json_output = {
            "collection_metadata": {
                "collector_version": "1.0.0", # You can manage this version string
                "collection_timestamp_utc": collection_start_time_utc.isoformat(),
                 "total_urls_processed": len(urls_to_process), # MODIFIED HERE
                "total_urls_successful": successful_fetches,
                "total_urls_failed": failed_fetches
            },
            "url_analysis_results": processed_urls_results_list
        }

        # Write the JSON output to a file
        # Generate output filename based on execution mode:
        # - Single URL: output/deepstack_output-{domain}.json 
        # - Batch mode: output/deepstack_output.json
        
        # Create output directory if it doesn't exist
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}/")
        
        if args.url:
            # Single URL mode - extract domain name for filename
            parsed_url = urlparse(args.url)
            # Remove www. prefix and replace colons with underscores for ports
            domain = parsed_url.netloc.replace('www.', '').replace(':', '_')
            output_filename = os.path.join(output_dir, f"deepstack_output-{domain}.json")
        else:
            # Batch mode - use generic filename
            output_filename = os.path.join(output_dir, "deepstack_output.json")
        try:
            with open(output_filename, 'w') as f:
                json.dump(final_json_output, f, indent=2) # indent=2 for pretty-printing
            print(f"\nResults successfully saved to {output_filename}")
        except IOError as e:
            print(f"\nError writing results to JSON file {output_filename}: {e}")
        except TypeError as e:
            print(f"\nError serializing data to JSON: {e}. Check data structures.")

        # The existing console output loop can remain for immediate feedback if desired,
        # or you might choose to simplify or remove it now that data is saved to a file.
        print("\n--- Console Output Summary ---") # Optional: Changed heading for clarity
        # (The line "print("\n--- Collection Finished ---")" or "print("\n--- Console Output Summary ---")" should be right above this new loop)

        for result_item in processed_urls_results_list: # Iterate through the new list
            print(f"\nData for {result_item['url']}:") # Access URL from result_item

            if result_item['fetch_status'] == "error": # Check fetch_status
                print(f"  Error: {result_item['error_details']}")
                continue # Skip to next URL if there was a fetch error

            # If successful, 'data_payload' is the dictionary holding all the categorized data
            data_payload = result_item.get('data')
            if not data_payload: 
                print("  Error: No data payload found for this URL despite successful fetch.")
                continue

            print(f"  Page Title: {result_item.get('page_title', 'Not found')}")

            # Marketing Technology & Data Foundation
            mt_df = data_payload.get('marketing_technology_data_foundation', {})
            print(f"  Marketing Technology & Data Foundation:")
            print(f"    MarTech Identified: {mt_df.get('martech_identified', 'None found')}")
            
            dl_summary_data = mt_df.get('dataLayer_summary', {}) 
            print(f"    DataLayer Exists: {dl_summary_data.get('exists', False)}")
            if dl_summary_data.get('exists'):
                if dl_summary_data.get('error'):
                     print(f"    DataLayer Summary Error: {dl_summary_data.get('error')}")
                else:
                    print(f"    DataLayer Summary - Total Pushes: {dl_summary_data.get('total_pushes', 'N/A')}")
                    if dl_summary_data.get('sample_pushes_structure'):
                        print("    DataLayer Summary - Sample Pushes Structure:")
                        for sample_push in dl_summary_data.get('sample_pushes_structure', []):
                            print(f"      {sample_push}")
            elif dl_summary_data.get('error'): 
                 print(f"    DataLayer Summary Error: {dl_summary_data.get('error')}")
            print(f"    Cookie Consent Tools: {mt_df.get('cookie_consent_tools_identified', 'None found')}")

            # Organic Presence & Content Signals
            ops_signals = data_payload.get('organic_presence_content_signals', {})
            if ops_signals: 
                print(f"  Organic Presence & Content Signals:")
                print(f"    Meta Title: {ops_signals.get('meta_title', 'Not found')}")
                meta_desc = ops_signals.get('meta_description')
                print(f"    Meta Description: {meta_desc[:100] + '...' if meta_desc and len(meta_desc) > 100 else meta_desc if meta_desc else 'Not found'}")
                print(f"    Meta Keywords: {ops_signals.get('meta_keywords', 'Not found')}")
                print(f"    Canonical URL: {ops_signals.get('canonical_url', 'Not found')}")
                print(f"    Robots Meta: {ops_signals.get('robots_meta', 'Not found')}")
                print(f"    H1 Tags: {ops_signals.get('h1_tags', [])}")
                print(f"    H2 Tags (count): {len(ops_signals.get('h2_tags', []))}")
                print(f"    JSON-LD Scripts (count): {len(ops_signals.get('json_ld_scripts', []))}")
                print(f"    Hreflang Tags (count): {len(ops_signals.get('hreflang_tags', []))}")

            # User Experience & Website Performance (Client-Side Clues)
            ux_perf = data_payload.get('user_experience_performance_clues', {})
            if ux_perf:
                print(f"  User Experience & Website Performance Clues:")
                print(f"    Viewport Meta Content: {ux_perf.get('viewport_meta_content', 'Not found')}")
                print(f"    Identified CDN Domains: {ux_perf.get('identified_cdn_domains', 'None found')}")
                lazy_info = ux_perf.get('lazy_loading_images', {})
                print(f"    Lazy Loading Images: {lazy_info.get('with_lazy_loading', 0)} found with 'loading=\"lazy\"' out of {lazy_info.get('sampled_images', 0)} sampled")
                alt_info = ux_perf.get('alt_text_images', {})
                print(f"    Image Alt Texts: {alt_info.get('with_alt_text', 0)} found with 'alt' attribute out of {alt_info.get('sampled_images', 0)} sampled")

            # Conversion & Funnel Effectiveness - Simplified console output
            conv_funnel = data_payload.get('conversion_funnel_effectiveness', {})
            print(f"  Conversion & Funnel Effectiveness:")
            print(f"    Identified Conversion Events: {conv_funnel.get('identified_conversion_events', 'None detected or empty')}")
            print(f"    Forms Analyzed (count): {len(conv_funnel.get('forms_analysis', []))}")

            # Competitive Posture & Strategic Tests - Simplified console output
            comp_strat = data_payload.get('competitive_posture_strategic_tests', {})
            print(f"  Competitive Posture & Strategic Tests:")
            print(f"    A/B Testing Tools Identified: {comp_strat.get('ab_testing_tools_present', 'None detected')}")
            print(f"    Feature Flag Systems Identified: {comp_strat.get('feature_flags_systems_identified', 'None detected')}")
            print(f"    Advanced MarTech Indicators: {comp_strat.get('advanced_martech_indicators', 'None detected')}")

        print("\nAttempting to close browser resources...")
        try:
            # Attempt to close context
            if 'context' in locals() and context:
                print("Closing browser context...")
                context.close()
                print("Browser context successfully closed.")
            else:
                print("Browser context object not available or already handled.")

            # Attempt to close browser
            if 'browser' in locals() and browser:
                if browser.is_connected(): # Correct check for browser
                    print("Closing browser...")
                    browser.close()
                    print("Browser successfully closed.")
                else:
                    print("Browser was already disconnected or closed.")
            else:
                print("Browser object not available.")
                
        except Exception as e_close:
            print(f"Error during browser/context close: {type(e_close).__name__} - {e_close}")
            # More specific checks for common Playwright closure issues
            if "Target page, context or browser has been closed" in str(e_close):
                 print("Indicates that a resource was likely already closed when an operation was attempted on it.")
            elif "Event loop is closed" in str(e_close) or "Browser has been closed" in str(e_close):
                print("Playwright's communication channel was already terminated or browser was already closed.")
            else:
                print("The browser or context might have been in an unstable state during closure.")
        
        # The original "print("Browser closed.")" is now part of the try block logic.
# --- Script Execution ---
if __name__ == "__main__":
    main()