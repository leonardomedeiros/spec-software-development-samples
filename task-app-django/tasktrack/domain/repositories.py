from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from ..domain.entities import Contract, Project, Requirement, Task, User


class IUserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    def list_all(self) -> List[User]:
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        pass


class IProjectRepository(ABC):
    @abstractmethod
    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        pass

    @abstractmethod
    def list_all(self) -> List[Project]:
        pass

    @abstractmethod
    def save(self, project: Project) -> Project:
        pass

    @abstractmethod
    def next_display_id(self) -> str:
        pass

    @abstractmethod
    def list_team_members(self, project_id: UUID) -> List[User]:
        pass

    @abstractmethod
    def add_team_member(self, project_id: UUID, user_id: UUID) -> None:
        pass

    @abstractmethod
    def remove_team_member(self, project_id: UUID, user_id: UUID) -> None:
        pass

    @abstractmethod
    def delete(self, project_id: UUID) -> None:
        pass


class IContractRepository(ABC):
    @abstractmethod
    def get_by_id(self, contract_id: UUID) -> Optional[Contract]:
        pass

    @abstractmethod
    def list_all(self) -> List[Contract]:
        pass

    @abstractmethod
    def save(self, contract: Contract) -> Contract:
        pass

    @abstractmethod
    def next_display_id(self) -> str:
        pass

    @abstractmethod
    def delete(self, contract_id: UUID) -> None:
        pass


class ITaskRepository(ABC):
    @abstractmethod
    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        pass

    @abstractmethod
    def list_all(self) -> List[Task]:
        pass

    @abstractmethod
    def list_by_project(self, project_id: UUID) -> List[Task]:
        pass

    @abstractmethod
    def save(self, task: Task) -> Task:
        pass

    @abstractmethod
    def next_display_id(self) -> str:
        pass

    @abstractmethod
    def delete(self, task_id: UUID) -> None:
        pass


class IRequirementRepository(ABC):
    @abstractmethod
    def get_by_id(self, requirement_id: UUID) -> Optional[Requirement]:
        pass

    @abstractmethod
    def list_all(self) -> List[Requirement]:
        pass

    @abstractmethod
    def save(self, requirement: Requirement) -> Requirement:
        pass

    @abstractmethod
    def next_display_id(self) -> str:
        pass

    @abstractmethod
    def delete(self, requirement_id: UUID) -> None:
        pass

    @abstractmethod
    def list_linked_tasks(self, requirement_id: UUID) -> List[Task]:
        pass

    @abstractmethod
    def link_task(self, requirement_id: UUID, task_id: UUID) -> None:
        pass

    @abstractmethod
    def unlink_task(self, requirement_id: UUID, task_id: UUID) -> None:
        pass
