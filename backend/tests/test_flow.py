"""End-to-end: Upload CV → Analyze → Add Job → Match → Interview → Evaluate → Report → Weaknesses →
Training → Retest → Readiness, plus billing, admin and privacy endpoints."""

from conftest import CV, JOB, register

GOOD = ("For example, in my project at Kolesa we had a slow dashboard. First I measured it with the profiler, "
        "found that the call stack was blocked and that state changes re-rendered the whole tree. I used React.memo, "
        "useMemo and stable keys, moved server state into a query cache, and code splitting cut the bundle by 35%. "
        "The trade-off is extra complexity, so I only memoize hot paths. At 10x scale I would add a CDN and caching.")
BAD = "I don't know"


def answer_until_done(client, h, state, pick):
    for _ in range(60):
        if state["status"] != "in_progress":
            return state
        q = state["current_question"]
        r = client.post(f"/api/v1/interviews/sessions/{state['session_id']}/answer", headers=h,
                        json={"text": pick(q), "duration_seconds": 40})
        assert r.status_code == 200, r.text
        state = r.json()
    raise AssertionError("interview did not finish")


def test_full_flow(client):
    h = register(client, "candidate@example.com")

    # CV upload as a real file (TXT) + analysis
    r = client.post("/api/v1/resumes", headers=h, files={"file": ("cv.txt", CV.encode(), "text/plain")})
    assert r.status_code == 201, r.text
    resume = r.json()
    assert resume["status"] == "analyzed"
    a = resume["analysis"]
    assert {"React", "TypeScript"} <= set(a["technologies"])
    assert 0 < resume["overall_score"] <= 100
    assert a["likely_questions"], "CV bullets must turn into interview questions"

    # onboarding autofilled from CV
    me = client.get("/api/v1/profile", headers=h).json()
    assert me["profile"]["stack"]
    assert me["profile"]["level"] in ("junior", "middle", "senior")

    # job + match + blueprint
    r = client.post("/api/v1/jobs", headers=h, json={"title": "Middle Frontend Engineer", "company_name": "Kaspi.kz",
                                                     "description": JOB, "interview_date": "2030-01-15"})
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["match_score"] is not None and 0 <= job["match_score"] <= 100
    assert "React" in job["match"]["strong"] + job["match"]["weak"]
    assert abs(sum(job["blueprint"]["weights"].values()) - 1) < 0.02
    assert job["blueprint"]["topics"]

    # interview: alternate strong and empty answers
    r = client.post("/api/v1/interviews", headers=h, json={"job_id": job["id"], "mode": "mixed", "language": "en"})
    assert r.status_code == 201, r.text
    state = r.json()
    assert state["current_question"]["text"]
    assert state["progress"]["planned_main"] >= 5
    counter = {"n": 0}

    def pick(q):
        counter["n"] += 1
        return BAD if counter["n"] % 3 == 0 else GOOD

    final = answer_until_done(client, h, state, pick)
    assert final["status"] == "completed"

    rep = client.get(f"/api/v1/interviews/sessions/{final['session_id']}/report", headers=h)
    assert rep.status_code == 200, rep.text
    report = rep.json()
    assert 0 <= report["overall"] <= 100
    assert report["dimensions"] and all("score" in d for d in report["dimensions"])
    assert report["readiness"]["status"] in ("READY", "ALMOST_READY", "NEEDS_WORK", "NOT_READY")

    # Error Memory captured the empty answers
    weak = client.get("/api/v1/weaknesses", headers=h).json()
    assert weak, "bad answers must create weaknesses"
    assert weak[0]["severity"] in ("critical", "high", "medium")
    assert weak[0]["recommended_exercise"]

    # Training plan generated from weaknesses, and every task is checkable
    plan = client.get("/api/v1/training", headers=h).json()
    assert plan and plan["tasks"]
    task = plan["tasks"][0]
    for i, _ in enumerate(task["questions"]):
        r = client.post(f"/api/v1/training/tasks/{task['id']}/answer", headers=h, json={"index": i, "text": GOOD})
        assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"
    assert r.json()["score"] is not None

    # Readiness history grows; dashboard has a next best action
    rd = client.get("/api/v1/readiness", headers=h).json()
    assert len(rd["history"]) >= 3
    assert len(rd["risks"]) <= 3
    dash = client.get("/api/v1/dashboard", headers=h).json()
    assert dash["next_best_action"]["action"]
    assert dash["upcoming_interview"]["days_left"] > 0
    assert dash["target"]["job_id"] == job["id"]

    # Free plan allows 1 interview → second is blocked with 402
    r = client.post("/api/v1/interviews", headers=h, json={"job_id": job["id"], "mode": "technical"})
    assert r.status_code == 402

    # Upgrade via sandbox provider, then retest works
    r = client.post("/api/v1/billing/checkout", headers=h, json={"plan_code": "pro", "currency": "KZT"})
    assert r.status_code == 200, r.text
    ext = r.json()["external_id"]
    assert client.post("/api/v1/billing/sandbox/confirm", headers=h, json={"external_id": ext}).status_code == 200
    assert client.get("/api/v1/profile", headers=h).json()["plan"]["code"] == "pro"
    r = client.post(f"/api/v1/interviews/{final['interview_id']}/retest", headers=h)
    assert r.status_code == 201, r.text
    retest = answer_until_done(client, h, r.json(), lambda q: GOOD)
    rep2 = client.get(f"/api/v1/interviews/sessions/{retest['session_id']}/report", headers=h).json()
    assert len(rep2["attempts"]) == 2
    assert rep2["previous_overall"] == report["overall"]

    # Privacy: export, then delete
    exp = client.get("/api/v1/profile/export", headers=h)
    assert exp.status_code == 200 and exp.json()["resumes"]


def test_admin_and_rbac(client):
    user_h = register(client, "plain@example.com")
    assert client.get("/api/v1/admin/overview", headers=user_h).status_code == 403
    admin_h = register(client, "admin@example.com")
    ov = client.get("/api/v1/admin/overview", headers=admin_h)
    assert ov.status_code == 200, ov.text
    assert "funnel" in ov.json()
    assert client.get("/api/v1/admin/ai/usage", headers=admin_h).status_code == 200
    prompts = client.get("/api/v1/admin/prompts", headers=admin_h).json()
    assert "evaluate_answer" in prompts["keys"]
    r = client.post("/api/v1/admin/prompts", headers=admin_h, json={
        "key": "chat", "system": "You are a concise coach. Answer in $language_name.", "user_template": "$message", "activate": True})
    assert r.status_code == 200 and r.json()["version"] == 2
    assert client.get("/api/v1/admin/questions", headers=admin_h).json()
    r = client.post("/api/v1/admin/companies", headers=admin_h, json={"name": "Test Co", "public_interview_notes": "x"})
    assert r.status_code == 400  # notes require a public source


def test_ownership_and_auth(client):
    a = register(client, "a@example.com")
    b = register(client, "b@example.com")
    r = client.post("/api/v1/resumes/text", headers=a, json={"text": CV})
    rid = r.json()["id"]
    assert client.get(f"/api/v1/resumes/{rid}", headers=b).status_code == 404
    client.cookies.clear()  # TestClient keeps the last session cookie
    assert client.get("/api/v1/dashboard").status_code == 401
    bad = client.post("/api/v1/resumes", headers=a, files={"file": ("cv.pdf", b"not a pdf at all" * 20, "application/pdf")})
    assert bad.status_code == 422
    assert client.delete("/api/v1/profile", headers=b).status_code == 200
    assert client.get("/api/v1/profile", headers=b).status_code == 401
