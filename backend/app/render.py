"""Aufbereitung der Aufgaben-HTML für die Auslieferung an Schüler.

Es werden zwei Formate unterstützt:
1. **Fragmente** (klassisch): HTML-Schnipsel ohne <html>/<head>/<body>.
   Werden in das LUKA-Seitentemplate gewrappt.
2. **Vollformat-Dokumente** (Lernpfade): Komplette HTML-Seite mit eigenem
   <style>, <script>, Step-Navigation etc. Werden nicht gewrappt, sondern
   LUKA-Scripts werden vor </body> injiziert.

In beiden Fällen wird vor der Auslieferung:
- der Meta-Block entfernt,
- `data-solution`/`data-type`/`data-answer`/`data-correct` entfernt
  (kein Spicken im Schüler-View).
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

# Entfernt data-solution / data-type / data-answer / data-correct Attribute
# (mit und ohne Wert) – verhindert Spicken im Schüler-View.
_SOLUTION_ATTR_RE = re.compile(
    r'\s+data-(?:solution|type|tolerance|answer|correct)\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)',
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


# Erkennt vollständige HTML-Dokumente (<!DOCTYPE ...> oder <html ...>).
_FULL_DOC_RE = re.compile(r'^\s*(?:<!DOCTYPE\s+html|<html)', re.IGNORECASE)

# Injektions-Scripts für Vollformat-Dokumente (vor </body> eingefügt).
_LUKA_INJECT = """  <!-- LUKA-Integration -->
  <a href="/aufgaben" style="position:fixed;top:12px;left:12px;z-index:9999;background:rgba(255,255,255,.9);border:1px solid #dbe3ef;border-radius:999px;padding:6px 14px;font-family:system-ui,sans-serif;font-size:.85rem;font-weight:700;color:#2563eb;text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.12)">&larr; Aufgaben</a>
  <script>window.LUKA_TASK = {task_json};</script>
  <script src="/static/luka.js"></script>
{extra_inject}</body>"""


def render_task_page(slug: str, title: str, raw_html: str, extra_inject: str = "") -> str:
    """Baut die auslieferbare HTML-Seite für eine Aufgabe.

    Erkennt automatisch, ob es sich um ein Fragment oder ein vollständiges
    HTML-Dokument handelt und wendet die entsprechende Rendering-Strategie an.

    extra_inject: Zusätzlicher HTML/JS-Code, der vor </body> eingefügt wird
                  (z.B. für die Lehrer-Ansicht mit Schüler-Antworten).
    """
    html = _META_BLOCK_RE.sub("", raw_html)
    html = _SOLUTION_ATTR_RE.sub("", html)
    task_json = json.dumps({"slug": slug, "title": title})

    if _FULL_DOC_RE.match(html):
        # Vollformat: nicht wrappen, LUKA-Scripts vor </body> injizieren.
        inject = _LUKA_INJECT.format(task_json=task_json, extra_inject=extra_inject)
        return html.replace("</body>", inject, 1)

    # Fragment: in LUKA-Seitentemplate wrappen (wie bisher).
    return _PAGE_TEMPLATE.format(
        title=html_lib.escape(title),
        body=html,
        task_json=task_json,
    )
