from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ContractStatus(str, Enum):
    PROSPECTING = "PROSPECTING"
    IN_PROGRESS = "IN_PROGRESS"
    SIGNED = "SIGNED"


class ProjectStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    DEVELOPER = "DEVELOPER"
    TEST = "TEST"
    MANAGER = "MANAGER"
    PRODUCT_OWNER = "PRODUCT_OWNER"


class RequirementType(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"
    NON_FUNCTIONAL = "NON_FUNCTIONAL"
    BUSINESS_RULE = "BUSINESS_RULE"
    TECHNICAL_CONSTRAINT = "TECHNICAL_CONSTRAINT"


class RequirementPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RequirementStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    IMPLEMENTED = "IMPLEMENTED"
    DEPRECATED = "DEPRECATED"
