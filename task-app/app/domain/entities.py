from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class Project:
    id: UUID


@dataclass(frozen=True)
class User:
    id: UUID


@dataclass
class Task:
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: UUID | None
    due_date: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(cls, project_id: UUID, title: str, description: str | None,
               priority: TaskPriority, assignee_id: UUID | None,
               due_date: datetime) -> "Task":
        now = datetime.now(timezone.utc)
        return cls(uuid4(), project_id, title, description, TaskStatus.PENDING,
                   priority, assignee_id, due_date, now, now)