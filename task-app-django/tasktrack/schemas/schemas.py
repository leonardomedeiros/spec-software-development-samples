from datetime import datetime, date, timezone
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from ..domain.enums import (
    ContractStatus,
    ProjectStatus,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
    TaskPriority,
    TaskStatus,
)


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


class UpdateContractSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    owner_id: Optional[UUID] = None

    @field_validator("title")
    @classmethod
    def validate_contract_title_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
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


class UpdateProjectSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    owner_id: Optional[UUID] = None

    @field_validator("title")
    @classmethod
    def validate_title_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
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
    due_date: Optional[date] = None

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
    def validate_due_date_future(cls, v: Optional[date]) -> Optional[date]:
        # RN-02 / CB-02: data no futuro (opcional)
        if v is None:
            return v

        from datetime import date as date_class
        today = date_class.today()
        if v <= today:
            raise ValueError("A data de vencimento não pode ser no passado.")
        return v


class UpdateTaskStatusSchema(BaseModel):
    status: TaskStatus


class UpdateTaskSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None
    github_url: Optional[str] = Field(None, max_length=255)

    @field_validator("title")
    @classmethod
    def validate_task_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean_val = v.strip()
        if len(clean_val) < 3:
            raise ValueError("O título da tarefa deve conter no mínimo 3 caracteres válidos.")
        return clean_val

    @field_validator("due_date")
    @classmethod
    def validate_due_date_future(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        from datetime import date as date_class
        today = date_class.today()
        if v <= today:
            raise ValueError("A data de vencimento não pode ser no passado.")
        return v

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            return None
        return v.strip()


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


class CreateRequirementSchema(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    title: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = None
    type: RequirementType
    priority: RequirementPriority = RequirementPriority.MEDIUM

    @field_validator("code")
    @classmethod
    def validate_code_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("O código do requisito não pode ser composto apenas por espaços em branco.")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_requirement_title(cls, v: str) -> str:
        clean_val = v.strip()
        if len(clean_val) < 3:
            raise ValueError("O título do requisito deve conter no mínimo 3 caracteres válidos.")
        return clean_val


class UpdateRequirementSchema(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = None
    type: Optional[RequirementType] = None
    priority: Optional[RequirementPriority] = None

    @field_validator("code")
    @classmethod
    def validate_code_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("O código do requisito não pode ser composto apenas por espaços em branco.")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_requirement_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean_val = v.strip()
        if len(clean_val) < 3:
            raise ValueError("O título do requisito deve conter no mínimo 3 caracteres válidos.")
        return clean_val


class UpdateRequirementStatusSchema(BaseModel):
    status: RequirementStatus


class RequirementResponseSchema(BaseModel):
    id: UUID
    code: str
    title: str
    description: Optional[str] = None
    type: RequirementType
    priority: RequirementPriority
    status: RequirementStatus
    created_at: datetime


class CreateActorSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_actor_name(cls, v: str) -> str:
        clean_val = v.strip()
        if len(clean_val) < 2:
            raise ValueError("O nome do ator deve conter no mínimo 2 caracteres válidos.")
        return clean_val


class UpdateActorSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_actor_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean_val = v.strip()
        if len(clean_val) < 2:
            raise ValueError("O nome do ator deve conter no mínimo 2 caracteres válidos.")
        return clean_val


class ActorResponseSchema(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
