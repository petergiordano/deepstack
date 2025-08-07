# DeepStack Collector

A Python-based web scraping and analysis tool that analyzes websites for marketing technology (MarTech) stacks, conversion tracking, and competitive intelligence.

## Overview

DeepStack Collector is the first step in a comprehensive three-step marketing analysis pipeline that transforms raw website data into strategic marketing intelligence. It uses Playwright for web automation and BeautifulSoup for HTML parsing to detect and analyze various marketing technologies and website features.

## Features

### Core Analysis Areas

1. **Marketing Technology & Data Foundation**
   - Identifies MarTech tools (Google Analytics, HubSpot, Meta Pixel, etc.)
   - Extracts dataLayer content
   - Detects cookie consent mechanisms

2. **Organic Presence & Content Signals**
   - SEO metadata extraction
   - Heading structure analysis
   - Structured data detection
   - Canonical URL identification

3. **User Experience & Performance Clues**
   - Viewport settings analysis
   - CDN usage detection
   - Lazy loading implementation
   - Image alt text coverage

4. **Conversion & Funnel Effectiveness**
   - Conversion event detection
   - Form analysis (including iframe forms)
   - Call-to-action identification

5. **Competitive Posture & Strategic Tests**
   - A/B testing tool detection
   - Feature flag system identification

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/petergiordano/deepstack.git
   cd deepstack
   ```

2. **Create a virtual environment:**

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

5. **Create output directory:**

   ```bash
   mkdir -p output
   ```

## Usage

DeepStack Collector can be used in two ways: through a **web interface** (recommended) or via **command line**.

### Web Interface (Recommended)

The easiest way to use DeepStack Collector is through the local web interface:

1. **Install dependencies** (if not already done):

   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the web server**:

   ```bash
   python app.py
   ```

3. **Open your browser** to `http://localhost:5000`

4. **Use the interface** to:
   - Analyze single URLs
   - Analyze multiple URLs (paste or upload file)
   - View results in real-time
   - Download JSON results

### Command Line Interface

For programmatic use or batch processing:

#### Single URL Analysis

```bash
python3 deepstack.py -u https://example.com
```

Output: `output/deepstack_output-example.com.json`

#### Batch Analysis

1. Create `urls_to_analyze.txt` in the project root:

   ```text
   https://example.com
   https://another-site.com
   # Comments start with #
   ```

2. Run batch analysis:

   ```bash
   python3 deepstack.py
   ```

Output: `output/deepstack_output.json`

#### Alternative Execution Methods

Using the shell script:

```bash
./deepstack.sh -u https://example.com
```

Direct execution:

```bash
python3 src/deepstack_collector.py -u https://example.com
```

## Output Format

The tool generates JSON output with the following structure:

```json
{
  "metadata": {
    "analysis_timestamp": "2024-01-01T12:00:00Z",
    "tool_version": "DeepStack Collector v1.0",
    "total_urls_analyzed": 1
  },
  "results": [
    {
      "url": "https://example.com",
      "timestamp": "2024-01-01T12:00:00Z",
      "marketing_tech_data_foundation": {
        "detected_martech_tools": ["Google Analytics", "Meta Pixel"],
        "dataLayer_content": {...},
        "cookie_consent_tools": ["OneTrust"]
      },
      "organic_presence_content_signals": {
        "seo_metadata": {...},
        "heading_structure": {...},
        "structured_data": [...]
      },
      "user_experience_performance": {
        "viewport_settings": "width=device-width, initial-scale=1",
        "cdn_usage": ["Cloudflare"],
        "lazy_loading": true
      },
      "conversion_funnel_effectiveness": {
        "conversion_events": [...],
        "forms_analysis": {...}
      },
      "competitive_posture_strategic_tests": {
        "ab_testing_tools": ["Optimizely"],
        "feature_flags": []
      }
    }
  ]
}
```

## Three-Step Analysis Pipeline

DeepStack Collector is part of a comprehensive analysis pipeline:

1. **DeepStack Collector** (This Tool)
   - Raw data collection and technical signal detection
   - Output: JSON files with structured technical data

2. **DeepStack Analysis Gem** (Gemini AI Agent)
   - Interprets technical signals from DeepStack output
   - Transforms raw data into structured insights
   - Documentation: `docs/deepstack_analysis_agent_docs/`

3. **Marketing Effectiveness Analysis Agent (MEARA)**
   - Generates strategic marketing recommendations
   - Creates executive-ready reports
   - Documentation: `docs/meara_agent_docs/`

## Project Structure

```text
deepstack/
├── deepstack.py                   # Python launcher script
├── deepstack.sh                   # Shell launcher script
├── src/                           # Source code
│   └── deepstack_collector.py     # Main analysis script
├── docs/                          # Documentation
│   ├── deepstack_analysis_agent_docs/
│   └── meara_agent_docs/
├── tools/                         # Utility scripts
├── output/                        # Analysis results
├── requirements.txt               # Python dependencies
├── CLAUDE.md                      # AI assistant instructions
└── README.md                      # This file
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Make sure you've activated the virtual environment:

   ```bash
   source venv/bin/activate
   ```

2. **Timeout errors**: Some websites may have protection or load slowly. Try:
   - Testing with a simpler site first
   - Checking if the site has Cloudflare protection
   - Increasing timeout in the script

3. **Playwright installation issues**: Ensure you've installed the browsers:

   ```bash
   playwright install chromium
   ```

## Security Considerations

This tool is designed for legitimate security research and competitive analysis. It:

- Implements rate limiting between requests
- Includes stealth capabilities to avoid anti-bot measures
- Respects website terms of service

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions, please open an issue on the [GitHub repository](https://github.com/petergiordano/deepstack/issues).
