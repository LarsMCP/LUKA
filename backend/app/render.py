"""Aufbereitung der Aufgaben-HTML für die Auslieferung an Schüler.

Aufgaben-Dateien sind HTML-Fragmente. Vor der Auslieferung wird:
- der Meta-Block entfernt,
- `data-solution`/`data-type` entfernt (Vorbereitung Auto-Korrektur; kein Spicken),
- das Fragment in eine vollständige HTML-Seite mit der `luka.js`-Runtime gewrappt.
"""
from __future__ import annotations

import html as html_lib
import json
import re

# Entfernt den Meta-Block aus der Schüleransicht.
_META_BLOCK_RE = re.compile(
    r'<script[^>]*id=["\']luka-task["\'][^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)

# Entfernt data-solution / data-type Attribute (mit und ohne Wert).
_SOLUTION_ATTR_RE = re.compile(
    r'\s+data-(?:solution|type|tolerance)\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)',
    re.IGNORECASE,
)

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; line-height: 1.5; color: #111; }}
    .luka-topbar {{ background: #f8fafc; border-bottom: 1px solid #e5e7eb; padding: 0.75rem 1rem; display: flex; align-items: center; gap: 1rem; position: sticky; top: 0; }}
    .luka-topbar a {{ color: #2563eb; text-decoration: none; font-weight: 600; }}
    .luka-topbar .luka-title {{ color: #6b7280; font-weight: 400; }}
    .luka-wrap {{ max-width: 720px; margin: 1.5rem auto; padding: 0 1rem; }}
    input, select, textarea {{ font-size: 1rem; padding: 0.25rem 0.4rem; }}
    .luka-bar {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; display: flex; align-items: center; gap: 1rem; }}
    .luka-btn {{ background: #2563eb; color: #fff; border: 0; border-radius: 6px; padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }}
    .luka-btn:disabled {{ opacity: 0.6; cursor: default; }}
    .luka-status {{ color: #16a34a; }}
    .luka-status.error {{ color: #dc2626; }}
  </style>
</head>
<body>
  <header class="luka-topbar">
    <a href="/aufgaben">&larr; Zurück zu den Aufgaben</a>
    <span class="luka-title">{title}</span>
  </header>
  <div class="luka-wrap">
    <main id="luka-task-body">
{body}
    </main>
  </div>
  <script>window.LUKA_TASK = {task_json};</script>
  <script src="/static/luka.js"></script>
</body>
</html>
"""


def render_task_page(slug: str, title: str, raw_html: str) -> str:
    """Baut die auslieferbare HTML-Seite für eine Aufgabe."""
    body = _META_BLOCK_RE.sub("", raw_html)
    body = _SOLUTION_ATTR_RE.sub("", body)
    task_json = json.dumps({"slug": slug, "title": title})
    return _PAGE_TEMPLATE.format(
        title=html_lib.escape(title),
        body=body,
        task_json=task_json,
    )
