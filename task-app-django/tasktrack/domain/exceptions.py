class DomainError(Exception):
    """Exceção base para erros de domínio."""
    pass


class InvalidStatusTransitionError(DomainError):
    """Lançada quando ocorre uma transição inválida de status (RN-04 / CB-03)."""
    def __init__(self, message: str = "Tarefas concluídas não podem ter seu status alterado."):
        self.code = "INVALID_STATUS_TRANSITION"
        self.message = message
        super().__init__(self.message)


class ProjectNotFoundError(DomainError):
    """Lançada quando um projeto não é encontrado (CB-01)."""
    def __init__(self, message: str = "Projeto não encontrado"):
        self.message = message
        super().__init__(self.message)


class TaskNotFoundError(DomainError):
    """Lançada quando uma tarefa não é encontrada."""
    def __init__(self, message: str = "Tarefa não encontrada"):
        self.message = message
        super().__init__(self.message)


class UserNotFoundError(DomainError):
    """Lançada quando o usuário responsável/proprietário não existe (CB-04)."""
    def __init__(self, message: str = "Usuário atribuído não existe"):
        self.message = message
        super().__init__(self.message)
