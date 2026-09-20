from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .enums import ContractStatus, TaskPriority, TaskStatus, UserRole
from .exceptions import InvalidStatusTransitionError


@dataclass
class User:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    email: str = ""
    role: UserRole = UserRole.MEMBER
    created_at: Optional[datetime] = None


@dataclass
class Contract:
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    contract_file: Optional[str] = None
    status: ContractStatus = ContractStatus.PROSPECTING
    owner_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    def change_status(self, new_status: ContractStatus) -> None:
        allowed_transitions = {
            ContractStatus.PROSPECTING: [ContractStatus.IN_PROGRESS],
            ContractStatus.IN_PROGRESS: [ContractStatus.PROSPECTING, ContractStatus.SIGNED],
            ContractStatus.SIGNED: [],
        }
        if new_status != self.status and new_status not in allowed_transitions[self.status]:
            raise InvalidStatusTransitionError(
                f"Transição inválida de {self.status.value} para {new_status.value}."
            )
        self.status = new_status


@dataclass
class Project:
    id: UUID = field(default_factory=uuid4)
    contract_id: Optional[UUID] = None
    title: str = ""
    description: str = ""
    owner_id: Optional[UUID] = None
    created_at: Optional[datetime] = None


@dataclass
class Task:
    id: UUID = field(default_factory=uuid4)
    project_id: Optional[UUID] = None
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    github_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def change_status(self, new_status: TaskStatus) -> None:
        """
        RN-04 (Ciclo de Vida do Status):
        - Transições permitidas (todas as combinações):
            PENDING -> IN_PROGRESS
            PENDING -> COMPLETED
            IN_PROGRESS -> COMPLETED
            IN_PROGRESS -> PENDING
            COMPLETED -> PENDING
            COMPLETED -> IN_PROGRESS
        - Todas as transições são permitidas com rastreamento de histórico
        """
        if new_status != self.status:
            self.status = new_status
            self.updated_at = datetime.now()


@dataclass
class TaskHistory:
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    changed_by_id: UUID = field(default_factory=uuid4)
    field_name: str = ""
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: Optional[datetime] = None
