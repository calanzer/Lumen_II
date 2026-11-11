# Sample files

Fictional documents for trying the app end to end. No real people, clinics or IDs.
Regenerate them with `python samples/generate_samples.py`.

## Try it

1. **Templates page** — pick a payor and upload a file from `files/past_reports/`.
   - `past_reauth_anthem_style.docx`: nine narrative sections.
   - `past_reauth_carelon_style.pdf`: a clinical-form layout with member header, changes since last report, goal table, coordination of care.
2. **Clients page** — add a client for the same payor.
3. **Upload page** — upload a file from `files/progress_reports/` for that client.
   - `progress_complete_sam.docx`: every section filled in, table-heavy.
   - `progress_gappy_devon.pdf`: no assessments, no caregiver training, low hours with no explanation, no discharge criteria, a behavior with no baseline. Use it to check that gaps are flagged instead of invented.
4. **Review Data → Generate → Export**.

Extraction, template analysis and generation call the Anthropic API, so they need `ANTHROPIC_API_KEY` in `.env`.
