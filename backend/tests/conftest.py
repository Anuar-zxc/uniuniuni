import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update({
    "ENVIRONMENT": "test",
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "AI_PROVIDER": "mock",
    "STORAGE_LOCAL_DIR": f"{_tmp}/uploads",
    "ADMIN_EMAIL": "admin@example.com",
    "JWT_SECRET": "test-secret-that-is-at-least-32-bytes-long",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CV = """Aidar Nurlanov
aidar@example.com | +7 701 000 00 00 | github.com/aidar
Frontend Developer, 3 years of experience

EXPERIENCE
Kolesa Group — Frontend Developer, 2022 – present
- Built a React + TypeScript dashboard used by 40k users per month
- Reduced bundle size by 35% with code splitting and lazy loading in Next.js
- Introduced Jest and Playwright tests, raising coverage from 20% to 70%
- Integrated REST API endpoints with the Node.js backend team

Freelance — Web Developer, 2021 – 2022
- Developed landing pages with HTML, CSS and JavaScript for 12 clients

EDUCATION
KBTU, BSc Information Systems, 2021

SKILLS
JavaScript, TypeScript, React, Next.js, Redux, HTML, CSS, Git, Docker
"""

JOB = """Middle Frontend Engineer at Kaspi.kz
We are looking for a Middle Frontend Engineer.
Requirements:
- 3+ years with JavaScript and TypeScript
- Strong React, understanding of rendering and performance
- REST API integration, Git
- Experience with testing (Jest)
Nice to have: Next.js, Docker, Kubernetes, GraphQL
"""


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "locale": "en"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
