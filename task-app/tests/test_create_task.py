from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.entities import Project, User
from app.main import app, projects, users


@pytest.fixture(autouse=True)
def clear_repositories() -> None:
    projects._projects.clear()
    users._users.clear()


@pytest.mark.asyncio
async def test_create_task_returns_created_task_with_pending_status() -> None:
    project_id = UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")
    projects.add(Project(id=project_id))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/projects/{project_id}/tasks", json={
            "title": "Criar Testes de Integração",
            "description": "Cobrir casos felizes e de erro.",
            "priority": "HIGH",
            "due_date": "2099-12-31T23:59:59Z",
        })
    body = response.json()
    assert response.status_code == 201
    assert UUID(body["id"])
    assert body["status"] == "PENDING"
    assert body["project_id"] == str(project_id)


@pytest.mark.asyncio
async def test_create_task_rejects_past_due_date() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/projects/{uuid4()}/tasks", json={
            "title": "Tarefa válida", "due_date": "2020-01-01T00:00:00Z"
        })
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "A data de vencimento não pode ser no passado."


@pytest.mark.asyncio
async def test_create_task_returns_404_for_unknown_project() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/projects/{uuid4()}/tasks", json={
            "title": "Tarefa válida", "due_date": "2099-01-01T00:00:00Z"
        })
    assert response.status_code == 404
    assert response.json() == {"detail": "Projeto não encontrado"}


@pytest.mark.asyncio
async def test_create_task_returns_404_for_unknown_assignee() -> None:
    project_id = uuid4()
    projects.add(Project(id=project_id))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/projects/{project_id}/tasks", json={
            "title": "Tarefa válida", "assignee_id": str(uuid4()),
            "due_date": "2099-01-01T00:00:00Z"
        })
    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário atribuído não existe"}


@pytest.mark.asyncio
async def test_create_task_accepts_existing_assignee() -> None:
    project_id = uuid4()
    user_id = uuid4()
    projects.add(Project(id=project_id))
    users.add(User(id=user_id))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/projects/{project_id}/tasks", json={
            "title": "Tarefa válida", "assignee_id": str(user_id),
            "due_date": datetime(2099, 1, 1, tzinfo=timezone.utc).isoformat()
        })
    assert response.status_code == 201
    assert response.json()["assignee_id"] == str(user_id)