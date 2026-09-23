import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.contrib.auth.models import User as AuthUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from tasktrack.domain.entities import Contract, Project, Requirement, Task, User
from tasktrack.domain.enums import (
    ContractStatus,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
    TaskPriority,
    TaskStatus,
    UserRole,
)
from tasktrack.domain.exceptions import (
    InvalidStatusTransitionError,
    ProjectNotFoundError,
    RequirementCodeAlreadyExistsError,
    RequirementNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from tasktrack.schemas.schemas import (
    CreateContractSchema,
    CreateProjectSchema,
    CreateRequirementSchema,
    CreateTaskSchema,
    UpdateRequirementSchema,
    UpdateTaskStatusSchema,
)
from tasktrack.use_cases.use_cases import (
    CreateContractUseCase,
    CreateProjectUseCase,
    CreateRequirementUseCase,
    CreateTaskUseCase,
    LinkRequirementToTaskUseCase,
    UnlinkRequirementFromTaskUseCase,
    UpdateRequirementUseCase,
    UpdateTaskStatusUseCase,
)
from tasktrack.use_cases.specification_export import END_MARKER, START_MARKER, export_requirements_section
from tasktrack.infra.repositories import (
    DjangoContractRepository,
    DjangoProjectRepository,
    DjangoRequirementRepository,
    DjangoTaskRepository,
    DjangoUserRepository,
)
from tasktrack.infra.models import ContractModel, UserModel, ProjectModel, TaskModel


class TaskTrackUnitAndIntegrationTests(TestCase):
    def setUp(self):
        self.user_repo = DjangoUserRepository()
        self.project_repo = DjangoProjectRepository()
        self.task_repo = DjangoTaskRepository()
        self.contract_repo = DjangoContractRepository()
        self.requirement_repo = DjangoRequirementRepository()

        self.media_root = tempfile.mkdtemp()
        self.override_media = override_settings(MEDIA_ROOT=self.media_root)
        self.override_media.enable()

        # Cria usuário base
        self.user = self.user_repo.save(
            User(
                id=uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"),
                name="Leonardo Admin",
                email="admin@tasktrack.com",
                role=UserRole.ADMIN,
            )
        )

        # Cria contrato base (projeto depende de um contrato - migration 0005)
        self.contract = self.contract_repo.save(
            Contract(
                id=uuid.UUID("b1d4b31e-6a8c-4c9a-a1a5-5f3c7e1f3a2b"),
                title="Contrato Base",
                description="Contrato de referência para os testes.",
                owner_id=self.user.id,
            )
        )

        # Cria projeto base vinculado ao contrato
        self.project = self.project_repo.save(
            Project(
                id=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
                contract_id=self.contract.id,
                title="Reformulação do E-commerce",
                description="Projeto focado na migração da vitrine.",
                owner_id=self.user.id,
            )
        )

        # Cria tarefa base vinculada ao projeto (usada nos testes de vínculo com requisitos)
        self.task = self.task_repo.save(
            Task(
                id=uuid.UUID("c2e5c42f-7b9d-4e0a-8f2c-1a3b4c5d6e7f"),
                project_id=self.project.id,
                title="Implementar Login",
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
            )
        )

        # Usuário de autenticação (views web exigem login_required)
        self.auth_user = AuthUser.objects.create_user(
            username=self.user.email,
            email=self.user.email,
            password="tasktrack-teste-2024",
        )
        self.client.force_login(self.auth_user)

    def tearDown(self):
        self.override_media.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    # -------------------------------------------------------------
    # DOMAIN UNIT TESTS
    # -------------------------------------------------------------
    def test_rn04_status_lifecycle_transitions(self):
        """RN-04: Testa transições válidas, incluindo reabertura de tarefas COMPLETED."""
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

        # COMPLETED -> IN_PROGRESS (Reabertura permitida, RN-04)
        task.change_status(TaskStatus.IN_PROGRESS)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

        # COMPLETED -> PENDING (Reabertura permitida, RN-04)
        task.change_status(TaskStatus.COMPLETED)
        task.change_status(TaskStatus.PENDING)
        self.assertEqual(task.status, TaskStatus.PENDING)

    # -------------------------------------------------------------
    # USE CASE / SPECIFICATION ACCEPTANCE CRITERIA
    # -------------------------------------------------------------
    def test_scenario_1_create_task_success(self):
        """Cenário 1: Sucesso na Criação de Tarefa (Spec 5.1)."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=10)).date()
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

    def test_scenario_3_reabertura_completed_to_in_progress(self):
        """Cenário 3: Reabertura de Tarefa Concluída (CB-03 / Spec 5.3).

        RN-04 permite reabrir tarefas COMPLETED (commit 146acdb removeu a antiga
        restrição que bloqueava COMPLETED -> IN_PROGRESS/PENDING).
        """
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()
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

        updated_task = use_case.execute(task.id, dto)
        self.assertEqual(updated_task.status, TaskStatus.IN_PROGRESS)

    def test_cb01_project_not_found(self):
        """CB-01: Projeto Inexistente ao criar tarefa."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()
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
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).date()
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
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(),
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

    def test_web_dashboard_shows_requirement_codes_on_linked_task_card(self):
        """Vínculo N:N (seção 2.6): o cartão da tarefa no Kanban exibe os códigos
        de TODOS os requisitos vinculados a ela, e um mesmo requisito pode
        aparecer em vários cartões de tarefa diferentes."""
        req1 = CreateRequirementUseCase(self.requirement_repo).execute(
            CreateRequirementSchema(code="RF-01", title="Login", type=RequirementType.FUNCTIONAL)
        )
        req2 = CreateRequirementUseCase(self.requirement_repo).execute(
            CreateRequirementSchema(code="RF-02", title="Logout", type=RequirementType.FUNCTIONAL)
        )
        other_task = self.task_repo.save(
            Task(project_id=self.project.id, title="Outra Tarefa", status=TaskStatus.PENDING)
        )

        # self.task atende aos dois requisitos; other_task também atende ao RF-01
        LinkRequirementToTaskUseCase(self.requirement_repo, self.task_repo).execute(req1.id, self.task.id)
        LinkRequirementToTaskUseCase(self.requirement_repo, self.task_repo).execute(req2.id, self.task.id)
        LinkRequirementToTaskUseCase(self.requirement_repo, self.task_repo).execute(req1.id, other_task.id)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("RF-01", body)
        self.assertIn("RF-02", body)
        self.assertGreaterEqual(body.count("RF-01"), 2)  # aparece no requisito e em 2 cartões de tarefa

    # -------------------------------------------------------------
    # CONTRACTS (nova spec: tabela contracts com contract_file)
    # -------------------------------------------------------------
    def test_contract_schema_blank_title_rejected(self):
        """Validação Pydantic: título de contrato não pode ser apenas espaços."""
        with self.assertRaises(ValueError):
            CreateContractSchema(
                title="   ",
                description="Sem título válido.",
                owner_id=self.user.id,
            )

    def test_create_contract_use_case_success(self):
        """Use case: cria contrato com arquivo e persiste via repositório."""
        dto = CreateContractSchema(
            title="Contrato de Prestação de Serviços",
            description="Acordo comercial para o e-commerce.",
            contract_file="contracts/contrato_2026.pdf",
            owner_id=self.user.id,
        )
        use_case = CreateContractUseCase(self.contract_repo, self.user_repo)
        contract = use_case.execute(dto)

        self.assertIsNotNone(contract.id)
        self.assertEqual(contract.title, dto.title)
        self.assertEqual(contract.contract_file, "contracts/contrato_2026.pdf")
        self.assertEqual(self.contract_repo.get_by_id(contract.id).title, dto.title)

    def test_create_contract_use_case_owner_not_found(self):
        """Use case: proprietário inexistente deve gerar UserNotFoundError."""
        dto = CreateContractSchema(
            title="Contrato sem dono",
            owner_id=uuid.uuid4(),
        )
        use_case = CreateContractUseCase(self.contract_repo, self.user_repo)
        with self.assertRaises(UserNotFoundError):
            use_case.execute(dto)

    def test_api_create_contract_json(self):
        """API: POST /api/v1/contracts com JSON retorna 201 e contract_file."""
        payload = {
            "title": "Contrato via API",
            "description": "Cadastrado por JSON.",
            "owner_id": str(self.user.id),
        }
        response = self.client.post(
            "/api/v1/contracts",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], payload["title"])
        self.assertIn("id", data)
        self.assertIsNone(data["contract_file"])

    def test_api_create_contract_multipart_file_upload(self):
        """API: POST /api/v1/contracts multipart anexa arquivo e salva caminho."""
        uploaded = SimpleUploadedFile(
            "contrato.pdf",
            b"%PDF-1.4 fake content",
            content_type="application/pdf",
        )
        response = self.client.post(
            "/api/v1/contracts",
            data={
                "title": "Contrato com Arquivo",
                "description": "Anexo enviado por multipart.",
                "owner_id": str(self.user.id),
                "contract_file": uploaded,
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["contract_file"].startswith("contracts/"))
        self.assertEqual(data["contract_file"].split("_", 1)[1], "contrato.pdf")

    def test_web_create_contract_with_file(self):
        """Web: POST /web/contracts com arquivo redireciona e persiste contrato."""
        uploaded = SimpleUploadedFile(
            "termo.txt",
            b"conteudo do termo",
            content_type="text/plain",
        )
        response = self.client.post(
            "/web/contracts",
            data={
                "title": "Termo de Adesão",
                "description": "Regras de uso.",
                "owner_id": str(self.user.id),
                "contract_file": uploaded,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContractModel.objects.filter(title="Termo de Adesão").count(), 1)
        contract = ContractModel.objects.get(title="Termo de Adesão")
        self.assertEqual(contract.title, "Termo de Adesão")
        self.assertTrue(contract.contract_file.startswith("contracts/"))

    def test_web_update_contract_status_success(self):
        """Web: POST /web/contracts/{id}/status atualiza o status do contrato."""
        response = self.client.post(
            f"/web/contracts/{self.contract.id}/status",
            {"status": "IN_PROGRESS"},
        )
        self.assertEqual(response.status_code, 302)
        updated = self.contract_repo.get_by_id(self.contract.id)
        self.assertEqual(updated.status.value, ContractStatus.IN_PROGRESS.value)

    def test_web_update_contract_status_invalid_transition(self):
        """Web: contrato SIGNED não pode retornar para IN_PROGRESS (estado final)."""
        signed = self.contract_repo.save(
            Contract(
                title="Contrato Assinado",
                owner_id=self.user.id,
                status=ContractStatus.SIGNED,
            )
        )
        response = self.client.post(
            f"/web/contracts/{signed.id}/status",
            {"status": "IN_PROGRESS"},
        )
        self.assertEqual(response.status_code, 302)
        updated = self.contract_repo.get_by_id(signed.id)
        self.assertEqual(updated.status.value, ContractStatus.SIGNED.value)

    def test_web_update_contract_status_contract_not_found(self):
        """Web: contrato inexistente gera mensagem de erro."""
        response = self.client.post(
            f"/web/contracts/{uuid.uuid4()}/status",
            {"status": "IN_PROGRESS"},
        )
        self.assertEqual(response.status_code, 302)

    def test_web_update_contract_success(self):
        """Web: POST /web/contracts/{id} edita título, descrição e proprietário."""
        other_owner = self.user_repo.save(User(name="Outro Dono", email="outro@tasktrack.com", role=UserRole.MANAGER))
        response = self.client.post(
            f"/web/contracts/{self.contract.id}",
            {"title": "Contrato Renomeado", "description": "Nova descrição", "owner_id": str(other_owner.id)},
        )
        self.assertEqual(response.status_code, 302)
        updated = self.contract_repo.get_by_id(self.contract.id)
        self.assertEqual(updated.title, "Contrato Renomeado")
        self.assertEqual(updated.description, "Nova descrição")
        self.assertEqual(updated.owner_id, other_owner.id)

    def test_web_update_contract_not_found(self):
        """Web: editar contrato inexistente não gera erro 500."""
        response = self.client.post(
            f"/web/contracts/{uuid.uuid4()}",
            {"title": "Não existe"},
        )
        self.assertEqual(response.status_code, 302)

    def test_web_delete_contract_cascades_projects_and_tasks(self):
        """Web: excluir contrato remove em cascata projetos e tarefas vinculados (FK CASCADE)."""
        response = self.client.post(f"/web/contracts/{self.contract.id}/delete")
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.contract_repo.get_by_id(self.contract.id))
        self.assertIsNone(self.project_repo.get_by_id(self.project.id))
        self.assertIsNone(self.task_repo.get_by_id(self.task.id))

    def test_web_delete_contract_not_found(self):
        """Web: excluir contrato inexistente não gera erro 500."""
        response = self.client.post(f"/web/contracts/{uuid.uuid4()}/delete")
        self.assertEqual(response.status_code, 302)

    def test_web_update_project_success(self):
        """Web: POST /web/projects/{id} edita título, descrição e proprietário."""
        other_owner = self.user_repo.save(User(name="Outro Dono 2", email="outro2@tasktrack.com", role=UserRole.MANAGER))
        response = self.client.post(
            f"/web/projects/{self.project.id}",
            {"title": "Projeto Renomeado", "description": "Nova descrição", "owner_id": str(other_owner.id)},
        )
        self.assertEqual(response.status_code, 302)
        updated = self.project_repo.get_by_id(self.project.id)
        self.assertEqual(updated.title, "Projeto Renomeado")
        self.assertEqual(updated.description, "Nova descrição")
        self.assertEqual(updated.owner_id, other_owner.id)

    def test_web_update_project_not_found(self):
        """Web: editar projeto inexistente não gera erro 500."""
        response = self.client.post(
            f"/web/projects/{uuid.uuid4()}",
            {"title": "Não existe"},
        )
        self.assertEqual(response.status_code, 302)

    def test_web_delete_project_cascades_tasks(self):
        """Web: excluir projeto remove em cascata as tarefas vinculadas (FK CASCADE)."""
        response = self.client.post(f"/web/projects/{self.project.id}/delete")
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.project_repo.get_by_id(self.project.id))
        self.assertIsNone(self.task_repo.get_by_id(self.task.id))
        self.assertIsNotNone(self.contract_repo.get_by_id(self.contract.id))

    def test_web_delete_project_not_found(self):
        """Web: excluir projeto inexistente não gera erro 500."""
        response = self.client.post(f"/web/projects/{uuid.uuid4()}/delete")
        self.assertEqual(response.status_code, 302)

    def test_api_update_contract_endpoint(self):
        """API: PATCH /api/v1/contracts/{id} atualiza campos parciais."""
        response = self.client.patch(
            f"/api/v1/contracts/{self.contract.id}",
            data={"title": "Contrato via API"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Contrato via API")

    def test_api_delete_contract_endpoint(self):
        """API: DELETE /api/v1/contracts/{id} exclui o contrato (e cascata)."""
        response = self.client.delete(f"/api/v1/contracts/{self.contract.id}")
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.contract_repo.get_by_id(self.contract.id))

    def test_api_update_project_endpoint(self):
        """API: PATCH /api/v1/projects/{id} atualiza campos parciais."""
        response = self.client.patch(
            f"/api/v1/projects/{self.project.id}",
            data={"title": "Projeto via API"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Projeto via API")

    def test_api_delete_project_endpoint(self):
        """API: DELETE /api/v1/projects/{id} exclui o projeto (e cascata)."""
        response = self.client.delete(f"/api/v1/projects/{self.project.id}")
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.project_repo.get_by_id(self.project.id))
        self.assertIsNone(self.task_repo.get_by_id(self.task.id))

    # -------------------------------------------------------------
    # REQUIREMENTS (Gestão de Requisitos)
    # -------------------------------------------------------------
    def test_requirement_change_status_transitions(self):
        """Domínio: transições válidas e proibição de transição a partir de DEPRECATED."""
        requirement = Requirement(title="Autenticação", code="RF-01", status=RequirementStatus.DRAFT)

        requirement.change_status(RequirementStatus.APPROVED)
        self.assertEqual(requirement.status, RequirementStatus.APPROVED)

        requirement.change_status(RequirementStatus.IMPLEMENTED)
        self.assertEqual(requirement.status, RequirementStatus.IMPLEMENTED)

        requirement.change_status(RequirementStatus.DEPRECATED)
        self.assertEqual(requirement.status, RequirementStatus.DEPRECATED)

        with self.assertRaises(InvalidStatusTransitionError):
            requirement.change_status(RequirementStatus.APPROVED)

    def test_create_requirement_use_case_success(self):
        dto = CreateRequirementSchema(
            code="RF-01",
            title="Autenticação de Usuários",
            description="O sistema deve permitir login via e-mail e senha.",
            type=RequirementType.FUNCTIONAL,
            priority=RequirementPriority.HIGH,
        )
        requirement = CreateRequirementUseCase(self.requirement_repo).execute(dto)
        self.assertEqual(requirement.code, "RF-01")
        self.assertEqual(requirement.status, RequirementStatus.DRAFT)

    def test_create_requirement_duplicate_code_rejected(self):
        dto = CreateRequirementSchema(code="RF-01", title="Primeiro Requisito", type=RequirementType.FUNCTIONAL)
        CreateRequirementUseCase(self.requirement_repo).execute(dto)

        dto_duplicado = CreateRequirementSchema(code="RF-01", title="Segundo Requisito", type=RequirementType.FUNCTIONAL)
        with self.assertRaises(RequirementCodeAlreadyExistsError):
            CreateRequirementUseCase(self.requirement_repo).execute(dto_duplicado)

    def test_update_requirement_partial(self):
        dto = CreateRequirementSchema(code="RF-01", title="Título Original", type=RequirementType.FUNCTIONAL)
        requirement = CreateRequirementUseCase(self.requirement_repo).execute(dto)

        updated = UpdateRequirementUseCase(self.requirement_repo).execute(
            requirement.id, UpdateRequirementSchema(title="Título Atualizado")
        )
        self.assertEqual(updated.title, "Título Atualizado")
        self.assertEqual(updated.code, "RF-01")

    def test_link_and_unlink_requirement_to_task(self):
        dto = CreateRequirementSchema(code="RF-01", title="Autenticação", type=RequirementType.FUNCTIONAL)
        requirement = CreateRequirementUseCase(self.requirement_repo).execute(dto)

        LinkRequirementToTaskUseCase(self.requirement_repo, self.task_repo).execute(requirement.id, self.task.id)
        linked = self.requirement_repo.list_linked_tasks(requirement.id)
        self.assertEqual([t.id for t in linked], [self.task.id])

        UnlinkRequirementFromTaskUseCase(self.requirement_repo).execute(requirement.id, self.task.id)
        self.assertEqual(self.requirement_repo.list_linked_tasks(requirement.id), [])

    def test_link_requirement_task_not_found(self):
        dto = CreateRequirementSchema(code="RF-01", title="Autenticação", type=RequirementType.FUNCTIONAL)
        requirement = CreateRequirementUseCase(self.requirement_repo).execute(dto)

        with self.assertRaises(TaskNotFoundError):
            LinkRequirementToTaskUseCase(self.requirement_repo, self.task_repo).execute(requirement.id, uuid.uuid4())

    def test_link_task_requirement_not_found(self):
        with self.assertRaises(RequirementNotFoundError):
            LinkRequirementToTaskUseCase(self.requirement_repo, self.task_repo).execute(uuid.uuid4(), self.task.id)

    def test_web_create_requirement_success(self):
        response = self.client.post(
            "/web/requirements",
            {"code": "RF-01", "title": "Autenticação de Usuários", "type": "FUNCTIONAL", "priority": "HIGH"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.requirement_repo.list_all()), 1)

    def test_web_link_task_to_requirement(self):
        dto = CreateRequirementSchema(code="RF-01", title="Autenticação", type=RequirementType.FUNCTIONAL)
        requirement = CreateRequirementUseCase(self.requirement_repo).execute(dto)

        response = self.client.post(
            f"/web/requirements/{requirement.id}/tasks",
            {"action": "add", "task_id": str(self.task.id)},
        )
        self.assertEqual(response.status_code, 302)
        linked = self.requirement_repo.list_linked_tasks(requirement.id)
        self.assertEqual([t.id for t in linked], [self.task.id])

    def test_api_create_requirement_endpoint(self):
        response = self.client.post(
            "/api/v1/requirements",
            data={"code": "RF-01", "title": "Autenticação de Usuários", "type": "FUNCTIONAL"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["code"], "RF-01")

    def test_api_create_requirement_duplicate_code(self):
        dto = CreateRequirementSchema(code="RF-01", title="Primeiro", type=RequirementType.FUNCTIONAL)
        CreateRequirementUseCase(self.requirement_repo).execute(dto)

        response = self.client.post(
            "/api/v1/requirements",
            data={"code": "RF-01", "title": "Segundo", "type": "FUNCTIONAL"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_export_requirements_section_updates_only_delimited_block(self):
        """Exportação regenera apenas o bloco entre os marcadores, preservando o resto do arquivo."""
        spec_content = (
            f"# Título\n\nAntes.\n\n{START_MARKER}\nplaceholder\n{END_MARKER}\n\nDepois.\n"
        )
        spec_dir = tempfile.mkdtemp()
        spec_path = Path(spec_dir) / "SPECIFICATION.md"
        spec_path.write_text(spec_content, encoding="utf-8")

        dto = CreateRequirementSchema(code="RF-01", title="Autenticação", type=RequirementType.FUNCTIONAL)
        requirement = CreateRequirementUseCase(self.requirement_repo).execute(dto)
        LinkRequirementToTaskUseCase(self.requirement_repo, self.task_repo).execute(requirement.id, self.task.id)

        export_requirements_section(self.requirement_repo, self.task_repo, spec_path)

        new_content = spec_path.read_text(encoding="utf-8")
        self.assertIn("Antes.", new_content)
        self.assertIn("Depois.", new_content)
        self.assertIn("RF-01", new_content)
        self.assertIn(self.task.title, new_content)
        self.assertNotIn("placeholder", new_content)
        shutil.rmtree(spec_dir, ignore_errors=True)
