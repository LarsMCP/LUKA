# LUKA – Lernplattform

Schlanke, DSGVO-freundliche Online-Lernplattform für Schülerklassen.
Backend: **FastAPI + SQLite**. Aufgaben werden als HTML-Dateien im Verzeichnis
`content/aufgaben/` abgelegt und automatisch erkannt.

## Funktionen

- **Schüler-Login** per Klassen-Code + Pseudonym (case-insensitiv, keine Klarnamen/E-Mails).
- **Aufgaben** als HTML-Dateien; Antworten werden über `luka.js` erfasst und gespeichert (beliebig oft korrigierbar). Status „offen/abgegeben" in der Übersicht.
- **Admin-Bereich**: Klassen + Beitritts-Codes, Aufgaben freischalten, Schülerverwaltung, Ergebnisansicht + CSV-Export.
- **DSGVO**: Datenminimierung, Datenschutzhinweise (`/datenschutz`), Lösch­funktionen (Schüler + ganze Klassen), Secure-Cookies + TLS in Produktion.
- **Rollen** vorbereitet für weitere Lehrer/Admins (`role`, `owner_teacher_id`).

## Projektstruktur

```
LUKA/
  backend/app/
    config.py       # Pfade & Einstellungen (inkl. SECURE_COOKIES)
    database.py     # SQLite-Engine, Session, init_db
    models.py       # Datenmodelle (SQLModel)
    auth.py         # Schüler-Session   admin_auth.py # Lehrer-Session (argon2)
    discovery.py    # Aufgaben-Scan     render.py     # Aufgabenseite + luka.js
    student.py      # Schüler-Flow      admin.py      # Admin-Bereich
    create_admin.py # CLI: Admin anlegen  maintenance.py # Dubletten zusammenführen
    templates/      # Jinja2-Templates
    main.py         # FastAPI-App + Health-Check + /datenschutz
  runtime/luka.js   # Antworten sammeln/absenden/vorausfüllen
  content/aufgaben/ # HTML-Aufgaben (dateibasiert)
  data/luka.db      # SQLite-Datenbank (wird automatisch angelegt)
  deploy/           # docker-compose.yml, Caddyfile, backup.sh
  Dockerfile
  requirements.txt
```

## Admin-Konto anlegen

```bash
.venv/bin/python -m backend.app.create_admin admin
```

Passwort wird interaktiv abgefragt. Danach Login unter `/admin/login`.

## Neue Aufgabe erstellen

Einen Ordner `content/aufgaben/<slug>/index.html` anlegen (HTML-Fragment):

```html
<script type="application/json" id="luka-task">
{ "title": "Bruchrechnung 1", "subject": "Mathe" }
</script>
<h1>Bruchrechnung</h1>
<p>1/2 + 1/2 = <input name="a1"></p>
```

Alle `input`/`select`/`textarea` mit `name` werden automatisch gespeichert.
Danach im Admin unter „Aufgaben" auf **Neu einlesen** klicken und der Klasse freischalten.

## Lokal starten (ohne Docker)

```bash
python -m venv .venv
source .venv/bin/activate      # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Danach erreichbar:

- Health-Check: <http://127.0.0.1:8000/health>
- API-Docs (Swagger): <http://127.0.0.1:8000/docs>

## Lokal starten (Docker)

```bash
docker compose -f deploy/docker-compose.yml up --build
```

App dann über Caddy unter <http://localhost/health> erreichbar.

## Deployment (EU-VPS, DSGVO-freundlich)

Empfehlung: kleiner EU-VPS (z.B. Hetzner, Standort DE) mit Docker Compose.

1. In `deploy/Caddyfile` die Domain eintragen (statt `:80`) – Caddy holt automatisch ein TLS-Zertifikat.
2. `deploy/.env` anlegen mit `LUKA_SECURE_COOKIES=true` (Cookies nur über HTTPS).
3. Start: `docker compose -f deploy/docker-compose.yml up -d --build`.
4. Admin-Konto im Container anlegen: `docker compose -f deploy/docker-compose.yml exec app python -m backend.app.create_admin admin`.

**Backups**: `deploy/backup.sh` sichert DB + Aufgaben in ein Archiv (per Cron, siehe Kopf der Datei).

### DSGVO-Hinweise

- Datenminimierung: nur Pseudonyme, keine Klarnamen/E-Mails der Schüler.
- Datenschutzhinweise unter `/datenschutz` – Platzhalter (Verantwortlicher, Kontakt) ausfüllen.
- Löschung: einzelne Schüler oder ganze Klassen (kaskadierend) im Admin; am Schuljahresende Klasse löschen.
- AVV mit dem Hoster abschließen; Server-Standort EU/DE.
- Kein Rechtsrat – im Zweifel mit dem/der Datenschutzbeauftragten abstimmen.
