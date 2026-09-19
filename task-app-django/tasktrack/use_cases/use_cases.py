from datetime import datetime, timezone
from uuid import UUID, uuid4

from ..domain.entities import Contract, Project, Task
from ..domain.enums import TaskStatus
from ..domain.exceptions import ProjectNotFoundError, TaskNotFoundError, UserNotFoundError
from ..domain.repositories import IContractRepository, IProjectRepository, ITaskRepository, IUserRepository
from ..schemas.schemas import CreateContractSchema, CreateProjectSchema, CreateTaskSchema, UpdateTaskStatusSchema


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
    def __init__(self, project_repo: IProjectRepository, user_repo: IUserRepository):
        self.project_repo = project_repo
        self.user_repo = user_repo

    def execute(self, dto: CreateProjectSchema) -> Project:
        owner = self.user_repo.get_by_id(dto.owner_id)
        if not owner:
            raise UserNotFoundError("Usuário proprietário não encontrado.")

        project = Project(
            id=uuid4(),
            title=dto.title,
            description=dto.description or "",
            owner_id=dto.owner_id,
            created_at=datetime.now(timezone.utc),
        )
        return self.project_repo.save(project)


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
