#!/usr/bin/env bash
#
# LUKA-Backup: sichert die SQLite-Datenbank (konsistent via .backup) und das
# Aufgabenverzeichnis in ein zeitgestempeltes Archiv.
#
# Nutzung:
#   ./deploy/backup.sh [ZIEL_VERZEICHNIS]
#
# Cron-Beispiel (täglich 02:30 Uhr):
#   30 2 * * * /pfad/zu/LUKA/deploy/backup.sh /pfad/zu/backups >> /var/log/luka-backup.log 2>&1
set -euo pipefail

# Projektwurzel = eine Ebene über diesem Skript.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${LUKA_DB_PATH:-$ROOT_DIR/data/luka.db}"
CONTENT_DIR="${LUKA_CONTENT_ROOT:-$ROOT_DIR/content}"
DEST_DIR="${1:-$ROOT_DIR/backups}"

STAMP="$(date +%Y%m%d-%H%M%S)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$DEST_DIR"

# Konsistente DB-Kopie (funktioniert auch bei laufendem Server).
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB_PATH" ".backup '$WORK_DIR/luka.db'"
else
  cp "$DB_PATH" "$WORK_DIR/luka.db"
fi

# Aufgaben mitsichern.
cp -r "$CONTENT_DIR" "$WORK_DIR/content"

ARCHIVE="$DEST_DIR/luka-backup-$STAMP.tar.gz"
tar -czf "$ARCHIVE" -C "$WORK_DIR" luka.db content

# Alte Backups (älter als 30 Tage) aufräumen.
find "$DEST_DIR" -name 'luka-backup-*.tar.gz' -mtime +30 -delete 2>/dev/null || true

echo "Backup erstellt: $ARCHIVE"
