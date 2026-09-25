"""Regras de visibilidade de Contratos/Projetos/Atores por perfil de usuário.

Convenção: um retorno `None` para um conjunto de IDs significa "sem restrição" (enxerga tudo).
Um `set()` vazio significa "nada visível" (ex.: MEMBER sem contrato selecionado).

Perfis:
* ADMIN: vê tudo. Selecionar um contrato no combo box apenas filtra a visão (não restringe).
* MEMBER: só vê os projetos/atores do contrato selecionado no combo box. Sem seleção, não vê nenhum.
* DEVELOPER / TEST / MANAGER / PRODUCT_OWNER: só veem os projetos dos quais são owner ou membro da
  equipe (e os atores/contratos desses projetos), independentemente de qualquer seleção de contrato —
  esses perfis não navegam por contrato.
"""
from typing import Dict, List, Optional, Set
from uuid import UUID

from .entities import Project, User
from .enums import UserRole


def can_browse_contracts(user: User) -> bool:
    """Indica se o combo box de seleção de contrato deve ser exibido para o usuário."""
    return user.role in (UserRole.ADMIN, UserRole.MEMBER)


def get_visible_project_ids(
    user: User,
    projects: List[Project],
    member_user_ids_by_project: Dict[UUID, Set[UUID]],
    selected_contract_id: Optional[UUID] = None,
) -> Optional[Set[UUID]]:
    """Projetos visíveis para o usuário. `None` = todos (sem restrição)."""
    if user.role == UserRole.ADMIN:
        if selected_contract_id is None:
            return None
        return {p.id for p in projects if p.contract_id == selected_contract_id}

    if user.role == UserRole.MEMBER:
        if selected_contract_id is None:
            return set()
        return {p.id for p in projects if p.contract_id == selected_contract_id}

    # DEVELOPER, TEST, MANAGER, PRODUCT_OWNER: apenas projetos próprios (owner ou membro da equipe)
    return {
        p.id
        for p in projects
        if p.owner_id == user.id or user.id in member_user_ids_by_project.get(p.id, set())
    }


def get_visible_contract_ids(
    user: User,
    projects: List[Project],
    visible_project_ids: Optional[Set[UUID]],
    selected_contract_id: Optional[UUID] = None,
) -> Optional[Set[UUID]]:
    """Contratos cujos dados (atores, tabela de contratos) devem ser exibidos. `None` = todos."""
    if user.role == UserRole.ADMIN:
        return {selected_contract_id} if selected_contract_id else None

    if user.role == UserRole.MEMBER:
        return {selected_contract_id} if selected_contract_id else set()

    if visible_project_ids is None:
        return None
    return {p.contract_id for p in projects if p.id in visible_project_ids and p.contract_id is not None}


def is_id_visible(entity_id: Optional[UUID], visible_ids: Optional[Set[UUID]]) -> bool:
    """`visible_ids is None` significa sem restrição (tudo visível)."""
    if visible_ids is None:
        return True
    return entity_id in visible_ids
