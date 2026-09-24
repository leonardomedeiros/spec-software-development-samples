from pathlib import Path

from ..domain.entities import Actor, Requirement, Task
from ..domain.repositories import IRequirementRepository, ITaskRepository

START_MARKER = "<!-- REQUISITOS:START -->"
END_MARKER = "<!-- REQUISITOS:END -->"

_TYPE_LABELS = {
    "FUNCTIONAL": "Requisito Funcional",
    "NON_FUNCTIONAL": "Requisito Não-Funcional",
    "BUSINESS_RULE": "Regra de Negócio",
    "TECHNICAL_CONSTRAINT": "Restrição Técnica",
}


def _render_requirement(requirement: Requirement, linked_tasks: list[Task], linked_actors: list[Actor]) -> str:
    lines = [
        f"**{requirement.code} — {requirement.title}**",
        f"*Tipo: {_TYPE_LABELS.get(requirement.type.value, requirement.type.value)} "
        f"| Prioridade: {requirement.priority.value} | Status: {requirement.status.value}*",
    ]
    if requirement.description:
        lines.append("")
        lines.append(requirement.description)
    lines.append("")
    if linked_tasks:
        lines.append("Tarefas vinculadas:")
        for task in linked_tasks:
            lines.append(f"* {task.title} (`{task.status.value}`)")
    else:
        lines.append("Tarefas vinculadas: _nenhuma tarefa vinculada._")
    lines.append("")
    if linked_actors:
        lines.append("Atores vinculados:")
        for actor in linked_actors:
            lines.append(f"* {actor.name} (`{actor.display_id}`)")
    else:
        lines.append("Atores vinculados: _nenhum ator vinculado._")
    return "\n".join(lines)


def build_requirements_section(requirement_repo: IRequirementRepository, task_repo: ITaskRepository) -> str:
    requirements = requirement_repo.list_all()
    if not requirements:
        return "_Nenhum requisito cadastrado ainda. Use o dashboard ou `export_specification` para gerar esta seção._"

    blocks = [
        _render_requirement(
            requirement,
            requirement_repo.list_linked_tasks(requirement.id),
            requirement_repo.list_linked_actors(requirement.id),
        )
        for requirement in requirements
    ]
    return "\n\n".join(blocks)


def export_requirements_section(
    requirement_repo: IRequirementRepository,
    task_repo: ITaskRepository,
    spec_path: Path,
) -> None:
    content = spec_path.read_text(encoding="utf-8")
    start_count = content.count(START_MARKER)
    end_count = content.count(END_MARKER)
    if start_count != 1 or end_count != 1:
        raise ValueError(
            f"Esperava exatamente um par de marcadores '{START_MARKER}' / '{END_MARKER}' em {spec_path}, "
            f"mas encontrou {start_count} início(s) e {end_count} fim(ns). "
            "Não é possível exportar os requisitos com segurança."
        )

    start_index = content.index(START_MARKER)
    end_index = content.index(END_MARKER, start_index + len(START_MARKER))
    if end_index < start_index:
        raise ValueError(f"Marcador de fim '{END_MARKER}' aparece antes do marcador de início em {spec_path}.")

    section = build_requirements_section(requirement_repo, task_repo)
    new_content = (
        content[:start_index]
        + f"{START_MARKER}\n{section}\n{END_MARKER}"
        + content[end_index + len(END_MARKER):]
    )
    spec_path.write_text(new_content, encoding="utf-8")
