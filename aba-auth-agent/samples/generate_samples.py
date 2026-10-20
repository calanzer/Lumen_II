"""Build the fictional sample files used to try the app end to end.

    python samples/generate_samples.py

Writes into samples/files/:
  past_reports/   a clinic's previously approved reauthorization reports. Upload one on
                  the Templates page to teach the app that layout.
  progress_reports/   new-period reports to upload for a client (complete, and with gaps).
Everything in these files is invented; no real people, clinics or IDs.
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import past_reports  # noqa: E402
import progress_reports  # noqa: E402
import render  # noqa: E402

OUT = HERE / "files"


def build() -> list[Path]:
    past_dir = OUT / "past_reports"
    new_dir = OUT / "progress_reports"
    past_dir.mkdir(parents=True, exist_ok=True)
    new_dir.mkdir(parents=True, exist_ok=True)

    written = [
        past_dir / "past_reauth_anthem_style.docx",
        past_dir / "past_reauth_carelon_style.pdf",
        new_dir / "progress_complete_sam.docx",
        new_dir / "progress_gappy_devon.pdf",
    ]
    render.to_docx(past_reports.anthem_style_report(), written[0])
    render.to_pdf(past_reports.carelon_style_report(), written[1])
    render.to_docx(progress_reports.complete_report(), written[2])
    render.to_pdf(progress_reports.gappy_report(), written[3])
    return written


if __name__ == "__main__":
    for path in build():
        print(f"{path.relative_to(HERE.parent)}  ({path.stat().st_size:,} bytes)")
