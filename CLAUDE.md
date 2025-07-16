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

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/petergiordano/deepstack.git
   cd deepstack
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

### Key Dependencies

- `playwright==1.40.0` - Web automation framework
- `playwright-stealth==1.0.6` - Stealth mode for avoiding detection
- `beautifulsoup4==4.12.2` - HTML parsing library
- Standard library: `json`, `datetime`, `re`, `random`, `time`, `argparse`

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

## MEARA Agent Documentation

The `meara_agent_docs/` folder contains reference documentation for building AI agents that consume DeepStack collector output for marketing analysis:

- **project_system_Instructions.md**: System instructions for B2B SaaS Marketing Analysis AI agents
- **instruct_marketing_analysis.md**: Detailed methodology and output formatting requirements
- **marketing_analysis_methodology.md**: 9-step analysis framework
- **marketing_analysis_rubrics.md**: Evaluation criteria for marketing dimensions
- **strategic_elements_framework.md**: Framework for strategic assessment
- **deep_research_prompt-meara-b2b-insights.md**: Prompts for deep research insights
- **Actual-Marketing-Analysis-Example-by-Maria-P.md**: Reference example of analysis output

These documents are used to build Claude Projects, Gemini Gems, ChatGPT Custom GPTs, and other AI agents that process DeepStack's raw JSON output into strategic marketing intelligence. They serve as reference material for improving the collector's data structure and ensuring it captures the signals needed for downstream analysis.

## Security Considerations

This tool is designed for legitimate security research and competitive analysis. It implements rate limiting, respects robots.txt patterns in URL filtering, and includes stealth capabilities to avoid triggering anti-bot measures.