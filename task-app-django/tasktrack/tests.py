import uuid
from datetime import datetime, timedelta, timezone
from django.test import TestCase
import pytest

from tasktrack.domain.entities import Project, Task, User
from tasktrack.domain.enums import TaskPriority, TaskStatus, UserRole
from tasktrack.domain.exceptions import (
    InvalidStatusTransitionError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from tasktrack.schemas.schemas import (
    CreateProjectSchema,
    CreateTaskSchema,
    UpdateTaskStatusSchema,
)
from tasktrack.use_cases.use_cases import (
    CreateProjectUseCase,
    CreateTaskUseCase,
    UpdateTaskStatusUseCase,
)
from tasktrack.infra.repositories import (
    DjangoProjectRepository,
    DjangoTaskRepository,
    DjangoUserRepository,
)
from tasktrack.infra.models import UserModel, ProjectModel, TaskModel


class TaskTrackUnitAndIntegrationTests(TestCase):
    def setUp(self):
        self.user_repo = DjangoUserRepository()
        self.project_repo = DjangoProjectRepository()
        self.task_repo = DjangoTaskRepository()

        # Cria usuário base
        self.user = self.user_repo.save(
            User(
                id=uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"),
                name="Leonardo Admin",
                email="admin@tasktrack.com",
                role=UserRole.ADMIN,
            )
        )

        # Cria projeto base
        self.project = self.project_repo.save(
            Project(
                id=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
                title="Reformulação do E-commerce",
                description="Projeto focado na migração da vitrine.",
                owner_id=self.user.id,
            )
        )

    # -------------------------------------------------------------
    # DOMAIN UNIT TESTS
    # -------------------------------------------------------------
    def test_rn04_status_lifecycle_transitions(self):
        """RN-04: Testa transições válidas e proibição de transição após COMPLETED."""
        task = Task(title="Test Lifecycle", status=TaskStatus.PENDING)

        # PENDING -> IN_PROGRESS (Válido)
        task.change_status(TaskStatus.IN_PROGRESS)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

        # IN_PROGRESS -> PENDING (Válido)
        task.change_status(TaskStatus.PENDING)
        self.assertEqual(task.status, TaskStatus.PENDING)

        # PENDING -> IN_PROGRESS -> COMPLETED (Válido)
        task.change_status(TaskStatus.IN_PROGRESS)
        task.change_status(TaskStatus.COMPLETED)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

        # COMPLETED -> IN_PROGRESS (Proibido - CB-03)
        with self.assertRaises(InvalidStatusTransitionError):
            task.change_status(TaskStatus.IN_PROGRESS)

        # COMPLETED -> PENDING (Proibido)
        with self.assertRaises(InvalidStatusTransitionError):
            task.change_status(TaskStatus.PENDING)

    # -------------------------------------------------------------
    # USE CASE / SPECIFICATION ACCEPTANCE CRITERIA
    # -------------------------------------------------------------
    def test_scenario_1_create_task_success(self):
        """Cenário 1: Sucesso na Criação de Tarefa (Spec 5.1)."""
        future_date = datetime.now(timezone.utc) + timedelta(days=10)
        dto = CreateTaskSchema(
            title="Criar Testes de Integração",
            description="Cobrir casos felizes e de erro.",
            priority=TaskPriority.HIGH,
            due_date=future_date,
        )

        use_case = CreateTaskUseCase(self.task_repo, self.project_repo, self.user_repo)
        created_task = use_case.execute(self.project.id, dto)

        self.assertIsNotNone(created_task.id)
        self.assertEqual(created_task.status, TaskStatus.PENDING)
        self.assertEqual(created_task.title, "Criar Testes de Integração")

    def test_scenario_2_due_date_in_past_validation_error(self):
        """Cenário 2: Falha por Data Retroativa (CB-02 / Spec 5.2)."""
        past_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError) as context:
            CreateTaskSchema(
                title="Tarefa Passada",
                due_date=past_date,
            )
        self.assertIn("A data de vencimento não pode ser no passado.", str(context.exception))

    def test_scenario_3_invalid_status_transition_on_completed(self):
        """Cenário 3: Transição Inválida de Status (CB-03 / Spec 5.3)."""
        future_date = datetime.now(timezone.utc) + timedelta(days=5)
        task = self.task_repo.save(
            Task(
                project_id=self.project.id,
                title="Tarefa Concluída",
                status=TaskStatus.COMPLETED,
                due_date=future_date,
            )
        )

        use_case = UpdateTaskStatusUseCase(self.task_repo)
        dto = UpdateTaskStatusSchema(status=TaskStatus.IN_PROGRESS)

        with self.assertRaises(InvalidStatusTransitionError) as context:
            use_case.execute(task.id, dto)

        self.assertEqual(context.exception.code, "INVALID_STATUS_TRANSITION")
        self.assertIn("Tarefas concluídas não podem ter seu status alterado.", context.exception.message)

    def test_cb01_project_not_found(self):
        """CB-01: Projeto Inexistente ao criar tarefa."""
        future_date = datetime.now(timezone.utc) + timedelta(days=5)
        dto = CreateTaskSchema(
            title="Tarefa com projeto inválido",
            due_date=future_date,
        )
        use_case = CreateTaskUseCase(self.task_repo, self.project_repo, self.user_repo)

        non_existent_project = uuid.uuid4()
        with self.assertRaises(ProjectNotFoundError):
            use_case.execute(non_existent_project, dto)

    def test_cb04_assignee_not_found(self):
        """CB-04 / RN-05: Usuário atribuído inexistente."""
        future_date = datetime.now(timezone.utc) + timedelta(days=5)
        non_existent_user = uuid.uuid4()
        dto = CreateTaskSchema(
            title="Tarefa com assignee inexistente",
            assignee_id=non_existent_user,
            due_date=future_date,
        )
        use_case = CreateTaskUseCase(self.task_repo, self.project_repo, self.user_repo)

        with self.assertRaises(UserNotFoundError):
            use_case.execute(self.project.id, dto)

    # -------------------------------------------------------------
    # API HTTP ENDPOINT INTEGRATION TESTS
    # -------------------------------------------------------------
    def test_api_create_task_endpoint(self):
        """Teste de Integração HTTP: POST /api/v1/projects/{project_id}/tasks."""
        payload = {
            "title": "Implementar Gateway de Pagamento",
            "description": "Integrar API da Zoop para checkout transparente.",
            "priority": "HIGH",
            "assignee_id": str(self.user.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }
        response = self.client.post(
            f"/api/v1/projects/{self.project.id}/tasks",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "PENDING")
        self.assertEqual(data["title"], payload["title"])

    def test_api_update_task_status_endpoint(self):
        """Teste de Integração HTTP: PATCH /api/v1/tasks/{task_id}/status."""
        task = self.task_repo.save(
            Task(
                project_id=self.project.id,
                title="Tarefa para Iniciar",
                status=TaskStatus.PENDING,
                due_date=datetime.now(timezone.utc) + timedelta(days=5),
            )
        )
        response = self.client.patch(
            f"/api/v1/tasks/{task.id}/status",
            data={"status": "IN_PROGRESS"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "IN_PROGRESS")

    def test_web_dashboard_home_view(self):
        """Teste da Página Inicial Web (GET /)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TaskTrack")
        self.assertContains(response, "Painel de Gestão de Tarefas")
        self.assertContains(response, self.project.title)
