-- Fictional jobs and a shared criteria library (test data only).
-- Embeddings are filled by scripts/backfill_embeddings.py.

INSERT INTO jobs (slug, title, description) VALUES
('ai-automation-engineer', 'Internal AI Engineer - Automations',
 'Build AI-powered workflows that automate internal processes across teams. Python, LLM APIs, workflow tools (n8n/Zapier), SQL, and a strong sense for reliability and data privacy.'),
('backend-engineer', 'Backend Engineer (Python)',
 'Design and operate backend services and APIs. Python, FastAPI or Django, PostgreSQL, Docker, cloud deployment, testing.'),
('recruiting-coordinator', 'Recruiting Coordinator',
 'Coordinate interview processes, keep the ATS clean, communicate with candidates and hiring managers. Organisation, communication, tooling affinity.');

INSERT INTO criteria (name, description, weight) VALUES
('python',                  'Production experience writing Python services, scripts or backends.', 1.00),
('llm_integration',         'Has integrated LLM APIs: prompting, structured output, evaluation of AI output.', 1.00),
('workflow_automation',     'Builds automations with n8n, Zapier, Make or similar workflow tools.', 0.80),
('sql_data',                'Works confidently with SQL databases, PostgreSQL and data modelling.', 0.60),
('stakeholder_work',        'Gathers requirements from non-technical teams and ships internal tools for them.', 0.60),
('api_design',              'Designed REST or GraphQL APIs with FastAPI, Django or Flask.', 0.80),
('devops_cloud',            'Docker, CI/CD pipelines and cloud deployment.', 0.60),
('automated_testing',       'Writes automated tests with pytest or similar frameworks.', 0.40),
('interview_coordination',  'Schedules and coordinates interviews and hiring processes across many stakeholders.', 1.00),
('candidate_communication', 'Clear written and spoken communication with candidates and hiring managers.', 0.80),
('ats_tools',               'Experience keeping an applicant tracking system (Greenhouse, Lever, Personio) clean.', 0.60),
('languages',               'Fluent English; additional languages are a plus.', 0.40);
