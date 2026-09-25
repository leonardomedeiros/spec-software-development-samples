class DomainError(Exception):
    """Exceção base para erros de domínio."""
    pass


class InvalidStatusTransitionError(DomainError):
    """Lançada quando ocorre uma transição inválida de status (RN-04 / CB-03)."""
    def __init__(self, message: str = "Transição de status inválida."):
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


class ContractNotFoundError(DomainError):
    """Lançada quando um contrato não é encontrado."""
    def __init__(self, message: str = "Contrato não encontrado"):
        self.message = message
        super().__init__(self.message)


class RequirementNotFoundError(DomainError):
    """Lançada quando um requisito não é encontrado."""
    def __init__(self, message: str = "Requisito não encontrado"):
        self.message = message
        super().__init__(self.message)


class ActorNotFoundError(DomainError):
    """Lançada quando um ator não é encontrado."""
    def __init__(self, message: str = "Ator não encontrado"):
        self.message = message
        super().__init__(self.message)
