# ABA Authorization Agent — MVP Prototype

Extracts clinical data from ABA progress report PDFs and generates payor-specific reauthorization narratives (Anthem Blue Cross CA) for BCBA review.

## Quick Start

```bash
cd aba-auth-agent

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your Anthropic API key

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Workflow

1. **Upload** — Upload an ABA progress report PDF (CentralReach, Catalyst, Rethink, or any standard format)
2. **Review Data** — Verify and edit the extracted clinical data (demographics, assessments, skill targets, behavior data, hours utilization)
3. **Generate** — Create the Anthem Blue Cross CA reauthorization narrative with AI, then review/edit each section
4. **Export** — Download as a Word document (.docx) for submission

## Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/) with access to Claude Sonnet

## Project Structure

```
aba-auth-agent/
├── app.py                     # Streamlit entry point
├── pages/                     # Streamlit multi-page UI
│   ├── 1_Upload.py            # PDF upload + extraction
│   ├── 2_Review_Data.py       # Extracted data review/edit
│   ├── 3_Generate.py          # Narrative generation + BCBA review
│   └── 4_Export.py            # DOCX export
├── pipeline/                  # Core processing modules
│   ├── classifier.py          # PDF type detection (native vs scanned)
│   ├── extractor.py           # Claude API extraction → structured JSON
│   ├── validator.py           # Completeness checker (Anthem requirements)
│   ├── generator.py           # Claude API narrative generation
│   └── exporter.py            # DOCX rendering via docxtpl
├── schemas/                   # Pydantic data models
│   ├── clinical_data.py       # Extracted data schema
│   └── narrative.py           # Narrative section schema
├── prompts/                   # System prompts and few-shot examples
├── templates/                 # Word document templates
└── tests/                     # Test suite
```

## Running Tests

```bash
source .venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

Tests validate Pydantic schemas and the completeness validator. Extraction and generation tests require a valid `ANTHROPIC_API_KEY`.

## HIPAA Notice

Use **only de-identified** progress reports during testing. Remove all 18 HIPAA identifiers before processing through the Claude API. For production use, deploy via AWS Bedrock with a signed BAA.
