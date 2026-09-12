from uuid import UUID

from app.domain.entities import Project, Task, User


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[UUID, Project] = {}

    def add(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project

    def exists(self, project_id: UUID) -> bool:
        return project_id in self._projects


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    def add(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def exists(self, user_id: UUID) -> bool:
        return user_id in self._users


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task