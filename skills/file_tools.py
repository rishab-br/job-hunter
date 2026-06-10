from pathlib import Path


OUTPUTS_DIR = Path("outputs")

# Print-optimised stylesheet for resume PDFs — single page, ATS-friendly fonts
_RESUME_CSS = """
  * { box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10.5pt; line-height: 1.45; color: #1a1a1a;
    max-width: 100%; margin: 0; padding: 0;
  }
  h1 { font-size: 19pt; margin: 0 0 2pt; letter-spacing: -0.3pt; }
  h2 {
    font-size: 11.5pt; text-transform: uppercase; letter-spacing: 1pt;
    border-bottom: 1.5pt solid #2563eb; padding-bottom: 2pt;
    margin: 12pt 0 6pt; color: #1e3a8a;
  }
  h3 { font-size: 10.5pt; margin: 8pt 0 2pt; }
  p { margin: 3pt 0; }
  ul { margin: 3pt 0; padding-left: 14pt; }
  li { margin: 1.5pt 0; }
  a { color: #2563eb; text-decoration: none; }
  strong { color: #111; }
  hr { border: none; border-top: 0.5pt solid #d1d5db; margin: 8pt 0; }
"""


def save_pdf_from_markdown(md_content: str, subdir: str, filename: str) -> Path:
    """Render Markdown to a clean single-column PDF via headless Chromium.

    Uses the Playwright install the project already ships — no LaTeX or
    wkhtmltopdf system dependency.
    """
    import markdown as md_lib
    from playwright.sync_api import sync_playwright

    body = md_lib.markdown(md_content, extensions=["extra", "sane_lists"])
    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{_RESUME_CSS}</style></head><body>{body}</body></html>"

    target = OUTPUTS_DIR / subdir
    target.mkdir(parents=True, exist_ok=True)
    path = target / filename

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(
            path=str(path),
            format="A4",
            margin={"top": "14mm", "bottom": "14mm", "left": "13mm", "right": "13mm"},
            print_background=True,
        )
        browser.close()
    return path


def save_text(content: str, subdir: str, filename: str) -> Path:
    """Saves text content to outputs/<subdir>/<filename>."""
    target = OUTPUTS_DIR / subdir
    target.mkdir(parents=True, exist_ok=True)
    path = target / filename
    path.write_text(content, encoding="utf-8")
    return path


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def list_outputs(subdir: str) -> list[Path]:
    target = OUTPUTS_DIR / subdir
    return sorted(target.iterdir()) if target.exists() else []
