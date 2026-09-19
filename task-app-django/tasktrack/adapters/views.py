import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from ..domain.entities import User
from ..domain.enums import ContractStatus, ProjectStatus, TaskPriority, TaskStatus, UserRole
from ..domain.exceptions import (
    DomainError,
    InvalidStatusTransitionError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from ..infra.repositories import (
    DjangoContractRepository,
    DjangoProjectRepository,
    DjangoTaskRepository,
    DjangoUserRepository,
)
from ..schemas.schemas import (
    ContractResponseSchema,
    CreateContractSchema,
    CreateProjectSchema,
    CreateTaskSchema,
    ProjectResponseSchema,
    TaskResponseSchema,
    UpdateContractStatusSchema,
    UpdateProjectStatusSchema,
    UpdateTaskStatusSchema,
)
from ..use_cases.use_cases import (
    CreateContractUseCase,
    CreateProjectUseCase,
    CreateTaskUseCase,
    AddProjectTeamMemberUseCase,
    RemoveProjectTeamMemberUseCase,
    UpdateContractStatusUseCase,
    UpdateProjectStatusUseCase,
    UpdateTaskStatusUseCase,
)

user_repo = DjangoUserRepository()
project_repo = DjangoProjectRepository()
task_repo = DjangoTaskRepository()
contract_repo = DjangoContractRepository()


def _format_pydantic_error(e: ValidationError) -> JsonResponse:
    details = []
    for err in e.errors():
        loc = list(err.get("loc", []))
        if loc and loc[0] != "body":
            loc = ["body"] + loc
        elif not loc:
            loc = ["body"]
        details.append({
            "loc": loc,
            "msg": err.get("msg", ""),
            "type": err.get("type", "value_error"),
        })
    return JsonResponse({"detail": details}, status=422)


def _save_contract_file(uploaded_file) -> Optional[str]:
    """Persiste o arquivo anexado em MEDIA_ROOT e retorna o caminho relativo."""
    if not uploaded_file:
        return None
    name = (uploaded_file.name or "contrato").replace("\\", "/").split("/")[-1]
    if len(name) > 100:
        parts = name.rsplit(".")
        ext = f".{parts[-1]}" if len(parts) > 1 and len(parts[-1]) <= 10 else ""
        name = name[:90] + ext
    return default_storage.save(f"contracts/{uuid4()}_{name}", uploaded_file)


# =====================================================================
# WEB TEMPLATE VIEWS (MVT + Bootstrap 5 Dashboard)
# =====================================================================

def home_view(request):
    """Página inicial com Dashboard de Projetos e Kanban de Tarefas."""
    selected_project_id = request.GET.get("project_id")
    projects = project_repo.list_all()
    users = user_repo.list_all()

    user_map = {u.id: u.name for u in users}

    if selected_project_id:
        try:
            tasks = task_repo.list_by_project(UUID(selected_project_id))
        except ValueError:
            tasks = task_repo.list_all()
    else:
        tasks = task_repo.list_all()

    # Anexa o nome do responsável se existir
    for t in tasks:
        t.assignee_name = user_map.get(t.assignee_id, "") if t.assignee_id else ""

    contracts = contract_repo.list_all()
    for c in contracts:
        c.owner_name = user_map.get(c.owner_id, "") if c.owner_id else ""

    tasks_by_project = {}
    for task in tasks:
        tasks_by_project.setdefault(task.project_id, []).append(task)
    for project in projects:
        project_tasks = tasks_by_project.get(project.id, [])
        statuses = {task.status for task in project_tasks}
        if project_tasks and statuses == {TaskStatus.COMPLETED}:
            project.dashboard_status = TaskStatus.COMPLETED
        elif TaskStatus.IN_PROGRESS in statuses:
            project.dashboard_status = TaskStatus.IN_PROGRESS
        elif project_tasks:
            project.dashboard_status = TaskStatus.PENDING
        else:
            project.dashboard_status = None
        project.team_members = project_repo.list_team_members(project.id)
        project.team_member_ids = {member.id for member in project.team_members}

    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
    in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
    completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

    context = {
        "projects": projects,
        "users": users,
        "contracts": contracts,
        "selected_project_id": selected_project_id,
        "MEDIA_URL": settings.MEDIA_URL,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completed_tasks": completed_tasks,
    }
    return render(request, "index.html", context)


def web_create_contract_view(request):
    if request.method == "POST":
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        owner_id_str = request.POST.get("owner_id", "")
        contract_file = _save_contract_file(request.FILES.get("contract_file"))

        try:
            dto = CreateContractSchema(
                title=title,
                description=description,
                contract_file=contract_file,
                owner_id=UUID(owner_id_str),
            )
        except (ValidationError, ValueError) as e:
            if isinstance(e, ValidationError):
                msg = e.errors()[0].get("msg", "Dados do contrato inválidos.")
            else:
                msg = "UUID do proprietário inválido."
            messages.error(request, f"Erro ao criar contrato: {msg}")
            return redirect("/")

        use_case = CreateContractUseCase(contract_repo=contract_repo, user_repo=user_repo)
        try:
            use_case.execute(dto)
            messages.success(request, f"Contrato '{title}' criado com sucesso!")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")
        except Exception as e:
            messages.error(request, f"Erro inesperado: {e}")

    return redirect("/")


def web_create_project_view(request):
    if request.method == "POST":
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        owner_id_str = request.POST.get("owner_id", "")
        contract_id_str = request.POST.get("contract_id", "")

        try:
            dto = CreateProjectSchema(
                title=title,
                description=description,
                owner_id=UUID(owner_id_str),
                contract_id=UUID(contract_id_str),
            )
            use_case = CreateProjectUseCase(project_repo=project_repo, user_repo=user_repo, contract_repo=contract_repo)
            use_case.execute(dto)
            messages.success(request, f"Projeto '{title}' criado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados do projeto inválidos.")
            messages.error(request, f"Erro ao criar projeto: {msg}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")
        except Exception as e:
            messages.error(request, f"Erro inesperado: {e}")

    return redirect("/")


def web_update_contract_status_view(request, contract_id: str):
    if request.method == "POST":
        try:
            dto = UpdateContractStatusSchema(status=ContractStatus(request.POST.get("status", "")))
            UpdateContractStatusUseCase(contract_repo).execute(UUID(contract_id), dto)
            messages.success(request, "Status do contrato atualizado!")
        except (ValidationError, ValueError):
            messages.error(request, "Status de contrato inválido.")
        except DomainError as e:
            messages.error(request, f"Erro ao alterar contrato: {e}")
    return redirect("/")


def web_update_project_status_view(request, project_id: str):
    if request.method == "POST":
        try:
            dto = UpdateProjectStatusSchema(status=ProjectStatus(request.POST.get("status", "")))
            UpdateProjectStatusUseCase(project_repo, task_repo).execute(UUID(project_id), dto)
            messages.success(request, "Status do projeto atualizado!")
        except (ValidationError, ValueError):
            messages.error(request, "Status de projeto inválido.")
        except DomainError as e:
            messages.error(request, f"Erro ao alterar projeto: {e}")
    return redirect("/")


def web_update_project_team_view(request, project_id: str):
    if request.method == "POST":
        try:
            user_id = UUID(request.POST.get("user_id", ""))
            if request.POST.get("action") == "remove":
                RemoveProjectTeamMemberUseCase(project_repo).execute(UUID(project_id), user_id)
                messages.success(request, "Membro removido da equipe do projeto!")
            else:
                AddProjectTeamMemberUseCase(project_repo, user_repo).execute(UUID(project_id), user_id)
                messages.success(request, "Membro adicionado à equipe do projeto!")
        except (ValidationError, ValueError):
            messages.error(request, "Usuário inválido.")
        except DomainError as e:
            messages.error(request, f"Erro ao alterar equipe: {e}")
    return redirect("/")


def web_create_task_view(request):
    if request.method == "POST":
        project_id_str = request.POST.get("project_id", "")
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        priority = request.POST.get("priority", "MEDIUM")
        assignee_id_str = request.POST.get("assignee_id", "")
        due_date_str = request.POST.get("due_date", "")

        try:
            due_date = datetime.fromisoformat(due_date_str)
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)

            dto = CreateTaskSchema(
                title=title,
                description=description,
                priority=TaskPriority(priority),
                assignee_id=UUID(assignee_id_str) if assignee_id_str else None,
                due_date=due_date,
            )
            use_case = CreateTaskUseCase(
                task_repo=task_repo,
                project_repo=project_repo,
                user_repo=user_repo,
            )
            use_case.execute(UUID(project_id_str), dto)
            messages.success(request, f"Tarefa '{title}' cadastrada com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados da tarefa inválidos.")
            messages.error(request, f"Erro ao criar tarefa: {msg}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")
        except Exception as e:
            messages.error(request, f"Erro ao processar dados da tarefa: {e}")

    return redirect("/")


def web_update_task_status_view(request, task_id: str):
    if request.method == "POST":
        status_str = request.POST.get("status", "")
        try:
            dto = UpdateTaskStatusSchema(status=TaskStatus(status_str))
            use_case = UpdateTaskStatusUseCase(task_repo=task_repo)
            use_case.execute(UUID(task_id), dto)
            messages.success(request, "Status da tarefa atualizado!")
        except InvalidStatusTransitionError as e:
            messages.error(request, f"Transição inválida: {e.message}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar status: {e}")

    return redirect("/")


def web_create_user_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role", "MEMBER")

        if name and email:
            user = User(id=uuid4(), name=name, email=email, role=UserRole(role))
            user_repo.save(user)
            messages.success(request, f"Usuário '{name}' cadastrado!")
        else:
            messages.error(request, "Nome e e-mail são obrigatórios.")

    return redirect("/")


# =====================================================================
# REST API ENDPOINTS
# =====================================================================


@csrf_exempt
def contracts_view(request):
    if request.method == "POST":
        contract_file = None
        if request.content_type and "multipart/form-data" in request.content_type:
            raw_body = request.POST
            contract_file = _save_contract_file(request.FILES.get("contract_file"))
        else:
            try:
                raw_body = json.loads(request.body.decode("utf-8")) if request.body else {}
            except json.JSONDecodeError:
                return JsonResponse({"detail": "JSON inválido"}, status=422)
            contract_file = raw_body.get("contract_file")

        try:
            dto = CreateContractSchema(
                title=raw_body.get("title", ""),
                description=raw_body.get("description"),
                contract_file=contract_file,
                owner_id=UUID(raw_body.get("owner_id", "")),
            )
        except ValidationError as e:
            return _format_pydantic_error(e)
        except ValueError:
            return JsonResponse({"detail": "UUID do proprietário inválido"}, status=422)

        use_case = CreateContractUseCase(contract_repo=contract_repo, user_repo=user_repo)
        try:
            contract = use_case.execute(dto)
            response_dto = ContractResponseSchema(
                id=contract.id,
                title=contract.title,
                description=contract.description,
                contract_file=contract.contract_file,
                status=contract.status,
                owner_id=contract.owner_id,
                created_at=contract.created_at,
            )
            return JsonResponse(response_dto.model_dump(mode="json"), status=201)
        except UserNotFoundError as e:
            return JsonResponse({"error": e.message}, status=400)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)


@csrf_exempt
def projects_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = CreateProjectSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = CreateProjectUseCase(project_repo=project_repo, user_repo=user_repo, contract_repo=contract_repo)
        try:
            project = use_case.execute(dto)
            response_dto = ProjectResponseSchema(
                id=project.id,
                contract_id=project.contract_id,
                title=project.title,
                description=project.description,
                owner_id=project.owner_id,
                created_at=project.created_at,
            )
            return JsonResponse(response_dto.model_dump(mode="json"), status=201)
        except UserNotFoundError as e:
            return JsonResponse({"error": e.message}, status=400)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)


@csrf_exempt
def project_tasks_view(request, project_id: str):
    try:
        proj_uuid = UUID(project_id)
    except ValueError:
        return JsonResponse({"detail": "UUID do projeto inválido"}, status=422)

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = CreateTaskSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = CreateTaskUseCase(
            task_repo=task_repo,
            project_repo=project_repo,
            user_repo=user_repo,
        )
        try:
            task = use_case.execute(proj_uuid, dto)
            response_dto = TaskResponseSchema(
                id=task.id,
                project_id=task.project_id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assignee_id=task.assignee_id,
                due_date=task.due_date,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            return JsonResponse(response_dto.model_dump(mode="json"), status=201)
        except ProjectNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except UserNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)


@csrf_exempt
def task_status_view(request, task_id: str):
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        return JsonResponse({"detail": "UUID da tarefa inválido"}, status=422)

    if request.method in ["PATCH", "POST"]:
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = UpdateTaskStatusSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = UpdateTaskStatusUseCase(task_repo=task_repo)
        try:
            task = use_case.execute(task_uuid, dto)
            response_dto = TaskResponseSchema(
                id=task.id,
                project_id=task.project_id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assignee_id=task.assignee_id,
                due_date=task.due_date,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            return JsonResponse(response_dto.model_dump(mode="json"), status=200)
        except TaskNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except InvalidStatusTransitionError as e:
            return JsonResponse({"error": e.code, "message": e.message}, status=400)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)
