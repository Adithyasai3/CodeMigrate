"""API smoke test: register -> login -> project -> scan (JSON and zip) -> poll -> reports."""

import io
import time
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-secret-0123456789abcdef0123456789")
    from codemigrate.api import db

    db._engine = None
    from codemigrate.api.main import app

    with TestClient(app) as c:
        yield c
    db._engine = None


def auth(client, email="dev@example.com", password="correct-horse"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def wait(client, headers, sid, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        scan = client.get(f"/api/scans/{sid}", headers=headers).json()
        if scan["status"] in {"COMPLETED", "FAILED"}:
            return scan
        time.sleep(0.2)
    raise AssertionError("scan did not finish")


CODE = "from django.utils.timezone import utc\n\nSTAMP = utc\n"


def test_full_flow(client):
    h = auth(client)
    assert client.get("/api/auth/me", headers=h).json()["email"] == "dev@example.com"
    pid = client.post("/api/projects", json={"name": "shop"}, headers=h).json()["id"]
    r = client.post(f"/api/projects/{pid}/scans", headers=h,
                    json={"files": [{"path": "views.py", "content": CODE}],
                          "retriever": "exact"})
    assert r.status_code == 202 and r.json()["status"] in {"PENDING", "RUNNING", "COMPLETED"}
    scan = wait(client, h, r.json()["id"])
    assert scan["status"] == "COMPLETED", scan["error"]
    lines = {f["line"] for f in scan["result"]["findings"]}
    assert 1 in lines
    assert scan["sources"][0]["path"] == "views.py"
    md = client.get(f"/api/scans/{scan['id']}/report.md", headers=h)
    assert md.status_code == 200 and "django.utils.timezone.utc" in md.text
    pdf = client.get(f"/api/scans/{scan['id']}/report.pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    hist = client.get(f"/api/projects/{pid}/scans", headers=h).json()
    assert len(hist) == 1


def test_zip_upload(client):
    h = auth(client)
    pid = client.post("/api/projects", json={"name": "z"}, headers=h).json()["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("proj/app.py", CODE)
        zf.writestr("proj/.venv/lib.py", "import django\n")
    r = client.post(f"/api/projects/{pid}/scans/upload", headers=h,
                    files={"file": ("proj.zip", buf.getvalue(), "application/zip")},
                    data={"retriever": "exact"})
    assert r.status_code == 202, r.text
    scan = wait(client, h, r.json()["id"])
    assert scan["status"] == "COMPLETED"
    assert [s["path"] for s in scan["sources"]] == ["proj/app.py"]


def test_auth_and_isolation(client):
    assert client.get("/api/projects").status_code == 401
    h1 = auth(client, "a@example.com")
    h2 = auth(client, "b@example.com")
    pid = client.post("/api/projects", json={"name": "private"}, headers=h1).json()["id"]
    assert client.get(f"/api/projects/{pid}/scans", headers=h2).status_code == 404
    bad = client.post("/api/auth/token", data={"username": "a@example.com", "password": "nope"})
    assert bad.status_code == 401
    dup = client.post("/api/auth/register", json={"email": "a@example.com",
                                                  "password": "whatever123"})
    assert dup.status_code == 409


def test_validation(client):
    h = auth(client)
    pid = client.post("/api/projects", json={"name": "v"}, headers=h).json()["id"]
    r = client.post(f"/api/projects/{pid}/scans", headers=h,
                    json={"files": [{"path": "a.py", "content": "x=1"}], "from_version": "5.1",
                          "to_version": "4.0"})
    assert r.status_code == 422
    r = client.post(f"/api/projects/{pid}/scans", headers=h,
                    json={"files": [{"path": "a.py", "content": "x=1"}], "provider": "magic"})
    assert r.status_code == 422
    assert client.get("/api/meta").json()["default"] == {"from": "4.0", "to": "5.1"}
