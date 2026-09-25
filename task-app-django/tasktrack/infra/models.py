import uuid
from django.db import models


class UserModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    role = models.CharField(
        max_length=20,
        choices=[
            ("ADMIN", "ADMIN"),
            ("MEMBER", "MEMBER"),
            ("DEVELOPER", "DEVELOPER"),
            ("TEST", "TEST"),
            ("MANAGER", "MANAGER"),
            ("PRODUCT_OWNER", "PRODUCT_OWNER"),
        ],
        default="MEMBER",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"


class IdentifierSequenceModel(models.Model):
    prefix = models.CharField(max_length=10, primary_key=True)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "identifier_sequences"


class ContractModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=20, unique=True, editable=False, null=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    contract_file = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Caminho do arquivo do contrato (ex: PDF).",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("PROSPECTING", "PROSPECTING"),
            ("IN_PROGRESS", "IN_PROGRESS"),
            ("SIGNED", "SIGNED"),
        ],
        default="PROSPECTING",
    )
    owner = models.ForeignKey(UserModel, on_delete=models.RESTRICT, related_name="contracts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contracts"


class ProjectModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=20, unique=True, editable=False, null=True)
    contract = models.ForeignKey(ContractModel, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(UserModel, on_delete=models.RESTRICT, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects"


class ProjectMembershipModel(models.Model):
    project = models.ForeignKey(ProjectModel, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="project_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_memberships"
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_project_member"),
        ]


class TaskModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=20, unique=True, editable=False, null=True)
    project = models.ForeignKey(ProjectModel, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "PENDING"),
            ("IN_PROGRESS", "IN_PROGRESS"),
            ("COMPLETED", "COMPLETED"),
        ],
        default="PENDING",
    )
    priority = models.CharField(
        max_length=10,
        choices=[
            ("LOW", "LOW"),
            ("MEDIUM", "MEDIUM"),
            ("HIGH", "HIGH"),
        ],
        default="MEDIUM",
    )
    assignee = models.ForeignKey(
        UserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    github_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="URL relativa a esta tarefa no GitHub (issue, PR, etc)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tasks"


class RequirementModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=20, unique=True, editable=False, null=True)
    project = models.ForeignKey(ProjectModel, on_delete=models.CASCADE, related_name="requirements")
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    req_type = models.CharField(
        max_length=25,
        choices=[
            ("FUNCTIONAL", "FUNCTIONAL"),
            ("NON_FUNCTIONAL", "NON_FUNCTIONAL"),
            ("BUSINESS_RULE", "BUSINESS_RULE"),
            ("TECHNICAL_CONSTRAINT", "TECHNICAL_CONSTRAINT"),
        ],
        default="FUNCTIONAL",
    )
    priority = models.CharField(
        max_length=10,
        choices=[
            ("LOW", "LOW"),
            ("MEDIUM", "MEDIUM"),
            ("HIGH", "HIGH"),
        ],
        default="MEDIUM",
    )
    status = models.CharField(
        max_length=15,
        choices=[
            ("DRAFT", "DRAFT"),
            ("APPROVED", "APPROVED"),
            ("IMPLEMENTED", "IMPLEMENTED"),
            ("DEPRECATED", "DEPRECATED"),
        ],
        default="DRAFT",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "requirements"


class RequirementTaskLinkModel(models.Model):
    requirement = models.ForeignKey(RequirementModel, on_delete=models.CASCADE, related_name="task_links")
    task = models.ForeignKey(TaskModel, on_delete=models.CASCADE, related_name="requirement_links")
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "requirement_task_links"
        constraints = [
            models.UniqueConstraint(fields=["requirement", "task"], name="unique_requirement_task"),
        ]


class ActorModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.CharField(max_length=20, unique=True, editable=False, null=True)
    contract = models.ForeignKey(ContractModel, on_delete=models.CASCADE, related_name="actors")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "actors"


class ActorRequirementLinkModel(models.Model):
    actor = models.ForeignKey(ActorModel, on_delete=models.CASCADE, related_name="requirement_links")
    requirement = models.ForeignKey(RequirementModel, on_delete=models.CASCADE, related_name="actor_links")
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "actor_requirement_links"
        constraints = [
            models.UniqueConstraint(fields=["actor", "requirement"], name="unique_actor_requirement"),
        ]


class TaskHistoryModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(TaskModel, on_delete=models.CASCADE, related_name="history")
    changed_by = models.ForeignKey(UserModel, on_delete=models.RESTRICT, related_name="task_changes")
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "task_history"
        ordering = ["-changed_at"]
