# Verbal Damage

Kleiner Webservice für zwei Personen: jede Person kann pro Kalendermonat einen Eintrag für die andere Person speichern. Der Eintrag verbraucht den Monats-Treffer und bleibt dauerhaft im Archiv. Am Monatswechsel wird das Kontingent automatisch wieder frei; die Historie bleibt erhalten.

## Start

1. Optional `.env.example` nach `.env` kopieren und Namen, Port oder erlaubte Browser-Origin anpassen.
2. Im Projektordner `docker compose up -d --build` ausführen.
3. Im Browser `http://localhost:8080` öffnen. Der HTTP-Port lässt sich über `PORT` einstellen.

Die Namen werden über `USER_ONE` und `USER_TWO` gesetzt. Das Datenbank-Volume `verbal-damage-data` hält das Archiv auch nach einem Container-Neustart fest.

## Technik

- Frontend: statische HTML/CSS/JS-Dateien hinter Nginx Alpine.
- Backend: Python-Standardbibliothek und SQLite, ohne zusätzliche Pakete. Ein einzelner HTTP-Request-Worker hält den Speicherverbrauch niedrig.
- API: `GET /api/state`, `POST /api/insults`, `GET /api/health`.
- CORS erlaubt ausschließlich die in `CORS_ORIGIN` eingestellte Origin (Standard `http://kackhost.lan`). Für HTTPS oder einen anderen Port den vollständigen Browser-Origin angeben, zum Beispiel `https://kackhost.lan`.
- Das Monatskontingent wird nach deutscher Ortszeit (Europe/Berlin) zum Monatswechsel zurückgesetzt. Jeder User kann höchstens einen Eintrag pro Kalendermonat erstellen; die API prüft und verbucht dies atomar.

Das Archiv zeigt sämtliche gespeicherten Einträge.
