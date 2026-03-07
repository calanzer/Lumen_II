# ABA Authorization Agent — MVP Prototype

Extracts clinical data from ABA progress report PDFs and generates payor-specific reauthorization narratives for BCBA review. Supports multiple payor templates (Anthem Blue Cross CA, Aetna, Optum, Blue Shield CA, Medi-Cal).

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
python -m streamlit run app.py
```

The app will open at `http://localhost:8501`.

**Default login:** username `bcba_reviewer`, password `changeme`

## Workflow

1. **Upload** — Upload an ABA progress report PDF (CentralReach, Catalyst, Rethink, or any standard format)
2. **Review Data** — Verify and edit the extracted clinical data (demographics, assessments, skill targets, behavior data, hours utilization)
3. **Generate** — Create the reauthorization narrative with AI, review source data side-by-side with generated text, and edit each section
4. **Export** — Select your payor template and download as a Word document (.docx) for submission

## Extraction Pipeline

```
PDF Upload -> PyMuPDF (classify native vs scanned)
           -> Claude Sonnet (extract to structured JSON)
           -> pdfplumber (cross-validate tables)
           -> Pydantic (enforce schema)
```

- **Prompt caching** on system prompts for ~90% cost savings on repeated calls
- **Post-generation validation** via Claude Haiku to cross-check quantitative claims
- **`@st.cache_data`** prevents redundant API calls on Streamlit page reruns

## Payor Templates

The Export page lets you select from multiple payor templates. Templates are `.docx` files with Jinja2 placeholders in the `templates/` directory. BCBAs can customize templates in Word without developer involvement.

| Payor | Template | Status |
|-------|----------|--------|
| Anthem Blue Cross CA | `anthem_reauth.docx` | Included |
| Aetna | `aetna_reauth.docx` | Auto-generated |
| Optum / UHC | `optum_reauth.docx` | Auto-generated |
| Blue Shield CA | `blue_shield_ca_reauth.docx` | Auto-generated |
| Medi-Cal | `medi_cal_reauth.docx` | Auto-generated |

To customize a template: replace the auto-generated file in `templates/` with your own `.docx` using the same `{{ placeholder }}` tags.

## Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/) with access to Claude Sonnet

## Project Structure

```
aba-auth-agent/
├── app.py                     # Streamlit entry point (with auth)
├── pages/                     # Streamlit multi-page UI
│   ├── 1_Upload.py            # PDF upload + extraction (cached)
│   ├── 2_Review_Data.py       # Extracted data review/edit
│   ├── 3_Generate.py          # Narrative generation + side-by-side BCBA review
│   └── 4_Export.py            # Payor template selector + DOCX export
├── pipeline/                  # Core processing modules
│   ├── classifier.py          # PDF type detection (native vs scanned)
│   ├── extractor.py           # Claude API extraction + pdfplumber validation
│   ├── validator.py           # Completeness checker (Anthem requirements)
│   ├── generator.py           # Claude API narrative generation + cross-validation
│   └── exporter.py            # Multi-payor DOCX rendering via docxtpl
├── schemas/                   # Pydantic data models
│   ├── clinical_data.py       # Extracted data schema (CPT + HCPCS codes)
│   └── narrative.py           # Narrative section schema
├── prompts/                   # System prompts and few-shot examples
├── templates/                 # Word document templates (one per payor)
└── tests/                     # Test suite
```

## Running Tests

```bash
source .venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

Tests validate Pydantic schemas and the completeness validator. Extraction and generation tests require a valid `ANTHROPIC_API_KEY`.

## Licensing Notes

- **PyMuPDF** uses AGPL-3.0, which requires a commercial license for proprietary SaaS distribution. For production, consider switching the classifier to use `pypdfium2` (Apache-2.0 license) as a drop-in alternative.
- **pdfplumber** (MIT), **docxtpl** (LGPL), **python-docx** (MIT) are permissively licensed.

## HIPAA Notice

Use **only de-identified** progress reports during testing. Remove all 18 HIPAA identifiers before processing through the Claude API. For production use, deploy via AWS Bedrock with a signed BAA.
