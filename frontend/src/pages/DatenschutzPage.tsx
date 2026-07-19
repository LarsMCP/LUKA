export function DatenschutzPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="sticky top-0 z-50 border-b border-gray-200 bg-white/95 px-4 py-3 backdrop-blur dark:border-gray-700 dark:bg-gray-900/95">
        <span className="text-lg font-bold">LUKA – Datenschutzhinweise</span>
      </div>
      <main className="mx-auto max-w-2xl p-6">
        <div className="prose dark:prose-invert">
          <h2>Datenschutz</h2>
          <p>
            LUKA ist eine schlanke Lernplattform. Es werden keine echten Namen
            gespeichert – Schüler melden sich mit einem selbst gewählten Kürzel
            (Pseudonym) an.
          </p>
          <h3>Was gespeichert wird</h3>
          <ul>
            <li>Klassen-Code und Klassenname</li>
            <li>Schüler-Kürzel (Pseudonym) und Passwort-Hash (Argon2)</li>
            <li>Abgaben (Antworten) mit Zeitstempel</li>
          </ul>
          <h3>Was nicht gespeichert wird</h3>
          <ul>
            <li>Keine echten Namen, E-Mail-Adressen oder IP-Adressen</li>
            <li>Keine Tracking-Cookies, keine externen CDN-Verbindungen</li>
          </ul>
          <p>
            Die Plattform wird selbst gehostet. Alle Daten bleiben auf dem
            Server der Schule/des Betreibers.
          </p>
        </div>
      </main>
    </div>
  );
}
