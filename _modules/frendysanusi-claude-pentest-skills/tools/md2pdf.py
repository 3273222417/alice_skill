import argparse
import re
import sys
from pathlib import Path

import markdown
from weasyprint import HTML

CSS = """
@page {
    size: A4;
    margin: 1cm 1.5cm;
    @bottom-center { content: counter(page) " / " counter(pages); font-size: 9px; color: #888; }
    @top-right { content: "CONFIDENTIAL"; font-size: 8px; color: #c00; letter-spacing: 2px; }
}

body {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11px;
    line-height: 1.6;
    color: #1a1a1a;
}

h1 { font-size: 22px; color: #0d47a1; border-bottom: 3px solid #0d47a1; padding-bottom: 6px; margin-top: 30px; page-break-before: auto; }
h2 { font-size: 17px; color: #1565c0; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 24px; }
h3 { font-size: 14px; color: #1976d2; margin-top: 18px; }
h4 { font-size: 12px; color: #333; margin-top: 14px; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 10px;
}
th {
    background: #0d47a1;
    color: white;
    padding: 6px 8px;
    text-align: left;
    font-weight: 600;
}
td {
    padding: 5px 8px;
    border-bottom: 1px solid #ddd;
    overflow-wrap: break-word;
    word-wrap: break-word;
}
tr:nth-child(even) td { background: #f5f7fa; }

/* Metadata tables */
table.meta { margin: 6px 0; }
table.meta thead { display: none; }
table.meta td { border-bottom: none; padding: 2px 8px; }
table.meta td:first-child { width: 160px; white-space: nowrap; }
table.meta tr:nth-child(even) td { background: none; }

code {
    background: #f0f0f0;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 10px;
    font-family: "Courier New", monospace;
}
pre {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 12px 14px;
    border-radius: 4px;
    font-size: 9.5px;
    line-height: 1.5;
    overflow-wrap: break-word;
    white-space: pre-wrap;
    margin: 10px 0;
}
pre code {
    background: none;
    padding: 0;
    color: inherit;
    font-size: inherit;
}

blockquote {
    border-left: 3px solid #0d47a1;
    padding: 8px 14px;
    margin: 10px 0;
    background: #f5f7fa;
    color: #444;
}

strong { color: #111; }

hr { border: none; border-top: 1px solid #ccc; margin: 20px 0; }


"""


def convert(md_path: str, pdf_path: str | None = None) -> str:
    source = Path(md_path)
    if not source.exists():
        print(f"Error: {md_path} not found", file=sys.stderr)
        sys.exit(1)

    dest = Path(pdf_path) if pdf_path else source.with_suffix(".pdf")

    md_text = source.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
        extension_configs={"codehilite": {"guess_lang": False, "css_class": "code"}},
    )

    html_body = re.sub(
        r'(<table>\s*<thead>\s*<tr>\s*(?:<th>\s*</th>\s*)+</tr>\s*</thead>)',
        lambda m: m.group(0).replace('<table>', '<table class="meta">'),
        html_body,
    )

    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{html_body}</body></html>"""

    HTML(string=full_html).write_pdf(str(dest))
    print(f"PDF saved: {dest} ({dest.stat().st_size // 1024} KB)")
    return str(dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert markdown report to PDF")
    parser.add_argument("input", help="Path to markdown file")
    parser.add_argument("-o", "--output", help="Output PDF path (default: same name .pdf)")
    args = parser.parse_args()
    convert(args.input, args.output)
