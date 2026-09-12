from typing import Optional
from uuid import UUID

from ..domain.entities import Project, Task, User
from ..domain.enums import TaskPriority, TaskStatus, UserRole
from ..domain.repositories import IProjectRepository, ITaskRepository, IUserRepository
from .models import ProjectModel, TaskModel, UserModel


class DjangoUserRepository(IUserRepository):
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        try:
            orm_user = UserModel.objects.get(id=user_id)
            return User(
                id=orm_user.id,
                name=orm_user.name,
                email=orm_user.email,
                role=UserRole(orm_user.role),
                created_at=orm_user.created_at,
            )
        except UserModel.DoesNotExist:
            return None

    def list_all(self) -> list[User]:
        return [
            User(
                id=u.id,
                name=u.name,
                email=u.email,
                role=UserRole(u.role),
                created_at=u.created_at,
            )
            for u in UserModel.objects.all().order_by("name")
        ]

    def save(self, user: User) -> User:
        orm_user, _ = UserModel.objects.update_or_create(
            id=user.id,
            defaults={
                "name": user.name,
                "email": user.email,
                "role": user.role.value,
            },
        )
        user.created_at = orm_user.created_at
        return user


class DjangoProjectRepository(IProjectRepository):
    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        try:
            orm_proj = ProjectModel.objects.get(id=project_id)
            return Project(
                id=orm_proj.id,
                title=orm_proj.title,
                description=orm_proj.description,
                owner_id=orm_proj.owner_id,
                created_at=orm_proj.created_at,
            )
        except ProjectModel.DoesNotExist:
            return None

    def list_all(self) -> list[Project]:
        return [
            Project(
                id=p.id,
                title=p.title,
                description=p.description,
                owner_id=p.owner_id,
                created_at=p.created_at,
            )
            for p in ProjectModel.objects.all().order_by("-created_at")
        ]

    def save(self, project: Project) -> Project:
        orm_proj, _ = ProjectModel.objects.update_or_create(
            id=project.id,
            defaults={
                "title": project.title,
                "description": project.description,
                "owner_id": project.owner_id,
            },
        )
        project.created_at = orm_proj.created_at
        return project


class DjangoTaskRepository(ITaskRepository):
    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        try:
            orm_task = TaskModel.objects.get(id=task_id)
            return Task(
                id=orm_task.id,
                project_id=orm_task.project_id,
                title=orm_task.title,
                description=orm_task.description,
                status=TaskStatus(orm_task.status),
                priority=TaskPriority(orm_task.priority),
                assignee_id=orm_task.assignee_id,
                due_date=orm_task.due_date,
                created_at=orm_task.created_at,
                updated_at=orm_task.updated_at,
            )
        except TaskModel.DoesNotExist:
            return None

    def list_all(self) -> list[Task]:
        return [
            Task(
                id=t.id,
                project_id=t.project_id,
                title=t.title,
                description=t.description,
                status=TaskStatus(t.status),
                priority=TaskPriority(t.priority),
                assignee_id=t.assignee_id,
                due_date=t.due_date,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in TaskModel.objects.all().order_by("due_date")
        ]

    def list_by_project(self, project_id: UUID) -> list[Task]:
        return [
            Task(
                id=t.id,
                project_id=t.project_id,
                title=t.title,
                description=t.description,
                status=TaskStatus(t.status),
                priority=TaskPriority(t.priority),
                assignee_id=t.assignee_id,
                due_date=t.due_date,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in TaskModel.objects.filter(project_id=project_id).order_by("due_date")
        ]

    def save(self, task: Task) -> Task:
        orm_task, _ = TaskModel.objects.update_or_create(
            id=task.id,
            defaults={
                "project_id": task.project_id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "assignee_id": task.assignee_id,
                "due_date": task.due_date,
            },
        )
        task.created_at = orm_task.created_at
        task.updated_at = orm_task.updated_at
        return task
