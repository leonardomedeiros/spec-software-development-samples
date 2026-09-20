# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TaskTrack** is a Django FullStack application for rigorous project and task management. It implements **Clean Architecture** (Domain, Use Cases, Adapters, Infrastructure) within Django's MVT pattern. The complete technical specification, SQL schemas, API contracts, and test cases are in `SPECIFICATION.md` — always read it first when implementing features.

## Quick Start

### Environment & Dependencies

This project uses **`uv`** (fast Python package manager). The `uv.lock` file is version-controlled.

```bash
# Install/sync dependencies
uv sync

# Run Django checks
uv run python manage.py check

# Apply database migrations
uv run python manage.py migrate

# Create a user for local development
uv run python manage.py create_tasktrack_user \
  --name "Leonardo" \
  --email user@example.com \
  --password "secure-password" \
  --role MANAGER

# Run development server
uv run python manage.py runserver
```

**After updating `pyproject.toml` dependencies:**
```bash
uv lock
uv sync
```

### Running Tests

```bash
# All tests
uv run pytest

# Single test file
uv run pytest tasktrack/tests/test_use_cases.py

# Specific test
uv run pytest tasktrack/tests/test_use_cases.py::TestCreateProjectUseCase::test_success

# With coverage
uv run pytest --cov=tasktrack
```

## Architecture: Clean Architecture in Django

TaskTrack uses **Clean Architecture** layered within Django:

```
tasktrack/
├── domain/          # Pure domain logic (entities, enums, exceptions, repositories interface)
├── use_cases/       # Application logic (orchestration, validation, business rules)
├── adapters/        # Controllers/Views (Django views, URL routing, schemas/DTOs)
├── infra/           # Infrastructure (Django models/ORM, repositories implementation)
├── schemas/         # Pydantic schemas (request/response validation)
└── management/      # Django management commands
```

### Key Architectural Patterns

**Dependency Injection via Constructor:**
- Use cases receive repositories in `__init__`
- Views instantiate use cases and repositories
- No service locator anti-pattern; explicit dependencies

**Repository Pattern:**
- All DB access goes through `ITaskRepository`, `IProjectRepository`, etc.
- Implementations in `infra/repositories.py` use Django ORM
- Allows swapping DB implementations without changing domain logic

**Pydantic for Validation:**
- Schema validation happens at adapter layer (views)
- DTOs cross the boundary between adapters and use cases
- Example: `CreateTaskSchema` validates title (3-100 chars), future due_date, etc.

**Domain Entities:**
- Immutable or minimally mutable (use dataclass)
- `Task.change_status()` enforces RN-04 (status transitions)
- `Contract.change_status()` enforces contract state machine
- Exceptions (`InvalidStatusTransitionError`) raised in domain, caught in adapters

### Data Flow Example: Create Task

```
View (adapters/views.py)
  └─> Validate form data + build CreateTaskSchema (Pydantic)
      └─> Call CreateTaskUseCase.execute(project_id, dto)
          └─> Domain: Check project exists, check assignee exists
          └─> Create Task entity, set status=PENDING, created_at, updated_at
          └─> Infra: task_repo.save(task) → ORM.save() → DB
          └─> Return Task entity to view
      └─> Build TaskResponseSchema, render in template
```

## Important Files & Responsibilities

**SPECIFICATION.md** → Authority for all requirements
- API contracts (endpoints, request/response)
- Business rules (RN-01 through RN-07)
- Edge cases (CB-01 through CB-07)
- Acceptance criteria (test scenarios)

**domain/entities.py** → Core business logic
- `Task`, `Project`, `Contract`, `User` dataclasses
- Methods: `Task.change_status(new_status)` validates transitions
- Exceptions: `InvalidStatusTransitionError`, `ProjectNotFoundError`, etc.

**use_cases/use_cases.py** → Orchestration
- `CreateTaskUseCase`, `UpdateTaskUseCase`, `DeleteTaskUseCase`
- `UpdateProjectStatusUseCase` (syncs all tasks when project status changes)
- Validate domain preconditions, call repositories, return entities

**infra/repositories.py** → ORM abstraction
- `DjangoTaskRepository`, `DjangoProjectRepository`, etc.
- Convert Django ORM models ↔ domain entities
- `get_by_id()`, `list_all()`, `list_by_project()`, `save()`, `delete()`

**infra/models.py** → Django ORM models
- `TaskModel`, `ProjectModel`, `ContractModel`, `UserModel`, `TaskHistoryModel`
- Mirrors domain entities; stores in PostgreSQL
- `TaskHistoryModel` records all changes (audit trail)

**adapters/views.py** → Web controllers
- `home_view()` renders dashboard with Kanban
- `web_create_task_view()`, `web_update_task_view()`, `web_delete_task_view()`
- REST API endpoints: `project_tasks_view()`, `task_status_view()`, `task_view()`
- Exception handling → convert domain errors to HTTP responses

**adapters/urls.py** → Routing (⚠️ Order matters!)
- Routes matched in order → specific routes before generic
- `/web/tasks/<task_id>/delete` MUST come before `/web/tasks/<task_id>`
- Web UI routes: `/web/tasks`, `/web/projects`, `/web/contracts`
- REST API routes: `/api/v1/tasks/<task_id>/status`, `/api/v1/tasks/<task_id>`

**templates/index.html** → Dashboard
- Kanban board: PENDING, IN_PROGRESS, COMPLETED columns
- Modals: edit task with 400px min-height textareas (Markdown support)
- Bootstrap 5 styling, form CSRF tokens, Django template tags

## Key Business Rules

**RN-04 (Task Status Transitions):**
- Allowed: PENDING→IN_PROGRESS, IN_PROGRESS→COMPLETED, IN_PROGRESS→PENDING, COMPLETED↔any (reabertura)
- Enforced in `Task.change_status()` — raises `InvalidStatusTransitionError` if invalid
- Full history tracked in `task_history` table (who, what, when, old/new values)

**RN-02 (Future Due Date):**
- `CreateTaskSchema` and `UpdateTaskSchema` validate `due_date > now(UTC)`
- Pydantic raises `ValidationError` if past date

**RN-05 (Assignee Validation):**
- If `assignee_id` provided, `CreateTaskUseCase` and `UpdateTaskUseCase` check user exists
- Raises `UserNotFoundError` → 404 in views

**RN-07 (Markdown in TEXT fields):**
- Descriptions (contracts, projects, tasks) stored as raw Markdown (up to 65KB)
- Textareas: `min-height: 400px` (~20 lines), `resize: vertical`
- Client responsible for rendering Markdown on display

**RN-06 (GitHub URL):**
- Optional field on tasks: `github_url` (max 255 chars)
- Links task to GitHub issues/PRs for traceability

## Important URLs & Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Dashboard (Kanban + stats) |
| `/web/tasks` | POST | Create task (from modal) |
| `/web/tasks/<id>` | POST | Edit task fields |
| `/web/tasks/<id>/delete` | POST | Delete task (with confirmation) |
| `/web/tasks/<id>/status` | POST | Change task status |
| `/api/v1/tasks/<id>` | PUT/PATCH | REST edit |
| `/api/v1/tasks/<id>` | DELETE | REST delete |
| `/api/v1/tasks/<id>/status` | PATCH | REST status change |
| `/login` | POST | Django auth login |
| `/logout` | GET | Django auth logout |

## Debugging & Common Issues

**DEBUG.md** contains a troubleshooting guide for task edit modal (F12 console, JavaScript, form submission).

**Modal not opening?** → Check browser console (F12) for JavaScript errors; verify `data-task-id` attributes on buttons.

**Edits not saving?** → Check Django console for validation errors; verify CSRF token in form; ensure task exists.

**Status transition fails?** → Check `Task.change_status()` logic in domain/entities.py; verify transition is in allowed_transitions dict.

**URL routing conflicts?** → Remember: specific routes MUST come before generic (`/delete` before `/<id>`).

## Dependency Management

```toml
# Main dependencies
django>=5.0,<6.0          # Web framework
pydantic>=2.0,<3.0        # Schema validation
psycopg2-binary>=2.9.9    # PostgreSQL driver
python-decouple>=3.8      # Environment config

# Dev dependencies  
pytest>=8.0.0             # Testing
pytest-django>=4.8.0      # Django test plugin
httpx>=0.27.0             # Async HTTP (for API tests)
```

## Code Review Checklist

When adding features or fixing bugs:

1. **Does SPECIFICATION.md need updating?** (new fields, rules, endpoints)
2. **Are all layers touched?** (domain, use_case, schema, repository, view, template)
3. **Is there a migration needed?** (new model fields → `makemigrations`, `migrate`)
4. **Is URL routing order correct?** (specific before generic)
5. **Is domain logic in `domain/`?** (not in views or use cases)
6. **Are repositories used for all DB access?** (not direct ORM in views)
7. **Is Pydantic validation at adapter boundary?** (not scattered)
8. **Do exceptions bubble up with context?** (catch and re-raise with useful messages)
9. **Are migrations versioned?** (`uv.lock` checked in)
10. **Is new code covered by tests?** (or noted as untestable in UI)

## Git Commit Policy

⚠️ **IMPORTANT: Claude must NEVER make commits automatically without explicit user permission.**

### Rules for Commits

1. **Ask First** - Always ask the user for permission before creating any commit
2. **Only After Request** - Create a commit ONLY when the user explicitly asks ("commit these changes", "make a commit", etc.)
3. **No Auto-Save** - Do NOT automatically commit at the end of a task or session
4. **Show Changes First** - Before committing, run `git status` and `git diff` to show the user what will be committed
5. **Confirm Message** - Present the proposed commit message to the user for approval before committing

### When User Asks for a Commit

1. Run `git status` to see all changes
2. Run `git diff` to preview changes
3. Review recent commits (`git log`) to match commit style
4. Draft commit message following the convention below
5. Show message to user for approval
6. Only then create commit with `git commit`

### Commit Message Convention

When user requests a commit, follow this format:

```
feat: brief description of what was added

- Detailed change 1
- Detailed change 2
- Detailed change 3

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

Categories:
- `feat:` new feature  
- `fix:` bug fix  
- `docs:` documentation only  
- `refactor:` code reorganization (no logic change)

### Example

```
feat: add task edit modal and github_url field

- Add UpdateTaskUseCase and DeleteTaskUseCase
- Add github_url VARCHAR(255) field to tasks
- Modal with 400px min-height textarea for descriptions
- Markdown support documentation in RN-07

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

**The user must explicitly approve before any commit is made.**
