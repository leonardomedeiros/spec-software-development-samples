from datetime import datetime, timezone
from uuid import UUID, uuid4

from ..domain.entities import Contract, Project, Task
from ..domain.enums import ContractStatus, ProjectStatus, TaskStatus
from ..domain.exceptions import (
    ContractNotFoundError,
    InvalidStatusTransitionError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from ..domain.repositories import IContractRepository, IProjectRepository, ITaskRepository, IUserRepository
from ..schemas.schemas import (
    CreateContractSchema,
    CreateProjectSchema,
    CreateTaskSchema,
    UpdateContractStatusSchema,
    UpdateProjectStatusSchema,
    UpdateTaskStatusSchema,
)


class CreateContractUseCase:
    def __init__(self, contract_repo: IContractRepository, user_repo: IUserRepository):
        self.contract_repo = contract_repo
        self.user_repo = user_repo

    def execute(self, dto: CreateContractSchema) -> Contract:
        owner = self.user_repo.get_by_id(dto.owner_id)
        if not owner:
            raise UserNotFoundError("Usuário proprietário não encontrado.")

        contract = Contract(
            id=uuid4(),
            title=dto.title,
            description=dto.description or "",
            contract_file=dto.contract_file,
            owner_id=dto.owner_id,
            created_at=datetime.now(timezone.utc),
        )
        return self.contract_repo.save(contract)


class CreateProjectUseCase:
    def __init__(self, project_repo: IProjectRepository, user_repo: IUserRepository, contract_repo: IContractRepository):
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.contract_repo = contract_repo

    def execute(self, dto: CreateProjectSchema) -> Project:
        owner = self.user_repo.get_by_id(dto.owner_id)
        if not owner:
            raise UserNotFoundError("Usuário proprietário não encontrado.")
        if not self.contract_repo.get_by_id(dto.contract_id):
            raise ProjectNotFoundError("Contrato não encontrado")

        project = Project(
            id=uuid4(),
            contract_id=dto.contract_id,
            title=dto.title,
            description=dto.description or "",
            owner_id=dto.owner_id,
            created_at=datetime.now(timezone.utc),
        )
        return self.project_repo.save(project)


class AddProjectTeamMemberUseCase:
    def __init__(self, project_repo: IProjectRepository, user_repo: IUserRepository):
        self.project_repo = project_repo
        self.user_repo = user_repo

    def execute(self, project_id: UUID, user_id: UUID) -> None:
        if not self.project_repo.get_by_id(project_id):
            raise ProjectNotFoundError()
        if not self.user_repo.get_by_id(user_id):
            raise UserNotFoundError("Usuário da equipe não existe")
        self.project_repo.add_team_member(project_id, user_id)


class RemoveProjectTeamMemberUseCase:
    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    def execute(self, project_id: UUID, user_id: UUID) -> None:
        if not self.project_repo.get_by_id(project_id):
            raise ProjectNotFoundError()
        self.project_repo.remove_team_member(project_id, user_id)


class UpdateContractStatusUseCase:
    def __init__(self, contract_repo: IContractRepository):
        self.contract_repo = contract_repo

    def execute(self, contract_id: UUID, dto: UpdateContractStatusSchema) -> Contract:
        contract = self.contract_repo.get_by_id(contract_id)
        if not contract:
            raise ContractNotFoundError()
        contract.change_status(dto.status)
        return self.contract_repo.save(contract)


class UpdateProjectStatusUseCase:
    def __init__(self, project_repo: IProjectRepository, task_repo: ITaskRepository):
        self.project_repo = project_repo
        self.task_repo = task_repo

    def execute(self, project_id: UUID, dto: UpdateProjectStatusSchema) -> list[Task]:
        if not self.project_repo.get_by_id(project_id):
            raise ProjectNotFoundError("Projeto não encontrado")

        tasks = self.task_repo.list_by_project(project_id)
        if not tasks:
            raise InvalidStatusTransitionError("Não é possível alterar o status de um projeto sem tarefas.")
        if dto.status == ProjectStatus.PENDING:
            if any(task.status == TaskStatus.COMPLETED for task in tasks):
                raise InvalidStatusTransitionError("Projeto com tarefas concluídas não pode voltar para PENDING.")
            for task in tasks:
                task.change_status(TaskStatus.PENDING)
        elif dto.status == ProjectStatus.IN_PROGRESS:
            if any(task.status == TaskStatus.COMPLETED for task in tasks):
                raise InvalidStatusTransitionError("Projeto com tarefas concluídas não pode voltar para IN_PROGRESS.")
            for task in tasks:
                task.change_status(TaskStatus.IN_PROGRESS)
        else:
            for task in tasks:
                if task.status == TaskStatus.PENDING:
                    task.change_status(TaskStatus.IN_PROGRESS)
                if task.status == TaskStatus.IN_PROGRESS:
                    task.change_status(TaskStatus.COMPLETED)
        for task in tasks:
            self.task_repo.save(task)
        return tasks


class CreateTaskUseCase:
    def __init__(
        self,
        task_repo: ITaskRepository,
        project_repo: IProjectRepository,
        user_repo: IUserRepository,
    ):
        self.task_repo = task_repo
        self.project_repo = project_repo
        self.user_repo = user_repo

    def execute(self, project_id: UUID, dto: CreateTaskSchema) -> Task:
        # CB-01: Projeto inexistente
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError("Projeto não encontrado")

        # RN-05 / CB-04: Atribuição de responsável
        if dto.assignee_id:
            assignee = self.user_repo.get_by_id(dto.assignee_id)
            if not assignee:
                raise UserNotFoundError("Usuário atribuído não existe")

        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid4(),
            project_id=project_id,
            title=dto.title,
            description=dto.description or "",
            status=TaskStatus.PENDING,
            priority=dto.priority,
            assignee_id=dto.assignee_id,
            due_date=dto.due_date,
            created_at=now,
            updated_at=now,
        )
        return self.task_repo.save(task)


class UpdateTaskStatusUseCase:
    def __init__(self, task_repo: ITaskRepository):
        self.task_repo = task_repo

    def execute(self, task_id: UUID, dto: UpdateTaskStatusSchema) -> Task:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError("Tarefa não encontrada")

        # RN-04 / CB-03: Valida a transição de status no domínio
        task.change_status(dto.status)
        return self.task_repo.save(task)


class UpdateTaskUseCase:
    def __init__(self, task_repo: ITaskRepository, user_repo: IUserRepository):
        self.task_repo = task_repo
        self.user_repo = user_repo

    def execute(self, task_id: UUID, dto) -> Task:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError("Tarefa não encontrada")

        if dto.title is not None:
            task.title = dto.title
        if dto.description is not None:
            task.description = dto.description
        if dto.priority is not None:
            task.priority = dto.priority
        if dto.assignee_id is not None:
            assignee = self.user_repo.get_by_id(dto.assignee_id)
            if not assignee:
                raise UserNotFoundError("Usuário atribuído não existe")
            task.assignee_id = dto.assignee_id
        if dto.due_date is not None:
            task.due_date = dto.due_date

        task.updated_at = datetime.now(timezone.utc)
        return self.task_repo.save(task)


class DeleteTaskUseCase:
    def __init__(self, task_repo: ITaskRepository):
        self.task_repo = task_repo

    def execute(self, task_id: UUID) -> None:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError("Tarefa não encontrada")
        self.task_repo.delete(task_id)
