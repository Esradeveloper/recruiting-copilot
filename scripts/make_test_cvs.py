"""Generate fictional CV PDFs for local testing.

All people, companies and contact details are invented.
Run: .venv/bin/python scripts/make_test_cvs.py
"""

from pathlib import Path

from fpdf import FPDF

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "cvs"

CVS = {
    # Strong match for ai-automation-engineer
    "cv_01_strong_ai.pdf": {
        "name": "Mira Testfeld",
        "headline": "Automation Engineer",
        "summary": "Four years building internal tools and AI workflows for operations teams.",
        "experience": [
            "2022-today  Automation Engineer, Nordlicht Logistics GmbH (fictional)",
            "  - Built 30+ n8n workflows for Finance and HR, saving ~40 h/week",
            "  - Integrated the Claude and OpenAI APIs with JSON-schema output and eval sets",
            "  - Python/FastAPI microservices on PostgreSQL, deployed via Docker",
            "2020-2022  Data Analyst, Beispiel Retail AG (fictional)",
            "  - SQL reporting, dbt models, requirement workshops with sales teams",
        ],
        "skills": "Python, FastAPI, SQL, PostgreSQL, n8n, Zapier, LLM APIs, Docker, pytest",
        "education": "B.Sc. Business Informatics, Fictional University of Applied Sciences",
    },
    # Partial match: strong backend, no LLM / workflow experience
    "cv_02_backend_only.pdf": {
        "name": "Jonas Platzhalter",
        "headline": "Senior Backend Developer",
        "summary": "Python backend developer focused on APIs and databases.",
        "experience": [
            "2019-today  Backend Developer, Musterbank Digital (fictional)",
            "  - Django and FastAPI services handling payments",
            "  - PostgreSQL schema design and query optimisation",
            "  - CI/CD with GitHub Actions, Kubernetes",
        ],
        "skills": "Python, Django, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, pytest",
        "education": "M.Sc. Computer Science, Fictional Technical University",
    },
    # Career changer: no-code automation, little Python
    "cv_03_career_changer.pdf": {
        "name": "Lena Erfunden",
        "headline": "Operations Manager turned Automation Builder",
        "summary": "Ops manager who automated her own team's work with no-code tools.",
        "experience": [
            "2021-today  Operations Manager, Sample Travel GmbH (fictional)",
            "  - Built Make and Zapier automations for booking and invoicing",
            "  - Prototyped a ChatGPT-based email triage in Google Sheets",
            "  - Python course (Udemy), small scripts for CSV cleanup",
        ],
        "skills": "Make, Zapier, Airtable, Google Apps Script, basic Python, stakeholder management",
        "education": "B.A. Tourism Management",
    },
    # Weak match for an engineering role
    "cv_04_weak.pdf": {
        "name": "Tom Fiktiv",
        "headline": "Sales Representative",
        "summary": "Sales professional with strong customer focus.",
        "experience": [
            "2018-today  Account Executive, Demo Software Ltd. (fictional)",
            "  - Exceeded quota 3 years in a row",
            "  - CRM maintenance in Salesforce",
        ],
        "skills": "Salesforce, negotiation, presentations, English, German",
        "education": "Apprenticeship, Industrial Clerk",
    },
    # Good match for recruiting-coordinator
    "cv_05_recruiting.pdf": {
        "name": "Sara Musterfrau",
        "headline": "Talent Acquisition Coordinator",
        "summary": "Coordinates hiring for fast-growing tech teams across time zones.",
        "experience": [
            "2021-today  Recruiting Coordinator, Example Audio Inc. (fictional)",
            "  - Scheduled 60+ interviews per week across EU and US",
            "  - Owner of Greenhouse hygiene and candidate communication templates",
            "2019-2021  HR Assistant, Probe GmbH (fictional)",
        ],
        "skills": "Greenhouse, Personio, Google Workspace, English (C2), German (C1), Spanish (B2)",
        "education": "B.A. Communication Studies",
    },
    # Edge case: very short CV with almost no information
    "cv_06_minimal.pdf": {
        "name": "Kim Anonym",
        "headline": "Developer",
        "summary": "Looking for new challenges.",
        "experience": ["2020-today  Developer"],
        "skills": "Programming",
        "education": "",
    },
}


def render(path: Path, cv: dict) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, cv["name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, cv["headline"], new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "contact: candidate@example.com (fictional)", new_x="LMARGIN", new_y="NEXT")

    for title, body in [
        ("Summary", [cv["summary"]]),
        ("Experience", cv["experience"]),
        ("Skills", [cv["skills"]]),
        ("Education", [cv["education"]] if cv["education"] else []),
    ]:
        if not body:
            continue
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for line in body:
            pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(path))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, cv in CVS.items():
        render(OUT_DIR / filename, cv)
        print(f"wrote {filename}")


if __name__ == "__main__":
    main()
