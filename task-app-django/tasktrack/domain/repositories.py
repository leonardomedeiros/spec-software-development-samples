from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from ..domain.entities import Contract, Project, Task, User


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
    def list_team_members(self, project_id: UUID) -> List[User]:
        pass

    @abstractmethod
    def add_team_member(self, project_id: UUID, user_id: UUID) -> None:
        pass

    @abstractmethod
    def remove_team_member(self, project_id: UUID, user_id: UUID) -> None:
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
