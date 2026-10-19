"""共享测试夹具：每个测试用独立临时 SQLite，不污染开发库。"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

TMP_DB = Path(tempfile.gettempdir()) / "mcfit_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TMP_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.init_db import init_db  # noqa: E402
from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="function")
def client() -> TestClient:
    Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client: TestClient) -> dict:
    """注册并登录，返回含token 的请求头。"""
    r = client.post("/api/v1/auth/register",
                    json={"username": "tester", "password": "test123456",
                          "email": "t@t.dev"})
    assert r.status_code == 201, r.text
    return {"headers": {"Authorization": f"Bearer {r.json()['access_token']}"},
            "user": r.json()["user"],
            "tokens": r.json()}