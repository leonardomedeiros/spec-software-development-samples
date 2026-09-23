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
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

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
    DomainError,
    InvalidStatusTransitionError,
    ProjectNotFoundError,
    RequirementNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from ..infra.repositories import (
    DjangoContractRepository,
    DjangoProjectRepository,
    DjangoRequirementRepository,
    DjangoTaskRepository,
    DjangoUserRepository,
)
from ..schemas.schemas import (
    ContractResponseSchema,
    CreateContractSchema,
    CreateProjectSchema,
    CreateRequirementSchema,
    CreateTaskSchema,
    ProjectResponseSchema,
    RequirementResponseSchema,
    TaskResponseSchema,
    UpdateContractStatusSchema,
    UpdateProjectStatusSchema,
    UpdateRequirementSchema,
    UpdateRequirementStatusSchema,
    UpdateTaskStatusSchema,
    UpdateTaskSchema,
)
from ..use_cases.specification_export import export_requirements_section
from ..use_cases.use_cases import (
    CreateContractUseCase,
    CreateProjectUseCase,
    CreateRequirementUseCase,
    CreateTaskUseCase,
    AddProjectTeamMemberUseCase,
    DeleteRequirementUseCase,
    LinkRequirementToTaskUseCase,
    RemoveProjectTeamMemberUseCase,
    UnlinkRequirementFromTaskUseCase,
    UpdateContractStatusUseCase,
    UpdateProjectStatusUseCase,
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

@login_required(login_url="/login")
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
        project.team_members = project_repo.list_team_members(project.id)
        project.team_member_ids = {member.id for member in project.team_members}

    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
    in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
    completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

    all_tasks = task_repo.list_all()
    requirements = requirement_repo.list_all()
    for requirement in requirements:
        requirement.linked_tasks = requirement_repo.list_linked_tasks(requirement.id)
        requirement.linked_task_ids = {t.id for t in requirement.linked_tasks}

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


@login_required(login_url="/login")
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
        code = request.POST.get("code", "")
        title = request.POST.get("title", "")
        description = request.POST.get("description", "")
        req_type = request.POST.get("type", "")
        priority = request.POST.get("priority", "MEDIUM")

        try:
            dto = CreateRequirementSchema(
                code=code,
                title=title,
                description=description,
                type=RequirementType(req_type),
                priority=RequirementPriority(priority),
            )
            CreateRequirementUseCase(requirement_repo).execute(dto)
            messages.success(request, f"Requisito '{code}' cadastrado com sucesso!")
        except ValidationError as e:
            msg = e.errors()[0].get("msg", "Dados do requisito inválidos.")
            messages.error(request, f"Erro ao criar requisito: {msg}")
        except ValueError:
            messages.error(request, "Tipo ou prioridade de requisito inválidos.")
        except DomainError as e:
            messages.error(request, f"Erro de domínio: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_update_requirement_view(request, requirement_id: str):
    if request.method == "POST":
        try:
            code = request.POST.get("code", "").strip()
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()
            type_str = request.POST.get("type", "").strip()
            priority_str = request.POST.get("priority", "").strip()

            dto = UpdateRequirementSchema(
                code=code if code else None,
                title=title if title else None,
                description=description if description else None,
                type=RequirementType(type_str) if type_str else None,
                priority=RequirementPriority(priority_str) if priority_str else None,
            )
            UpdateRequirementUseCase(requirement_repo).execute(UUID(requirement_id), dto)
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
        try:
            DeleteRequirementUseCase(requirement_repo).execute(UUID(requirement_id))
            messages.success(request, "Requisito excluído com sucesso!")
        except DomainError as e:
            messages.error(request, f"Erro ao excluir requisito: {e}")

    return redirect("/")


@login_required(login_url="/login")
def web_update_requirement_tasks_view(request, requirement_id: str):
    if request.method == "POST":
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

        use_case = CreateRequirementUseCase(requirement_repo)
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

        use_case = UpdateRequirementUseCase(requirement_repo)
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
