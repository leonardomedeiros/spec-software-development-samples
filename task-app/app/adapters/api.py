from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.exceptions import AssigneeNotFoundError, ProjectNotFoundError
from app.application.use_cases import CreateTask, CreateTaskInput
from app.domain.entities import Task, TaskPriority, TaskStatus


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None
    due_date: datetime

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O título não pode ser composto apenas por espaços em branco.")
        return value

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_future(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        if value <= datetime.now(timezone.utc):
            raise ValueError("A data de vencimento não pode ser no passado.")
        return value


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: UUID | None
    due_date: datetime
    created_at: datetime
    updated_at: datetime


def build_router(create_task: CreateTask) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def get_create_task() -> CreateTask:
        return create_task

    @router.post(
        "/projects/{project_id}/tasks",
        response_model=TaskResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_task_endpoint(
        project_id: UUID,
        request: CreateTaskRequest,
        use_case: Annotated[CreateTask, Depends(get_create_task)],
    ) -> Task:
        try:
            return use_case.execute(CreateTaskInput(
                project_id=project_id,
                title=request.title,
                description=request.description,
                priority=request.priority,
                assignee_id=request.assignee_id,
                due_date=request.due_date,
            ))
        except ProjectNotFoundError as error:
            raise HTTPException(status_code=404, detail="Projeto não encontrado") from error
        except AssigneeNotFoundError as error:
            raise HTTPException(status_code=404, detail="Usuário atribuído não existe") from error

    return router