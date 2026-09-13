"""Helpers for authenticated API tests. Not production seed logic."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import hash_password


def create_test_user(
    session: Session,
    *,
    role: UserRole,
    password: str = "test-password-123",
    name: str | None = None,
) -> tuple[User, str]:
    suffix = uuid.uuid4().hex[:8]
    email = f"{role.value.lower()}-{suffix}@example.invalid"
    user = User(
        name=name or f"{role.value} {suffix}",
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user, password


def login_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        raise AssertionError(f"login failed: {response.status_code} {response.text}")
    token = response.json()["access_token"]
    body = response.json()
    if "password_hash" in body or "password_hash" in str(body.get("user", {})):
        raise AssertionError("password_hash leaked in login response")
    return {"Authorization": f"Bearer {token}"}
