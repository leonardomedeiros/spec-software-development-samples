from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from ..domain.enums import ContractStatus, ProjectStatus, TaskPriority, TaskStatus


class ContractResponseSchema(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    contract_file: Optional[str] = None
    status: ContractStatus
    owner_id: UUID
    created_at: datetime


class CreateContractSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    contract_file: Optional[str] = Field(None, max_length=255)
    owner_id: UUID

    @field_validator("title")
    @classmethod
    def validate_contract_title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O título não pode ser composto apenas por espaços em branco.")
        return v.strip()


class UpdateContractStatusSchema(BaseModel):
    status: ContractStatus


class UpdateProjectStatusSchema(BaseModel):
    status: ProjectStatus


class CreateProjectSchema(BaseModel):
    contract_id: UUID
    title: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    owner_id: UUID

    @field_validator("title")
    @classmethod
    def validate_title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O título não pode ser composto apenas por espaços em branco.")
        return v.strip()


class ProjectResponseSchema(BaseModel):
    id: UUID
    contract_id: UUID
    title: str
    description: Optional[str] = None
    owner_id: UUID
    created_at: datetime


class CreateTaskSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: Optional[UUID] = None
    due_date: datetime

    @field_validator("title")
    @classmethod
    def validate_task_title(cls, v: str) -> str:
        # RN-01: 3 a 100 caracteres e não apenas espaços
        clean_val = v.strip()
        if len(clean_val) < 3:
            raise ValueError("O título da tarefa deve conter no mínimo 3 caracteres válidos.")
        return clean_val

    @field_validator("due_date")
    @classmethod
    def validate_due_date_future(cls, v: datetime) -> datetime:
        # RN-02 / CB-02: data no futuro
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v_cmp = v.replace(tzinfo=timezone.utc)
        else:
            v_cmp = v

        if v_cmp <= now:
            raise ValueError("A data de vencimento não pode ser no passado.")
        return v


class UpdateTaskStatusSchema(BaseModel):
    status: TaskStatus


class TaskResponseSchema(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: Optional[UUID] = None
    due_date: datetime
    created_at: datetime
    updated_at: datetime
