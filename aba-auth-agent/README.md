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

# Build the web app once (needs Node 20+)
(cd web && npm install && npm run build)

# Run it
.venv/bin/uvicorn api.main:app --port 8000
```

The app is at `http://localhost:8000`.

**Default login:** username `bcba_reviewer`, password `changeme` (stored hashed in `config/auth_config.yaml`, created on first run; change it before anyone else uses the app).

## Development

```bash
# Terminal 1: API (set ABA_LOCAL_NO_LOGIN=1 to skip sign-in on your own machine)
.venv/bin/uvicorn api.main:app --port 8000

# Terminal 2: frontend with hot reload
cd web && npm run dev          # http://localhost:5173
```

`ABA_LOCAL_NO_LOGIN=1` only applies to requests from this computer to `localhost`, and the sidebar shows a **Local** badge when it's active. Stack, design tokens, API routes, security notes and quality gates are in [docs/DESIGN.md](docs/DESIGN.md). The Streamlit app this replaced is in git history; what carried over is listed in [docs/PARITY.md](docs/PARITY.md).

## Workflow

1. **Import** — Drop an ABA progress report (PDF or Word; CentralReach, Catalyst, Rethink, or any standard format). The app reads it, finds or creates the client and period, drafts the narrative and cross-checks the numbers
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
- **Background jobs** run imports and narrative generation, so the browser polls instead of waiting on one long request

## Payor Templates

The Export screen lets you select from multiple payor templates. Templates are `.docx` files with Jinja2 placeholders in the `templates/` directory. BCBAs can customize templates in Word without developer involvement.

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
├── api/                       # FastAPI: login, clients, periods, imports, templates; serves web/dist
├── web/                       # React app (Vite, TypeScript, shadcn/ui, Tailwind v4)
├── auth_config.py             # Login file loader (config/auth_config.yaml)
├── data/                      # SQLite store
├── docs/                      # DESIGN.md, PARITY.md, deploy.md, payor_requirements.md
├── pipeline/                  # Core processing modules
│   ├── classifier.py          # PDF type detection (native vs scanned)
│   ├── extractor.py           # Claude API extraction + pdfplumber validation
│   ├── validator.py           # Completeness checker (Anthem requirements)
│   ├── generator.py           # Claude API narrative generation + cross-validation
│   ├── intake.py              # Client/period matching and import plan
│   ├── claim_check.py         # Number-aware cross-check of the narrative
│   ├── template_extractor.py  # Learns a payor's layout from a past report
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

cd web && npx vitest run && npx tsc -b && npx oxlint
```

Tests validate Pydantic schemas and the completeness validator. Extraction and generation tests require a valid `ANTHROPIC_API_KEY`.

## Licensing Notes

- **PyMuPDF** uses AGPL-3.0, which requires a commercial license for proprietary SaaS distribution. For production, consider switching the classifier to use `pypdfium2` (Apache-2.0 license) as a drop-in alternative.
- **pdfplumber** (MIT), **docxtpl** (LGPL), **python-docx** (MIT) are permissively licensed.

## HIPAA Notice

Use **only de-identified** progress reports during testing. Remove all 18 HIPAA identifiers before processing through the Claude API. For production use with PHI, obtain a BAA from Anthropic (direct API) or route through AWS Bedrock / Google Vertex AI / Azure under their respective BAAs. See `docs/deploy.md` for full deployment guidance.
