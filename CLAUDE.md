# Recruiting Copilot

Portfolio-Projekt für eine Bewerbung bei ElevenLabs (Rolle: Internal AI Engineer / Automations).
Ziel: zeigen, dass ich KI-Workflows bauen kann, die einen echten manuellen Ablauf automatisieren – zuverlässig, nachvollziehbar und sicher.

## Was das Projekt macht
1. Eine Bewerbung (Lebenslauf als PDF + Stelle) kommt per n8n-Webhook rein.
2. Ein Python-Service liest den PDF-Text und lässt Claude den Lebenslauf anhand fester Kriterien bewerten.
3. Die passenden Kriterien zur Stelle werden per RAG aus PostgreSQL (pgvector) geholt.
4. Jede Bewertung wird mit Zeitstempel, Modellname und Begründung in PostgreSQL gespeichert (Audit-Log).
5. n8n schickt eine Zusammenfassung mit Buttons „Weiter“ / „Absage“ an Slack (#recruiting).
6. Die Entscheidung trifft immer ein Mensch. Der Button-Klick wird ebenfalls gespeichert.
7. Optional (Bonus): ElevenAgents-Sprachagent führt ein kurzes Vor-Interview (3 Fragen), das Transkript fließt in die Bewertung ein.

## Tech-Stack
- Python 3.12, FastAPI, Pydantic
- PostgreSQL 16 mit pgvector
- Anthropic API (Claude) für Bewertung, strukturierte JSON-Ausgabe
- n8n für Orchestrierung (Webhook → Service → Slack)
- Docker + docker-compose lokal, Deployment auf Google Cloud Run
- pytest für Tests

## Regeln
- Code, Kommentare, Commit-Messages und README auf Englisch. Erklärungen an mich bitte auf Deutsch.
- Nur erfundene Testdaten – niemals echte Personendaten.
- Keine personenbezogenen Daten in Logs (nur IDs).
- API-Keys nur über Umgebungsvariablen (.env), .env steht in .gitignore, .env.example ist im Repo.
- Die KI gibt nur eine Empfehlung mit Begründung ab, nie eine automatische Absage (EU AI Act: Recruiting = Hochrisiko-Bereich, Mensch entscheidet).
- Claude-Antworten immer gegen ein Pydantic-Schema validieren; bei ungültiger Antwort einmal neu versuchen, sonst Fehler speichern.
- Kleine Schritte: nach jedem Schritt kurz erklären, was gebaut wurde und wie ich es teste.
- Am Ende jedes Tages: schreib mir in notizen.md auf Deutsch 3–5 Sätze, welche Entscheidungen wir getroffen haben und warum.

## GitHub
- Öffentliches Repo „recruiting-copilot“, ich nutze GitHub Desktop.
- Nach jeder abgeschlossenen Aufgabe einen kleinen Commit mit klarer englischer Message.
- Am Ende jedes Tages pushen (oder mir sagen, dass ich in GitHub Desktop auf „Push origin“ klicken soll).
- Vor jedem Commit prüfen, dass keine .env, API-Keys oder echten Personendaten im Commit sind.

## Bewertungs-Ausgabe (JSON)
- score: 0–100
- recommendation: "advance" | "review" | "reject_suggested"
- strengths: Liste
- gaps: Liste
- reasoning: kurzer Text
- criteria_scores: Punkte je Kriterium

## Ordnerstruktur (Ziel)
```
recruiting-copilot/
├── app/            # FastAPI-Service (main.py, scoring.py, rag.py, db.py, schemas.py)
├── db/             # SQL-Schema und Seed-Daten
├── data/           # erfundene Lebensläufe (PDF) + Stellenanzeigen
├── evals/          # Testfälle mit erwartetem Ergebnis + Auswertungsskript
├── n8n/            # exportierte Workflows (JSON)
├── scripts/        # Hilfsskripte (z. B. Testdaten erzeugen)
├── tests/
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md
```

## Wochenplan
- Tag 1: Repo, Docker, PostgreSQL, Testdaten
- Tag 2: PDF lesen + Claude-Bewertung (JSON)
- Tag 3: RAG mit pgvector + Speichern
- Tag 4: n8n-Workflow + Slack mit Buttons
- Tag 5: Evaluation (Skript + Ergebnistabelle)
- Tag 6: Cloud Run Deployment, optional ElevenAgents
- Tag 7: README (Englisch, Architektur-Diagramm) + Demo-Video
