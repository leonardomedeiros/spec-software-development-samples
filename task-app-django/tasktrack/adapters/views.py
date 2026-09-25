import json
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User as DjangoUser
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from ..domain import visibility
from ..domain.entities import User
from ..domain.enums import (
    ContractStatus,
    ProjectStatus,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
    TaskPriority,
    TaskStatus,
    UserRole,
)
from ..domain.exceptions import (
    ActorNotFoundError,
    ContractNotFoundError,
    DomainError,
    InvalidStatusTransitionError,
    ProjectNotFoundError,
    RequirementNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from ..infra.repositories import (
    DjangoActorRepository,
    DjangoContractRepository,
    DjangoProjectRepository,
    DjangoRequirementRepository,
    DjangoTaskRepository,
    DjangoUserRepository,
)
from ..schemas.schemas import (
    ContractResponseSchema,
    CreateActorSchema,
    CreateContractSchema,
    CreateProjectSchema,
    CreateRequirementSchema,
    CreateTaskSchema,
    ProjectResponseSchema,
    RequirementResponseSchema,
    TaskResponseSchema,
    UpdateActorSchema,
    UpdateContractSchema,
    UpdateContractStatusSchema,
    UpdateProjectSchema,
    UpdateProjectStatusSchema,
    UpdateRequirementSchema,
    UpdateRequirementStatusSchema,
    UpdateTaskStatusSchema,
    UpdateTaskSchema,
)
from ..use_cases.specification_export import export_requirements_section
from ..use_cases.use_cases import (
    CreateActorUseCase,
    CreateContractUseCase,
    CreateProjectUseCase,
    CreateRequirementUseCase,
    CreateTaskUseCase,
    AddProjectTeamMemberUseCase,
    DeleteActorUseCase,
    DeleteContractUseCase,
    DeleteProjectUseCase,
    DeleteRequirementUseCase,
    LinkActorToRequirementUseCase,
    LinkRequirementToTaskUseCase,
    RemoveProjectTeamMemberUseCase,
    UnlinkActorFromRequirementUseCase,
    UnlinkRequirementFromTaskUseCase,
    UpdateActorUseCase,
    UpdateContractStatusUseCase,
    UpdateContractUseCase,
    UpdateProjectStatusUseCase,
    UpdateProjectUseCase,
    UpdateRequirementStatusUseCase,
    UpdateRequirementUseCase,
    UpdateTaskStatusUseCase,
    UpdateTaskUseCase,
    DeleteTaskUseCase,
)

user_repo = DjangoUserRepository()
project_repo = DjangoProjectRepository()
task_repo = DjangoTaskRepository()
contract_repo = DjangoContractRepository()
requirement_repo = DjangoRequirementRepository()
actor_repo = DjangoActorRepository()


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


def _get_current_domain_user(request) -> Optional[User]:
    """Resolve o perfil de domínio (com role) correspondente ao usuário Django autenticado."""
    if not request.user.is_authenticated:
        return None
    return user_repo.get_by_email(request.user.username)


def _user_can_access_project(request, project_id: UUID) -> bool:
    """Guarda de autorização para ações (editar/excluir/vincular) sobre um projeto específico."""
    current_user = _get_current_domain_user(request)
    if current_user is None:
        return False
    if current_user.role == UserRole.ADMIN:
        return True
    project = project_repo.get_by_id(project_id)
    if project is None:
        return False
    if current_user.role == UserRole.MEMBER:
        # MEMBER pode navegar/agir em projetos de qualquer contrato (seleção explícita no dashboard).
        return True
    if project.owner_id == current_user.id:
        return True
    return any(member.id == current_user.id for member in project_repo.list_team_members(project_id))


def _user_can_access_contract(request, contract_id: UUID) -> bool:
    """Guarda de autorização para ações sobre um contrato ou entidade vinculada a ele (ex.: Ator)."""
    current_user = _get_current_domain_user(request)
    if current_user is None:
        return False
    if current_user.role in (UserRole.ADMIN, UserRole.MEMBER):
        return True
    contract_projects = [p for p in project_repo.list_all() if p.contract_id == contract_id]
    for project in contract_projects:
        if project.owner_id == current_user.id:
            return True
        if any(member.id == current_user.id for member in project_repo.list_team_members(project.id)):
            return True
    return False


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

@login_required(login_url="/login")
def home_view(request):
    """Página inicial com Dashboard de Projetos e Kanban de Tarefas, filtrada pela visibilidade do usuário."""
    current_user = _get_current_domain_user(request)
    if current_user is None:
        messages.error(request, "Não foi possível identificar seu perfil de acesso. Contate um administrador.")
        return render(request, "index.html", {
            "projects": [], "users": [], "contracts": [], "prospecting_contracts": [],
            "in_progress_contracts": [], "signed_contracts": [], "selected_project_id": None,
            "MEDIA_URL": settings.MEDIA_URL, "pending_tasks": [], "in_progress_tasks": [],
            "completed_tasks": [], "requirements": [], "all_tasks": [], "actors": [],
            "can_browse_contracts": False, "all_contracts": [], "selected_contract_id": None,
        })

    selected_project_id = request.GET.get("project_id")
    selected_contract_id_str = request.GET.get("contract_id")
    selected_contract_id = None
    if selected_contract_id_str:
        try:
            selected_contract_id = UUID(selected_contract_id_str)
        except ValueError:
            selected_contract_id = None

    users = user_repo.list_all()
    user_map = {u.id: u.name for u in users}

    # Carrega todos os projetos com equipe anexada — necessário tanto para exibição
    # quanto para calcular a visibilidade de perfis baseados em posse/associação.
    all_projects = project_repo.list_all()
    for project in all_projects:
        project.team_members = project_repo.list_team_members(project.id)
        project.team_member_ids = {member.id for member in project.team_members}
    member_user_ids_by_project = {p.id: p.team_member_ids for p in all_projects}

    visible_project_ids = visibility.get_visible_project_ids(
        current_user, all_projects, member_user_ids_by_project, selected_contract_id
    )
    visible_contract_ids = visibility.get_visible_contract_ids(
        current_user, all_projects, visible_project_ids, selected_contract_id
    )
    can_browse_contracts = visibility.can_browse_contracts(current_user)

    projects = [p for p in all_projects if visibility.is_id_visible(p.id, visible_project_ids)]
    visible_project_id_set = {p.id for p in projects}

    # A tarefa/projeto selecionado via querystring só é aplicado se estiver dentro do
    # conjunto visível — evita que um usuário force a visualização de outro projeto pela URL.
    all_tasks_unfiltered = task_repo.list_all()
    all_tasks = [t for t in all_tasks_unfiltered if t.project_id in visible_project_id_set]

    selected_project_uuid = None
    if selected_project_id:
        try:
            candidate = UUID(selected_project_id)
            if candidate in visible_project_id_set:
                selected_project_uuid = candidate
        except ValueError:
            pass

    if selected_project_uuid:
        tasks = [t for t in all_tasks if t.project_id == selected_project_uuid]
    else:
        selected_project_id = None
        tasks = all_tasks

    # Anexa o nome do responsável se existir
    for t in tasks:
        t.assignee_name = user_map.get(t.assignee_id, "") if t.assignee_id else ""

    all_contracts = contract_repo.list_all()
    contracts = [c for c in all_contracts if visibility.is_id_visible(c.id, visible_contract_ids)]
    for c in contracts:
        c.owner_name = user_map.get(c.owner_id, "") if c.owner_id else ""

    prospecting_contracts = [c for c in contracts if c.status == ContractStatus.PROSPECTING]
    in_progress_contracts = [c for c in contracts if c.status == ContractStatus.IN_PROGRESS]
    signed_contracts = [c for c in contracts if c.status == ContractStatus.SIGNED]

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

    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
    in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
    completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

    all_actors = actor_repo.list_all()
    actors = [a for a in all_actors if visibility.is_id_visible(a.contract_id, visible_contract_ids)]

    all_requirements = requirement_repo.list_all()
    requirements = [r for r in all_requirements if r.project_id in visible_project_id_set]

    task_requirement_codes = {}
    actor_requirement_names = {}
    for requirement in requirements:
        requirement.linked_tasks = requirement_repo.list_linked_tasks(requirement.id)
        requirement.linked_task_ids = {t.id for t in requirement.linked_tasks}
        for linked_task in requirement.linked_tasks:
            task_requirement_codes.setdefault(linked_task.id, []).append(requirement.code)

        requirement.linked_actors = requirement_repo.list_linked_actors(requirement.id)
        requirement.linked_actor_ids = {a.id for a in requirement.linked_actors}
        for linked_actor in requirement.linked_actors:
            actor_requirement_names.setdefault(linked_actor.id, []).append(requirement.code)

    # Anexa os códigos dos requisitos atendidos por cada tarefa (vínculo N:N, seção 2.6)
    for t in tasks:
        t.requirement_codes = task_requirement_codes.get(t.id, [])

    # Anexa os códigos dos requisitos vinculados a cada ator (vínculo N:N, seção 2.7)
    for actor in actors:
        actor.requirement_codes = actor_requirement_names.get(actor.id, [])

    context = {
        "projects": projects,
        "users": users,
        "contracts": contracts,
        "prospecting_contracts": prospecting_contracts,
        "in_progress_contracts": in_progress_contracts,
        "signed_contracts": signed_contracts,
        "selected_project_id": selected_project_id,
        "MEDIA_URL": settings.MEDIA_URL,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completed_tasks": completed_tasks,
        "requirements": requirements,
        "all_tasks": all_tasks,
        "actors": actors,
        "can_browse_contracts": can_browse_contracts,
        "all_contracts": all_contracts,
        "selected_contract_id": str(selected_contract_id) if selected_contract_id else "",
        "current_user_role": current_user.role.value,
    }
    return render(request, "index.html", context)


@login_required(login_url="/login")
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


@login_required(login_url="/login")
def web_create_project_view(request):
    if request.method == "POST":
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        owner_id_str = request.POST.get("owner_id", "")
        contract_id_str = request.POST.get("contract_id", "")

        try:
            contract_uuid = UUID(contract_id_str)
            if not _user_can_access_contract(request, contract_uuid):
                messages.error(request, "Você não tem permissão para criar projetos neste contrato.")
                return redirect("/")

            dto = CreateProjectSchema(
                title=title,
                description=description,
                owner_id=UUID(owner_id_str),
                contract_id=contract_uuid,
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


@login_required(login_url="/login")
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


@login_required(login_url="/login")
def web_update_contract_view(request, contract_id: str):
    if request.method == "POST":
        try:
            contract_uuid = UUID(contract_id)
        except ValueError:
            messages.error(request, "ID do contrato inválido.")
            return redirect("/")

        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        owner_id_str = request.POST.get("owner_id", "").strip()

        try:
            dto = UpdateContractSchema(
                title=title if title else None,
                description=description if description else None,
                owner_id=UUID(owner_id_str) if owner_id_str else None,
            )
            UpdateContractUseCase(contract_repo=contract_repo, user_repo=user_repo).execute(contract_uuid, dto)
            messages.success(request, "Contrato atualizado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados do contrato inválidos.")
            messages.error(request, f"Erro de validação: {msg}")
        except ValueError as e:
            messages.error(request, f"Dados inválidos: {str(e)}")
        except UserNotFoundError as e:
            messages.error(request, f"Usuário não encontrado: {e.message}")
        except ContractNotFoundError as e:
            messages.error(request, f"Contrato não encontrado: {e.message}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_delete_contract_view(request, contract_id: str):
    if request.method == "POST":
        try:
            DeleteContractUseCase(contract_repo=contract_repo).execute(UUID(contract_id))
            messages.success(request, "Contrato excluído com sucesso!")
        except ContractNotFoundError as e:
            messages.error(request, f"Contrato não encontrado: {e.message}")
        except DomainError as e:
            messages.error(request, f"Erro ao excluir contrato: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_update_project_status_view(request, project_id: str):
    if request.method == "POST":
        if not _user_can_access_project(request, UUID(project_id)):
            messages.error(request, "Você não tem permissão para modificar este projeto.")
            return redirect("/")
        try:
            dto = UpdateProjectStatusSchema(status=ProjectStatus(request.POST.get("status", "")))
            UpdateProjectStatusUseCase(project_repo, task_repo).execute(UUID(project_id), dto)
            messages.success(request, "Status do projeto atualizado!")
        except (ValidationError, ValueError):
            messages.error(request, "Status de projeto inválido.")
        except DomainError as e:
            messages.error(request, f"Erro ao alterar projeto: {e}")
    return redirect("/")


@login_required(login_url="/login")
def web_update_project_team_view(request, project_id: str):
    if request.method == "POST":
        if not _user_can_access_project(request, UUID(project_id)):
            messages.error(request, "Você não tem permissão para modificar este projeto.")
            return redirect("/")
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


@login_required(login_url="/login")
def web_update_project_view(request, project_id: str):
    if request.method == "POST":
        try:
            project_uuid = UUID(project_id)
        except ValueError:
            messages.error(request, "ID do projeto inválido.")
            return redirect("/")

        if not _user_can_access_project(request, project_uuid):
            messages.error(request, "Você não tem permissão para modificar este projeto.")
            return redirect("/")

        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        owner_id_str = request.POST.get("owner_id", "").strip()

        try:
            dto = UpdateProjectSchema(
                title=title if title else None,
                description=description if description else None,
                owner_id=UUID(owner_id_str) if owner_id_str else None,
            )
            UpdateProjectUseCase(project_repo=project_repo, user_repo=user_repo).execute(project_uuid, dto)
            messages.success(request, "Projeto atualizado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados do projeto inválidos.")
            messages.error(request, f"Erro de validação: {msg}")
        except ValueError as e:
            messages.error(request, f"Dados inválidos: {str(e)}")
        except UserNotFoundError as e:
            messages.error(request, f"Usuário não encontrado: {e.message}")
        except ProjectNotFoundError as e:
            messages.error(request, f"Projeto não encontrado: {e.message}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_delete_project_view(request, project_id: str):
    if request.method == "POST":
        if not _user_can_access_project(request, UUID(project_id)):
            messages.error(request, "Você não tem permissão para excluir este projeto.")
            return redirect("/")
        try:
            DeleteProjectUseCase(project_repo=project_repo).execute(UUID(project_id))
            messages.success(request, "Projeto excluído com sucesso!")
        except ProjectNotFoundError as e:
            messages.error(request, f"Projeto não encontrado: {e.message}")
        except DomainError as e:
            messages.error(request, f"Erro ao excluir projeto: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_create_task_view(request):
    if request.method == "POST":
        project_id_str = request.POST.get("project_id", "")
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        priority = request.POST.get("priority", "MEDIUM")
        assignee_id_str = request.POST.get("assignee_id", "")
        due_date_str = request.POST.get("due_date", "")

        try:
            if not _user_can_access_project(request, UUID(project_id_str)):
                messages.error(request, "Você não tem permissão para cadastrar tarefas neste projeto.")
                return redirect("/")

            from datetime import date
            due_date = None
            if due_date_str:
                due_date = date.fromisoformat(due_date_str)

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


@login_required(login_url="/login")
def web_update_task_status_view(request, task_id: str):
    if request.method == "POST":
        existing_task = task_repo.get_by_id(UUID(task_id))
        if existing_task and not _user_can_access_project(request, existing_task.project_id):
            messages.error(request, "Você não tem permissão para modificar esta tarefa.")
            return redirect("/")
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


@login_required(login_url="/login")
def web_update_task_view(request, task_id: str):
    if request.method == "POST":
        try:
            # Get and validate task exists first
            try:
                task_uuid = UUID(task_id)
            except ValueError:
                messages.error(request, "ID da tarefa inválido.")
                return redirect("/")

            task = task_repo.get_by_id(task_uuid)
            if not task:
                messages.error(request, "Tarefa não encontrada.")
                return redirect("/")

            if not _user_can_access_project(request, task.project_id):
                messages.error(request, "Você não tem permissão para modificar esta tarefa.")
                return redirect("/")

            # Extract form data
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()
            priority_str = request.POST.get("priority", "").strip()
            assignee_id_str = request.POST.get("assignee_id", "").strip()
            due_date_str = request.POST.get("due_date", "").strip()
            github_url = request.POST.get("github_url", "").strip()

            # Parse due_date
            from datetime import date
            due_date = None
            if due_date_str:
                parsed_due_date = date.fromisoformat(due_date_str)
                # Only treat as a change if it differs from the task's current
                # due date; otherwise resubmitting an unchanged (possibly past)
                # due date would fail the "must be future" validation on every edit.
                current_due_date = task.due_date
                if isinstance(current_due_date, datetime):
                    current_due_date = current_due_date.date()
                if parsed_due_date != current_due_date:
                    due_date = parsed_due_date

            # Build DTO with None for empty fields (partial update)
            dto = UpdateTaskSchema(
                title=title if title else None,
                description=description if description else None,
                priority=TaskPriority(priority_str) if priority_str else None,
                assignee_id=UUID(assignee_id_str) if assignee_id_str else None,
                due_date=due_date,
                github_url=github_url if github_url else None,
            )

            # Execute use case
            use_case = UpdateTaskUseCase(task_repo=task_repo, user_repo=user_repo)
            use_case.execute(task_uuid, dto)
            messages.success(request, "Tarefa atualizada com sucesso!")

        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados inválidos.")
            messages.error(request, f"Erro de validação: {msg}")
        except UserNotFoundError as e:
            messages.error(request, f"Usuário não encontrado: {e.message}")
        except TaskNotFoundError as e:
            messages.error(request, f"Tarefa não encontrada: {e.message}")
        except ValueError as e:
            messages.error(request, f"Dados inválidos: {str(e)}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar tarefa: {str(e)}")

    return redirect("/")


@login_required(login_url="/login")
def web_delete_task_view(request, task_id: str):
    if request.method == "POST":
        existing_task = task_repo.get_by_id(UUID(task_id))
        if existing_task and not _user_can_access_project(request, existing_task.project_id):
            messages.error(request, "Você não tem permissão para excluir esta tarefa.")
            return redirect("/")
        try:
            use_case = DeleteTaskUseCase(task_repo=task_repo)
            use_case.execute(UUID(task_id))
            messages.success(request, "Tarefa excluída com sucesso!")
        except DomainError as e:
            messages.error(request, f"Erro ao excluir tarefa: {e}")
        except Exception as e:
            messages.error(request, f"Erro ao excluir tarefa: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_create_requirement_view(request):
    if request.method == "POST":
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        req_type = request.POST.get("type", "")
        priority = request.POST.get("priority", "MEDIUM")
        project_id_str = request.POST.get("project_id", "")
        task_ids = [t for t in request.POST.getlist("task_ids") if t]
        actor_ids = [a for a in request.POST.getlist("actor_ids") if a]

        try:
            project_id = UUID(project_id_str)
            if not _user_can_access_project(request, project_id):
                messages.error(request, "Você não tem permissão para cadastrar requisitos neste projeto.")
                return redirect("/")

            dto = CreateRequirementSchema(
                project_id=project_id,
                title=title,
                description=description,
                type=RequirementType(req_type),
                priority=RequirementPriority(priority),
            )
            with transaction.atomic():
                requirement = CreateRequirementUseCase(requirement_repo, project_repo).execute(dto)
                for task_id in task_ids:
                    LinkRequirementToTaskUseCase(requirement_repo, task_repo).execute(
                        requirement.id, UUID(task_id)
                    )
                for actor_id in actor_ids:
                    LinkActorToRequirementUseCase(requirement_repo, actor_repo).execute(
                        requirement.id, UUID(actor_id)
                    )
            messages.success(request, f"Requisito '{requirement.code}' cadastrado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados do requisito inválidos.")
            messages.error(request, f"Erro ao criar requisito: {msg}")
        except ValueError:
            messages.error(request, "Projeto, tipo, prioridade, tarefa ou ator inválidos.")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


def _guard_requirement_access(request, requirement_id: str) -> bool:
    """True se o requisito não existir (deixa o use case reportar) ou se o usuário puder acessá-lo."""
    existing = requirement_repo.get_by_id(UUID(requirement_id))
    if existing is None:
        return True
    return _user_can_access_project(request, existing.project_id)


@login_required(login_url="/login")
def web_update_requirement_view(request, requirement_id: str):
    if request.method == "POST":
        if not _guard_requirement_access(request, requirement_id):
            messages.error(request, "Você não tem permissão para modificar este requisito.")
            return redirect("/")
        try:
            req_uuid = UUID(requirement_id)
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()
            type_str = request.POST.get("type", "").strip()
            priority_str = request.POST.get("priority", "").strip()
            task_ids = {UUID(t) for t in request.POST.getlist("task_ids") if t}
            actor_ids = {UUID(a) for a in request.POST.getlist("actor_ids") if a}

            dto = UpdateRequirementSchema(
                title=title if title else None,
                description=description if description else None,
                type=RequirementType(type_str) if type_str else None,
                priority=RequirementPriority(priority_str) if priority_str else None,
            )
            with transaction.atomic():
                UpdateRequirementUseCase(requirement_repo, project_repo).execute(req_uuid, dto)

                current_task_ids = {t.id for t in requirement_repo.list_linked_tasks(req_uuid)}
                for task_id in current_task_ids - task_ids:
                    UnlinkRequirementFromTaskUseCase(requirement_repo).execute(req_uuid, task_id)
                for task_id in task_ids - current_task_ids:
                    LinkRequirementToTaskUseCase(requirement_repo, task_repo).execute(req_uuid, task_id)

                current_actor_ids = {a.id for a in requirement_repo.list_linked_actors(req_uuid)}
                for actor_id in current_actor_ids - actor_ids:
                    UnlinkActorFromRequirementUseCase(requirement_repo).execute(req_uuid, actor_id)
                for actor_id in actor_ids - current_actor_ids:
                    LinkActorToRequirementUseCase(requirement_repo, actor_repo).execute(req_uuid, actor_id)

            messages.success(request, "Requisito atualizado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados inválidos.")
            messages.error(request, f"Erro de validação: {msg}")
        except ValueError as e:
            messages.error(request, f"Dados inválidos: {str(e)}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_update_requirement_status_view(request, requirement_id: str):
    if request.method == "POST":
        if not _guard_requirement_access(request, requirement_id):
            messages.error(request, "Você não tem permissão para modificar este requisito.")
            return redirect("/")
        status_str = request.POST.get("status", "")
        try:
            dto = UpdateRequirementStatusSchema(status=RequirementStatus(status_str))
            UpdateRequirementStatusUseCase(requirement_repo).execute(UUID(requirement_id), dto)
            messages.success(request, "Status do requisito atualizado!")
        except (ValidationError, ValueError):
            messages.error(request, "Status de requisito inválido.")
        except InvalidStatusTransitionError as e:
            messages.error(request, f"Transição inválida: {e.message}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_delete_requirement_view(request, requirement_id: str):
    if request.method == "POST":
        if not _guard_requirement_access(request, requirement_id):
            messages.error(request, "Você não tem permissão para excluir este requisito.")
            return redirect("/")
        try:
            DeleteRequirementUseCase(requirement_repo).execute(UUID(requirement_id))
            messages.success(request, "Requisito excluído com sucesso!")
        except DomainError as e:
            messages.error(request, f"Erro ao excluir requisito: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_update_requirement_tasks_view(request, requirement_id: str):
    if request.method == "POST":
        if not _guard_requirement_access(request, requirement_id):
            messages.error(request, "Você não tem permissão para modificar este requisito.")
            return redirect("/")
        try:
            task_id = UUID(request.POST.get("task_id", ""))
            if request.POST.get("action") == "remove":
                UnlinkRequirementFromTaskUseCase(requirement_repo).execute(UUID(requirement_id), task_id)
                messages.success(request, "Tarefa desvinculada do requisito!")
            else:
                LinkRequirementToTaskUseCase(requirement_repo, task_repo).execute(UUID(requirement_id), task_id)
                messages.success(request, "Tarefa vinculada ao requisito!")
        except (ValidationError, ValueError):
            messages.error(request, "Tarefa inválida.")
        except DomainError as e:
            messages.error(request, f"Erro ao vincular tarefa: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_update_requirement_actors_view(request, requirement_id: str):
    if request.method == "POST":
        if not _guard_requirement_access(request, requirement_id):
            messages.error(request, "Você não tem permissão para modificar este requisito.")
            return redirect("/")
        try:
            actor_id = UUID(request.POST.get("actor_id", ""))
            if request.POST.get("action") == "remove":
                UnlinkActorFromRequirementUseCase(requirement_repo).execute(UUID(requirement_id), actor_id)
                messages.success(request, "Ator desvinculado do requisito!")
            else:
                LinkActorToRequirementUseCase(requirement_repo, actor_repo).execute(UUID(requirement_id), actor_id)
                messages.success(request, "Ator vinculado ao requisito!")
        except (ValidationError, ValueError):
            messages.error(request, "Ator inválido.")
        except DomainError as e:
            messages.error(request, f"Erro ao vincular ator: {e}")

    return redirect("/")


def _guard_actor_access(request, actor_id: str) -> bool:
    """True se o ator não existir (deixa o use case reportar) ou se o usuário puder acessá-lo."""
    existing = actor_repo.get_by_id(UUID(actor_id))
    if existing is None:
        return True
    return _user_can_access_contract(request, existing.contract_id)


@login_required(login_url="/login")
def web_create_actor_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "")
        description = request.POST.get("description", "")
        contract_id_str = request.POST.get("contract_id", "")

        try:
            contract_id = UUID(contract_id_str)
            if not _user_can_access_contract(request, contract_id):
                messages.error(request, "Você não tem permissão para cadastrar atores neste contrato.")
                return redirect("/")

            dto = CreateActorSchema(contract_id=contract_id, name=name, description=description)
            CreateActorUseCase(actor_repo, contract_repo).execute(dto)
            messages.success(request, f"Ator '{dto.name}' cadastrado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados do ator inválidos.")
            messages.error(request, f"Erro ao criar ator: {msg}")
        except ValueError:
            messages.error(request, "Contrato inválido.")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_update_actor_view(request, actor_id: str):
    if request.method == "POST":
        if not _guard_actor_access(request, actor_id):
            messages.error(request, "Você não tem permissão para modificar este ator.")
            return redirect("/")
        try:
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()

            dto = UpdateActorSchema(
                name=name if name else None,
                description=description if description else None,
            )
            UpdateActorUseCase(actor_repo, contract_repo).execute(UUID(actor_id), dto)
            messages.success(request, "Ator atualizado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados inválidos.")
            messages.error(request, f"Erro de validação: {msg}")
        except ValueError as e:
            messages.error(request, f"Dados inválidos: {str(e)}")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_delete_actor_view(request, actor_id: str):
    if request.method == "POST":
        if not _guard_actor_access(request, actor_id):
            messages.error(request, "Você não tem permissão para excluir este ator.")
            return redirect("/")
        try:
            DeleteActorUseCase(actor_repo).execute(UUID(actor_id))
            messages.success(request, "Ator excluído com sucesso!")
        except DomainError as e:
            messages.error(request, f"Erro ao excluir ator: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_export_specification_view(request):
    if request.method == "POST":
        spec_path = settings.BASE_DIR / "SPECIFICATION.md"
        try:
            export_requirements_section(requirement_repo, task_repo, spec_path)
            messages.success(request, "SPECIFICATION.md atualizado com os requisitos cadastrados!")
        except (ValueError, OSError) as e:
            messages.error(request, f"Erro ao exportar especificação: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_create_user_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role", "MEMBER")
        password = request.POST.get("password", "")
        password_confirmation = request.POST.get("password_confirmation", "")

        if not name or not email or not password:
            messages.error(request, "Nome, e-mail e senha são obrigatórios.")
        elif len(password) < 8:
            messages.error(request, "A senha deve ter pelo menos 8 caracteres.")
        elif password != password_confirmation:
            messages.error(request, "As senhas não conferem.")
        elif DjangoUser.objects.filter(username=email).exists():
            messages.error(request, "Já existe um usuário com este e-mail.")
        else:
            try:
                role_enum = UserRole(role)
                auth_user = DjangoUser.objects.create_user(
                    username=email,
                    email=email,
                    first_name=name,
                    password=password,
                )
                user_repo.save(User(id=uuid4(), name=name, email=email, role=role_enum))
                messages.success(request, f"Usuário '{name}' cadastrado com acesso ao sistema!")
            except ValueError:
                messages.error(request, "Função de usuário inválida.")
            except Exception:
                if "auth_user" in locals() and auth_user.pk:
                    auth_user.delete()
                messages.error(request, "Não foi possível cadastrar o usuário.")

    return redirect("/")


@login_required(login_url="/login")
def download_contract_view(request, contract_file_path: str):
    """Download contract file with proper headers for browser."""
    if not contract_file_path:
        return HttpResponse("Arquivo não encontrado", status=404)

    try:
        file_content = default_storage.open(contract_file_path, 'rb')
        filename = os.path.basename(contract_file_path)

        response = FileResponse(file_content, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = default_storage.size(contract_file_path)

        return response
    except Exception as e:
        messages.error(request, f"Erro ao baixar arquivo: {str(e)}")
        return redirect("/")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get("next") or "/")
        messages.error(request, "E-mail ou senha inválidos.")
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("/login")


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
def contract_view(request, contract_id: str):
    try:
        contract_uuid = UUID(contract_id)
    except ValueError:
        return JsonResponse({"detail": "UUID do contrato inválido"}, status=422)

    if request.method in ["PUT", "PATCH"]:
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = UpdateContractSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = UpdateContractUseCase(contract_repo=contract_repo, user_repo=user_repo)
        try:
            contract = use_case.execute(contract_uuid, dto)
            response_dto = ContractResponseSchema(
                id=contract.id,
                title=contract.title,
                description=contract.description,
                contract_file=contract.contract_file,
                status=contract.status,
                owner_id=contract.owner_id,
                created_at=contract.created_at,
            )
            return JsonResponse(response_dto.model_dump(mode="json"), status=200)
        except ContractNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except UserNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "DELETE":
        use_case = DeleteContractUseCase(contract_repo=contract_repo)
        try:
            use_case.execute(contract_uuid)
            return JsonResponse({"message": "Contrato excluído com sucesso"}, status=204)
        except ContractNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
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
def project_view(request, project_id: str):
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return JsonResponse({"detail": "UUID do projeto inválido"}, status=422)

    if request.method in ["PUT", "PATCH"]:
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = UpdateProjectSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = UpdateProjectUseCase(project_repo=project_repo, user_repo=user_repo)
        try:
            project = use_case.execute(project_uuid, dto)
            response_dto = ProjectResponseSchema(
                id=project.id,
                contract_id=project.contract_id,
                title=project.title,
                description=project.description,
                owner_id=project.owner_id,
                created_at=project.created_at,
            )
            return JsonResponse(response_dto.model_dump(mode="json"), status=200)
        except ProjectNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except UserNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "DELETE":
        use_case = DeleteProjectUseCase(project_repo=project_repo)
        try:
            use_case.execute(project_uuid)
            return JsonResponse({"message": "Projeto excluído com sucesso"}, status=204)
        except ProjectNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
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


@csrf_exempt
def task_view(request, task_id: str):
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        return JsonResponse({"detail": "UUID da tarefa inválido"}, status=422)

    if request.method in ["PUT", "PATCH"]:
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = UpdateTaskSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = UpdateTaskUseCase(task_repo=task_repo, user_repo=user_repo)
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
        except UserNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "DELETE":
        use_case = DeleteTaskUseCase(task_repo=task_repo)
        try:
            use_case.execute(task_uuid)
            return JsonResponse({"message": "Tarefa excluída com sucesso"}, status=204)
        except TaskNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)


def _requirement_response(requirement) -> RequirementResponseSchema:
    return RequirementResponseSchema(
        id=requirement.id,
        project_id=requirement.project_id,
        code=requirement.code,
        title=requirement.title,
        description=requirement.description,
        type=requirement.type,
        priority=requirement.priority,
        status=requirement.status,
        created_at=requirement.created_at,
    )


@csrf_exempt
def requirements_view(request):
    if request.method == "GET":
        requirements = requirement_repo.list_all()
        return JsonResponse(
            [_requirement_response(r).model_dump(mode="json") for r in requirements],
            safe=False,
            status=200,
        )

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = CreateRequirementSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = CreateRequirementUseCase(requirement_repo, project_repo)
        try:
            requirement = use_case.execute(dto)
            return JsonResponse(_requirement_response(requirement).model_dump(mode="json"), status=201)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)


@csrf_exempt
def requirement_view(request, requirement_id: str):
    try:
        req_uuid = UUID(requirement_id)
    except ValueError:
        return JsonResponse({"detail": "UUID do requisito inválido"}, status=422)

    if request.method in ["PUT", "PATCH"]:
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = UpdateRequirementSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = UpdateRequirementUseCase(requirement_repo, project_repo)
        try:
            requirement = use_case.execute(req_uuid, dto)
            return JsonResponse(_requirement_response(requirement).model_dump(mode="json"), status=200)
        except RequirementNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "DELETE":
        use_case = DeleteRequirementUseCase(requirement_repo)
        try:
            use_case.execute(req_uuid)
            return JsonResponse({"message": "Requisito excluído com sucesso"}, status=204)
        except RequirementNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)


@csrf_exempt
def requirement_status_view(request, requirement_id: str):
    try:
        req_uuid = UUID(requirement_id)
    except ValueError:
        return JsonResponse({"detail": "UUID do requisito inválido"}, status=422)

    if request.method in ["PATCH", "POST"]:
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido"}, status=422)

        try:
            dto = UpdateRequirementStatusSchema(**body)
        except ValidationError as e:
            return _format_pydantic_error(e)

        use_case = UpdateRequirementStatusUseCase(requirement_repo)
        try:
            requirement = use_case.execute(req_uuid, dto)
            return JsonResponse(_requirement_response(requirement).model_dump(mode="json"), status=200)
        except RequirementNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except InvalidStatusTransitionError as e:
            return JsonResponse({"error": e.code, "message": e.message}, status=400)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)


@csrf_exempt
def requirement_tasks_view(request, requirement_id: str):
    try:
        req_uuid = UUID(requirement_id)
    except ValueError:
        return JsonResponse({"detail": "UUID do requisito inválido"}, status=422)

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
            task_uuid = UUID(body.get("task_id", ""))
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"detail": "JSON ou task_id inválido"}, status=422)

        try:
            if body.get("action") == "remove":
                UnlinkRequirementFromTaskUseCase(requirement_repo).execute(req_uuid, task_uuid)
            else:
                LinkRequirementToTaskUseCase(requirement_repo, task_repo).execute(req_uuid, task_uuid)
            linked_tasks = requirement_repo.list_linked_tasks(req_uuid)
            return JsonResponse({"linked_task_ids": [str(t.id) for t in linked_tasks]}, status=200)
        except RequirementNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except TaskNotFoundError as e:
            return JsonResponse({"error": e.message}, status=404)
        except DomainError as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"detail": "Método não permitido"}, status=405)
