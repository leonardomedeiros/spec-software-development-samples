from typing import Optional
from uuid import UUID

from django.db import transaction

from ..domain.entities import Actor, Contract, Project, Requirement, Task, User
from ..domain.enums import (
    ContractStatus,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
    TaskPriority,
    TaskStatus,
    UserRole,
)
from ..domain.repositories import (
    IActorRepository,
    IContractRepository,
    IProjectRepository,
    IRequirementRepository,
    ITaskRepository,
    IUserRepository,
)
from .models import (
    ActorModel,
    ActorRequirementLinkModel,
    ContractModel,
    IdentifierSequenceModel,
    ProjectMembershipModel,
    ProjectModel,
    RequirementModel,
    RequirementTaskLinkModel,
    TaskModel,
    UserModel,
)


def _next_sequence_value(prefix: str) -> int:
    """Gera o próximo número da sequência para um prefixo (ex: 'PRJ'), de forma atômica."""
    with transaction.atomic():
        sequence, _ = IdentifierSequenceModel.objects.select_for_update().get_or_create(prefix=prefix)
        sequence.last_value += 1
        sequence.save(update_fields=["last_value"])
        return sequence.last_value


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


class DjangoContractRepository(IContractRepository):
    def get_by_id(self, contract_id: UUID) -> Optional[Contract]:
        try:
            orm_contract = ContractModel.objects.get(id=contract_id)
            return Contract(
                id=orm_contract.id,
                display_id=orm_contract.display_id,
                title=orm_contract.title,
                description=orm_contract.description,
                contract_file=orm_contract.contract_file,
                status=ContractStatus(orm_contract.status),
                owner_id=orm_contract.owner_id,
                created_at=orm_contract.created_at,
            )
        except ContractModel.DoesNotExist:
            return None

    def list_all(self) -> list[Contract]:
        return [
            Contract(
                id=c.id,
                display_id=c.display_id,
                title=c.title,
                description=c.description,
                contract_file=c.contract_file,
                status=ContractStatus(c.status),
                owner_id=c.owner_id,
                created_at=c.created_at,
            )
            for c in ContractModel.objects.all().order_by("-created_at")
        ]

    def save(self, contract: Contract) -> Contract:
        orm_contract, _ = ContractModel.objects.update_or_create(
            id=contract.id,
            defaults={
                "display_id": contract.display_id,
                "title": contract.title,
                "description": contract.description,
                "contract_file": contract.contract_file,
                "status": contract.status.value,
                "owner_id": contract.owner_id,
            },
        )
        contract.created_at = orm_contract.created_at
        return contract

    def next_display_id(self) -> str:
        return f"CRT{_next_sequence_value('CRT')}"

    def delete(self, contract_id: UUID) -> None:
        ContractModel.objects.filter(id=contract_id).delete()


class DjangoProjectRepository(IProjectRepository):
    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        try:
            orm_proj = ProjectModel.objects.get(id=project_id)
            return Project(
                id=orm_proj.id,
                display_id=orm_proj.display_id,
                contract_id=orm_proj.contract_id,
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
                display_id=p.display_id,
                contract_id=p.contract_id,
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
                "display_id": project.display_id,
                "contract_id": project.contract_id,
                "title": project.title,
                "description": project.description,
                "owner_id": project.owner_id,
            },
        )
        project.created_at = orm_proj.created_at
        return project

    def next_display_id(self) -> str:
        return f"PRJ{_next_sequence_value('PRJ')}"

    def list_team_members(self, project_id: UUID) -> list[User]:
        return [
            User(
                id=membership.user.id,
                name=membership.user.name,
                email=membership.user.email,
                role=UserRole(membership.user.role),
                created_at=membership.user.created_at,
            )
            for membership in ProjectMembershipModel.objects.filter(project_id=project_id).select_related("user").order_by("user__name")
        ]

    def add_team_member(self, project_id: UUID, user_id: UUID) -> None:
        ProjectMembershipModel.objects.get_or_create(project_id=project_id, user_id=user_id)

    def remove_team_member(self, project_id: UUID, user_id: UUID) -> None:
        ProjectMembershipModel.objects.filter(project_id=project_id, user_id=user_id).delete()

    def delete(self, project_id: UUID) -> None:
        ProjectModel.objects.filter(id=project_id).delete()


class DjangoTaskRepository(ITaskRepository):
    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        try:
            orm_task = TaskModel.objects.get(id=task_id)
            return Task(
                id=orm_task.id,
                display_id=orm_task.display_id,
                project_id=orm_task.project_id,
                title=orm_task.title,
                description=orm_task.description,
                status=TaskStatus(orm_task.status),
                priority=TaskPriority(orm_task.priority),
                assignee_id=orm_task.assignee_id,
                due_date=orm_task.due_date,
                github_url=orm_task.github_url,
                created_at=orm_task.created_at,
                updated_at=orm_task.updated_at,
            )
        except TaskModel.DoesNotExist:
            return None

    def list_all(self) -> list[Task]:
        return [
            Task(
                id=t.id,
                display_id=t.display_id,
                project_id=t.project_id,
                title=t.title,
                description=t.description,
                status=TaskStatus(t.status),
                priority=TaskPriority(t.priority),
                assignee_id=t.assignee_id,
                due_date=t.due_date,
                github_url=t.github_url,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in TaskModel.objects.all().order_by("due_date")
        ]

    def list_by_project(self, project_id: UUID) -> list[Task]:
        return [
            Task(
                id=t.id,
                display_id=t.display_id,
                project_id=t.project_id,
                title=t.title,
                description=t.description,
                status=TaskStatus(t.status),
                priority=TaskPriority(t.priority),
                assignee_id=t.assignee_id,
                due_date=t.due_date,
                github_url=t.github_url,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in TaskModel.objects.filter(project_id=project_id).order_by("due_date")
        ]

    def save(self, task: Task) -> Task:
        orm_task, _ = TaskModel.objects.update_or_create(
            id=task.id,
            defaults={
                "display_id": task.display_id,
                "project_id": task.project_id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "assignee_id": task.assignee_id,
                "due_date": task.due_date,
                "github_url": task.github_url,
            },
        )
        task.created_at = orm_task.created_at
        task.updated_at = orm_task.updated_at
        return task

    def next_display_id(self) -> str:
        return f"TSK{_next_sequence_value('TSK')}"

    def delete(self, task_id: UUID) -> None:
        TaskModel.objects.filter(id=task_id).delete()


class DjangoRequirementRepository(IRequirementRepository):
    def get_by_id(self, requirement_id: UUID) -> Optional[Requirement]:
        try:
            orm_req = RequirementModel.objects.get(id=requirement_id)
            return Requirement(
                id=orm_req.id,
                display_id=orm_req.display_id,
                code=orm_req.code,
                title=orm_req.title,
                description=orm_req.description,
                type=RequirementType(orm_req.req_type),
                priority=RequirementPriority(orm_req.priority),
                status=RequirementStatus(orm_req.status),
                created_at=orm_req.created_at,
            )
        except RequirementModel.DoesNotExist:
            return None

    def list_all(self) -> list[Requirement]:
        return [
            Requirement(
                id=r.id,
                display_id=r.display_id,
                code=r.code,
                title=r.title,
                description=r.description,
                type=RequirementType(r.req_type),
                priority=RequirementPriority(r.priority),
                status=RequirementStatus(r.status),
                created_at=r.created_at,
            )
            for r in RequirementModel.objects.all().order_by("code")
        ]

    def save(self, requirement: Requirement) -> Requirement:
        orm_req, _ = RequirementModel.objects.update_or_create(
            id=requirement.id,
            defaults={
                "display_id": requirement.display_id,
                "code": requirement.code,
                "title": requirement.title,
                "description": requirement.description,
                "req_type": requirement.type.value,
                "priority": requirement.priority.value,
                "status": requirement.status.value,
            },
        )
        requirement.created_at = orm_req.created_at
        return requirement

    def next_display_id(self) -> str:
        return f"REQ{_next_sequence_value('REQ')}"

    def delete(self, requirement_id: UUID) -> None:
        RequirementModel.objects.filter(id=requirement_id).delete()

    def list_linked_tasks(self, requirement_id: UUID) -> list[Task]:
        return [
            Task(
                id=link.task.id,
                project_id=link.task.project_id,
                title=link.task.title,
                description=link.task.description,
                status=TaskStatus(link.task.status),
                priority=TaskPriority(link.task.priority),
                assignee_id=link.task.assignee_id,
                due_date=link.task.due_date,
                github_url=link.task.github_url,
                created_at=link.task.created_at,
                updated_at=link.task.updated_at,
            )
            for link in RequirementTaskLinkModel.objects.filter(requirement_id=requirement_id)
                .select_related("task").order_by("task__due_date")
        ]

    def link_task(self, requirement_id: UUID, task_id: UUID) -> None:
        RequirementTaskLinkModel.objects.get_or_create(requirement_id=requirement_id, task_id=task_id)

    def unlink_task(self, requirement_id: UUID, task_id: UUID) -> None:
        RequirementTaskLinkModel.objects.filter(requirement_id=requirement_id, task_id=task_id).delete()

    def list_linked_actors(self, requirement_id: UUID) -> list[Actor]:
        return [
            Actor(
                id=link.actor.id,
                display_id=link.actor.display_id,
                name=link.actor.name,
                description=link.actor.description,
                created_at=link.actor.created_at,
            )
            for link in ActorRequirementLinkModel.objects.filter(requirement_id=requirement_id)
                .select_related("actor").order_by("actor__name")
        ]

    def link_actor(self, requirement_id: UUID, actor_id: UUID) -> None:
        ActorRequirementLinkModel.objects.get_or_create(requirement_id=requirement_id, actor_id=actor_id)

    def unlink_actor(self, requirement_id: UUID, actor_id: UUID) -> None:
        ActorRequirementLinkModel.objects.filter(requirement_id=requirement_id, actor_id=actor_id).delete()


class DjangoActorRepository(IActorRepository):
    def get_by_id(self, actor_id: UUID) -> Optional[Actor]:
        try:
            orm_actor = ActorModel.objects.get(id=actor_id)
            return Actor(
                id=orm_actor.id,
                display_id=orm_actor.display_id,
                name=orm_actor.name,
                description=orm_actor.description,
                created_at=orm_actor.created_at,
            )
        except ActorModel.DoesNotExist:
            return None

    def list_all(self) -> list[Actor]:
        return [
            Actor(
                id=a.id,
                display_id=a.display_id,
                name=a.name,
                description=a.description,
                created_at=a.created_at,
            )
            for a in ActorModel.objects.all().order_by("name")
        ]

    def save(self, actor: Actor) -> Actor:
        orm_actor, _ = ActorModel.objects.update_or_create(
            id=actor.id,
            defaults={
                "display_id": actor.display_id,
                "name": actor.name,
                "description": actor.description,
            },
        )
        actor.created_at = orm_actor.created_at
        return actor

    def next_display_id(self) -> str:
        return f"ACT{_next_sequence_value('ACT')}"

    def delete(self, actor_id: UUID) -> None:
        ActorModel.objects.filter(id=actor_id).delete()

    def list_linked_requirements(self, actor_id: UUID) -> list[Requirement]:
        return [
            Requirement(
                id=link.requirement.id,
                display_id=link.requirement.display_id,
                code=link.requirement.code,
                title=link.requirement.title,
                description=link.requirement.description,
                type=RequirementType(link.requirement.req_type),
                priority=RequirementPriority(link.requirement.priority),
                status=RequirementStatus(link.requirement.status),
                created_at=link.requirement.created_at,
            )
            for link in ActorRequirementLinkModel.objects.filter(actor_id=actor_id)
                .select_related("requirement").order_by("requirement__code")
        ]
