# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based web scraping and analysis tool called "DeepStack Collector" that analyzes websites for marketing technology (MarTech) stacks, conversion tracking, and competitive intelligence. The tool uses Playwright for web automation and BeautifulSoup for HTML parsing.

## Core Architecture

The project consists of a single main script (`deepstack_collector.py`) that performs comprehensive website analysis across five key areas:

1. **Marketing Technology & Data Foundation**: Identifies MarTech tools (Google Analytics, HubSpot, Meta Pixel, etc.), dataLayer content, and cookie consent mechanisms
2. **Organic Presence & Content Signals**: Extracts SEO-related metadata, heading tags, structured data, and canonical URLs
3. **User Experience & Performance Clues**: Analyzes viewport settings, CDN usage, lazy loading, and image alt text
4. **Conversion & Funnel Effectiveness**: Detects conversion events and analyzes forms (including those in iframes)
5. **Competitive Posture & Strategic Tests**: Identifies A/B testing tools and feature flag systems

## Key Dependencies

- `playwright` with `playwright-stealth` for browser automation
- `beautifulsoup4` for HTML parsing  
- `argparse` for command-line interface
- Standard library: `json`, `datetime`, `re`, `random`, `time`

## Running the Tool

### Single URL Analysis
```bash
python3 deepstack_collector.py -u https://example.com
```

### Batch Analysis
```bash
python3 deepstack_collector.py
```
This reads URLs from `urls_to_analyze.txt` (one URL per line, comments start with #)

## Input/Output Files

- **Input**: `urls_to_analyze.txt` - Contains URLs to analyze (created automatically if missing)
- **Output**: `deepstack_collector_output.json` - Structured analysis results with metadata

## Detection Signatures

The tool uses regex pattern matching to identify technologies through:
- Script tag sources and inline content
- Network request URLs
- HTML content patterns
- JavaScript object detection

Key signature dictionaries:
- `MARTECH_SIGNATURES`: Marketing technology tools
- `COOKIE_CONSENT_SIGNATURES`: Cookie consent management platforms
- `FEATURE_FLAG_SIGNATURES`: Feature flag and A/B testing systems
- `CONVERSION_EVENT_SIGNATURES`: Conversion tracking events
- `CDN_DOMAIN_PATTERNS`: Content delivery networks

## Browser Configuration

The tool uses Chromium with stealth mode and specific launch arguments to avoid detection:
- Headless mode configurable (`headless=False` for debugging)
- Custom user agent and viewport settings
- Cloudflare challenge detection and handling
- Random delays between requests (2-5 seconds)

## Special Features

- **Cloudflare Challenge Handling**: Automatically detects and waits for Cloudflare protection to resolve
- **Iframe Form Analysis**: Analyzes forms within iframes using JavaScript evaluation
- **DataLayer Extraction**: Captures Google Tag Manager dataLayer content structure
- **Dynamic Content Support**: Uses `page.evaluate()` for JavaScript-heavy sites

## Error Handling

The tool includes comprehensive error handling for:
- Network timeouts and connection issues
- Cloudflare protection challenges
- Malformed HTML and JavaScript
- Missing or inaccessible iframes
- JSON serialization errors

## Security Considerations

This tool is designed for legitimate security research and competitive analysis. It implements rate limiting, respects robots.txt patterns in URL filtering, and includes stealth capabilities to avoid triggering anti-bot measures.