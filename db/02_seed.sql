-- Fictional jobs and scoring criteria (test data only).

INSERT INTO jobs (slug, title, description) VALUES
('ai-automation-engineer', 'Internal AI Engineer - Automations',
 'Build AI-powered workflows that automate internal processes across teams. Python, LLM APIs, workflow tools (n8n/Zapier), SQL, and a strong sense for reliability and data privacy.'),
('backend-engineer', 'Backend Engineer (Python)',
 'Design and operate backend services and APIs. Python, FastAPI or Django, PostgreSQL, Docker, cloud deployment, testing.'),
('recruiting-coordinator', 'Recruiting Coordinator',
 'Coordinate interview processes, keep the ATS clean, communicate with candidates and hiring managers. Organisation, communication, tooling affinity.');

INSERT INTO criteria (job_id, name, description, weight)
SELECT j.id, c.name, c.description, c.weight
FROM jobs j
JOIN (VALUES
    ('ai-automation-engineer', 'python',          'Production experience writing Python services or scripts.', 0.25),
    ('ai-automation-engineer', 'llm_integration',  'Has integrated LLM APIs (prompting, structured output, evaluation).', 0.25),
    ('ai-automation-engineer', 'workflow_tools',   'Experience with n8n, Zapier, Make or similar automation tools.', 0.20),
    ('ai-automation-engineer', 'data_sql',         'Works confidently with SQL databases and data modelling.', 0.15),
    ('ai-automation-engineer', 'stakeholders',     'Gathers requirements from non-technical teams and ships for them.', 0.15),

    ('backend-engineer', 'python',        'Production experience with Python backends.', 0.30),
    ('backend-engineer', 'api_design',    'Designed REST or GraphQL APIs (FastAPI, Django, Flask).', 0.25),
    ('backend-engineer', 'databases',     'PostgreSQL or similar, schema design, query tuning.', 0.20),
    ('backend-engineer', 'devops',        'Docker, CI/CD, cloud deployment.', 0.15),
    ('backend-engineer', 'testing',       'Writes automated tests (pytest or similar).', 0.10),

    ('recruiting-coordinator', 'coordination',  'Scheduling and coordinating many stakeholders at once.', 0.35),
    ('recruiting-coordinator', 'communication', 'Clear written and spoken communication with candidates.', 0.30),
    ('recruiting-coordinator', 'ats_tools',     'Experience with ATS tools (Greenhouse, Lever, Personio).', 0.20),
    ('recruiting-coordinator', 'languages',     'Fluent English; additional languages are a plus.', 0.15)
) AS c(job_slug, name, description, weight) ON c.job_slug = j.slug;
