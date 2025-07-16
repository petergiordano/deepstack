# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based web scraping and analysis tool called "DeepStack Collector" that analyzes websites for marketing technology (MarTech) stacks, conversion tracking, and competitive intelligence. The tool uses Playwright for web automation and BeautifulSoup for HTML parsing.

## Three-Step Analysis Pipeline

DeepStack operates as part of a comprehensive three-step analysis pipeline:

### Step 1: DeepStack Collector (This Tool)
- **Purpose**: Raw data collection and technical signal detection
- **Output**: JSON files with structured technical data across 5 core areas:
  - Marketing Technology & Data Foundation
  - Organic Presence & Content Signals  
  - User Experience & Performance Clues
  - Conversion & Funnel Effectiveness
  - Competitive Posture & Strategic Tests

### Step 2: DeepStack Analysis Gem (Gemini AI Agent)
- **Purpose**: Interpret and analyze technical signals from DeepStack output
- **Documentation**: `docs/deepstack_analysis_agent_docs/`
- **Process**: Transforms raw technical data into structured insights across three levels:
  - **L1 Signals**: Basic technical detection and categorization
  - **L2 Snapshot**: Contextual analysis and pattern recognition
  - **L3 Ground Truth**: Strategic interpretation and recommendations
- **Output**: Structured analysis ready for marketing strategy development

### Step 3: Marketing Effectiveness Analysis Agent (MEARA)
- **Purpose**: Generate strategic marketing recommendations and reports
- **Documentation**: `docs/meara_agent_docs/`
- **Process**: Uses DeepStack Analysis Gem output to create comprehensive marketing effectiveness reports
- **Output**: Executive-ready marketing analysis with actionable recommendations

This pipeline transforms raw website data into strategic marketing intelligence through progressive analysis and interpretation.

## Project Structure

```text
deepstack/
├── deepstack.py                   # Python launcher script (recommended)
├── deepstack.sh                   # Shell launcher script
├── src/                           # Source code
│   └── deepstack_collector.py     # Main analysis script
├── docs/                          # Documentation and visualizations
│   ├── deepstack-workflow-architecture.md
│   ├── deepstack_scale_gtm_sankey_diagram.html
│   ├── deepstack_analysis_pipeline_visualization.html
│   ├── meara_agent_docs/          # MEARA marketing analysis AI agent docs
│   └── deepstack_analysis_agent_docs/ # DeepStack analysis AI agent docs
├── tools/                         # Utility scripts
│   ├── clean_markdown.py
│   └── markdown_cleaner.py
├── backup_meara_docs/             # Backup of original documentation
├── reference/                     # Reference configurations
├── requirements.txt               # Python dependencies
├── CLAUDE.md                      # This documentation file
└── *.txt, *.json                 # Input/output files
```

## Core Architecture

The project consists of a single main script (`src/deepstack_collector.py`) that performs comprehensive website analysis across five key areas:

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

You can run the DeepStack Collector from the root directory using either of the provided launcher scripts:

### Using Python Launcher (Recommended)

**Single URL Analysis:**

```bash
python3 deepstack.py -u https://example.com
# Output: output/deepstack_output-example.com.json

python3 deepstack.py -u https://www.google.com
# Output: output/deepstack_output-google.com.json

python3 deepstack.py -u https://subdomain.example.com:8080
# Output: output/deepstack_output-subdomain.example.com_8080.json
```

**Batch Analysis:**

```bash
python3 deepstack.py
# Output: output/deepstack_output.json (reads from urls_to_analyze.txt)
```

### Using Shell Launcher

**Single URL Analysis:**

```bash
./deepstack.sh -u https://example.com
# Output: output/deepstack_output-example.com.json

./deepstack.sh -u https://www.google.com
# Output: output/deepstack_output-google.com.json

./deepstack.sh -u https://subdomain.example.com:8080
# Output: output/deepstack_output-subdomain.example.com_8080.json
```

**Batch Analysis:**

```bash
./deepstack.sh
# Output: output/deepstack_output.json (reads from urls_to_analyze.txt)
```

### Direct Execution

You can also run the script directly from the src directory:

**Single URL Analysis:**

```bash
python3 src/deepstack_collector.py -u https://example.com
```

**Batch Analysis:**

```bash
python3 src/deepstack_collector.py
```

**Note:** Batch analysis reads URLs from `urls_to_analyze.txt` (one URL per line, comments start with #)

## Input/Output Files

- **Input**: `urls_to_analyze.txt` - Contains URLs to analyze (created automatically if missing)
- **Output**: All output files are automatically saved to the `output/` directory
  - **Single URL mode**: `output/deepstack_output-{domain}.json` (e.g., `output/deepstack_output-example.com.json`)
    - Automatically extracts domain name from URL, removes `www.` prefix
    - Replaces colons with underscores for ports (e.g., `output/deepstack_output-example.com_8080.json`)
  - **Batch mode**: `output/deepstack_output.json` - Structured analysis results with metadata

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

## AI Agent Documentation

The `docs/` directory contains documentation for building the two AI agents in the analysis pipeline:

### Step 2: DeepStack Analysis Agent Documentation (`docs/deepstack_analysis_agent_docs/`)

Documentation for building **Gemini AI agents** that interpret DeepStack's raw technical output:

- **System_Instructions_DeepStack_Analysis_Gem.md**: Core system instructions for DeepStack analysis agents
- **Instruct_DeepStack_L1_Signals.md**: L1 signal detection and interpretation instructions
- **Instruct_DeepStack_L2_Snapshot.md**: L2 snapshot analysis methodology
- **Instruct_DeepStack_L3_GroundTruth.md**: L3 ground truth analysis framework
- **_README-DeepStack_Analysis_Gem.md**: Overview and setup guide for DeepStack analysis gems

**Purpose**: These agents consume DeepStack Collector's raw JSON output and transform technical signals into structured insights across three progressive analysis levels (L1→L2→L3).

### Step 3: MEARA Agent Documentation (`docs/meara_agent_docs/`)

Documentation for building **marketing effectiveness analysis agents** that generate strategic reports:

- **project_system_Instructions.md**: System instructions for B2B SaaS Marketing Analysis AI agents
- **instruct_marketing_analysis.md**: Detailed methodology and output formatting requirements
- **marketing_analysis_methodology.md**: 9-step analysis framework
- **marketing_analysis_rubrics.md**: Evaluation criteria for marketing dimensions
- **strategic_elements_framework.md**: Framework for strategic assessment
- **deep_research_prompt-meara-b2b-insights.md**: Prompts for deep research insights
- **Actual-Marketing-Analysis-Example-by-Maria-P.md**: Reference example of analysis output

**Purpose**: These agents consume the structured insights from DeepStack Analysis Gems and generate comprehensive marketing effectiveness reports with actionable recommendations.

### Pipeline Integration

1. **DeepStack Collector** → Raw technical data (JSON)
2. **DeepStack Analysis Gem** → Structured insights and interpretations  
3. **MEARA Agent** → Strategic marketing recommendations and reports

These documents serve as reference material for building Claude Projects, Gemini Gems, ChatGPT Custom GPTs, and other AI agents that form the complete analysis pipeline.

### Workflow Documentation and Visualizations

The `docs/` directory also contains workflow documentation and interactive visualizations:

- **deepstack-workflow-architecture.md**: Complete workflow documentation including L1/L2/L3 output levels and GTM intelligence pipeline
- **deepstack_scale_gtm_sankey_diagram.html**: Interactive Sankey diagram visualization of the GTM analysis pipeline  
- **deepstack_analysis_pipeline_visualization.html**: Visual representation of the analysis pipeline components

## Tools Directory

The `tools/` directory contains utility scripts for maintaining and processing project files:

- **clean_markdown.py**: Command-line interface for cleaning escaped markdown characters from Google Docs exports
- **markdown_cleaner.py**: Core cleaning function that removes backslash escapes from markdown formatting (headers, emphasis, lists, links, etc.)

These tools were used to clean the MEARA documentation files that were exported from Google Docs with escaped characters. The cleaning scripts can be run on individual files or in batch mode using shell commands.

### Usage Examples

Clean a single markdown file:

```bash
python3 tools/clean_markdown.py input.md -o output.md
```

Test cleaning without writing changes:

```bash
python3 tools/clean_markdown.py input.md --dry-run
```

Clean all markdown files in a directory:

```bash
find meara_agent_docs -name "*.md" -exec python3 tools/clean_markdown.py {} \;
```

## Security Considerations

This tool is designed for legitimate security research and competitive analysis. It implements rate limiting, respects robots.txt patterns in URL filtering, and includes stealth capabilities to avoid triggering anti-bot measures.
