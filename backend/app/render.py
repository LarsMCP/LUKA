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
  <meta name="color-scheme" content="light dark">
  <title>{title}</title>
  <link rel="stylesheet" href="/assets/styles.css">
  <style>
    .luka-bar {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--md-outline-variant); display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }}
    .luka-status {{ color: var(--md-success); }}
    .luka-status.error {{ color: var(--md-error); }}
  </style>
  <script>
    (function () {{
      try {{
        var saved = localStorage.getItem("luka-theme");
        if (saved === "light" || saved === "dark") {{
          document.documentElement.setAttribute("data-theme", saved);
        }}
      }} catch (e) {{}}
    }})();
  </script>
</head>
<body>
  <header class="app-bar">
    <a href="/aufgaben"><span class="icon">arrow_back</span> Zurück zu den Aufgaben</a>
    <span class="app-bar__title subject">{title}</span>
    <nav class="app-bar__nav">
      <button type="button" id="theme-toggle" class="icon-btn" title="Farbschema wechseln" aria-label="Hell-/Dunkel-Modus wechseln">
        <span class="icon" id="theme-toggle-icon">dark_mode</span>
      </button>
    </nav>
  </header>
  <main class="page">
    <div id="luka-task-body">
{body}
    </div>
  </main>
  <script>window.LUKA_TASK = {task_json};</script>
  <script src="/static/luka.js"></script>
  <script>
    (function () {{
      var mql = window.matchMedia("(prefers-color-scheme: dark)");
      function getSaved() {{
        try {{ return localStorage.getItem("luka-theme"); }} catch (e) {{ return null; }}
      }}
      function isDark() {{
        var saved = getSaved();
        if (saved === "dark") return true;
        if (saved === "light") return false;
        return mql.matches;
      }}
      function updateIcon() {{
        var icon = document.getElementById("theme-toggle-icon");
        if (icon) icon.textContent = isDark() ? "light_mode" : "dark_mode";
      }}
      updateIcon();
      var btn = document.getElementById("theme-toggle");
      if (btn) {{
        btn.addEventListener("click", function () {{
          var next = isDark() ? "light" : "dark";
          try {{ localStorage.setItem("luka-theme", next); }} catch (e) {{}}
          document.documentElement.setAttribute("data-theme", next);
          updateIcon();
        }});
      }}
    }})();
  </script>
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
