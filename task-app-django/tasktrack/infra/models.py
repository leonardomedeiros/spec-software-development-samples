import uuid
from django.db import models


class UserModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    role = models.CharField(
        max_length=20,
        choices=[("ADMIN", "ADMIN"), ("MEMBER", "MEMBER")],
        default="MEMBER",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"


class ContractModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tasks"
