from typing import Protocol
from uuid import UUID

from app.domain.entities import Task


class ProjectRepository(Protocol):
    def exists(self, project_id: UUID) -> bool: ...


class UserRepository(Protocol):
    def exists(self, user_id: UUID) -> bool: ...


class TaskRepository(Protocol):
    def add(self, task: Task) -> Task: ...