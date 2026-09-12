from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.exceptions import AssigneeNotFoundError, ProjectNotFoundError
from app.application.ports import ProjectRepository, TaskRepository, UserRepository
from app.domain.entities import Task, TaskPriority


@dataclass(frozen=True)
class CreateTaskInput:
    project_id: UUID
    title: str
    description: str | None
    priority: TaskPriority
    assignee_id: UUID | None
    due_date: datetime


class CreateTask:
    def __init__(self, projects: ProjectRepository, users: UserRepository,
                 tasks: TaskRepository) -> None:
        self._projects = projects
        self._users = users
        self._tasks = tasks

    def execute(self, data: CreateTaskInput) -> Task:
        if not self._projects.exists(data.project_id):
            raise ProjectNotFoundError
        if data.assignee_id is not None and not self._users.exists(data.assignee_id):
            raise AssigneeNotFoundError
        task = Task.create(data.project_id, data.title.strip(), data.description,
                           data.priority, data.assignee_id, data.due_date)
        return self._tasks.add(task)