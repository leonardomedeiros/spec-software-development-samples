# AGENTS.md

<!-- 
Configurações de execução do OpenCode para o projeto TaskTrack.

No Windows (PowerShell) para chamar o OpenCode via Docker:
docker run --name opencode -it --rm -v "$($PWD.Path):/workspace" -w /workspace ghcr.io/anomalyco/opencode

No Linux/WSL/macOS:
docker run --name opencode -it --rm -v "${PWD}:/workspace" -w /workspace ghcr.io/anomalyco/opencode

Prompt recomendado para o OpenCode:
"Atue como um Engenheiro de Software Sênior. Siga rigorosamente a especificação contida em @SPECIFICATION.md para implementar as camadas da arquitetura, os Use Cases e a suíte de testes unitários e de integração."
-->

## 1. Visão Geral do Projeto

**TaskTrack** é uma aplicação FullStack desenvolvida em **Django** para gestão rigorosa de projetos e tarefas (ciclo de vida de status, prioridades, prazos e atribuição de usuários responsáveis).

A especificação técnica completa, esquemas SQL, contratos de API e casos de teste encontram-se em `SPECIFICATION.md`.

### Procedimento obrigatório para qualquer solicitação de alteração

- Identifique primeiro o arquivo, símbolo, requisito ou comportamento mencionado pelo usuário.
- Leia os arquivos relevantes antes de planejar ou editar qualquer coisa. Quando o usuário mencionar `SPECIFICATION.md`, leia o arquivo na raiz deste projeto usando `read`.
- Use somente as ferramentas realmente disponíveis na sessão. Para localizar arquivos e trechos, use `glob`, `grep` e `read`; para alterar arquivos, use `edit` ou `write`.
- Nunca tente chamar uma ferramenta chamada `explore` se ela não estiver explicitamente disponível.
- Nunca emita chamadas no formato XML, como `<function=explore>` ou `<tool_call>`; faça chamadas de ferramentas usando o mecanismo nativo da sessão.
- Escolha o arquivo correto com base no caminho fornecido pelo usuário e no diretório atual do projeto. Não edite uma cópia em outro projeto.
- Execute a alteração solicitada diretamente depois de obter contexto suficiente. Não pare apenas descrevendo o que deveria ser feito.
- Preserve o escopo solicitado e não altere arquivos não relacionados sem necessidade.
- Depois da edição, releia o trecho alterado e execute uma validação adequada, como testes, checagem, lint ou validação de sintaxe.
- Informe ao usuário quais arquivos foram alterados e o resultado da validação.
- Para alterações simples e localizadas, não delegue a tarefa para outro agente; faça a leitura e a edição diretamente.

---

## 2. Stack Tecnológica

- **Linguagem:** Python 3.11+
- **Framework Web:** Django 5.x (Arquitetura MVT + Camada de Serviços/Use Cases)
- **Interface/Views:** Django Templates estilizados com Bootstrap 5
- **Banco de Dados / Persistência:** PostgreSQL 16+ via Django ORM
- **Validação de Dados & Schemas:** Pydantic v2
- **Testes Automatizados:** `django.test` / `pytest` + `httpx` (ou `django.test.Client`)
- **Containerização:** Docker e Docker Compose

---

## 3. Arquitetura e Estrutura de Camadas

A aplicação deve seguir uma separação clara de responsabilidades:

1. `Domain`: Entidades puras, objetos de valor (Value Objects), Enums e exceções de domínio (ex: `InvalidStatusTransitionError`).
2. `Use Cases / Services`: Regras de negócio da aplicação, validação de fluxo e orquestração.
3. `Adapters / Views / Schemas`: Controllers/Views do Django, formulários, serializadores/schemas Pydantic v2 e templates Bootstrap.
4. `Infrastructure`: Models do Django ORM, migrations, repositórios de persistência e integrações externas.

**Regra Arquitetural:** É proibido acoplar regras de negócio diretamente nas Views ou Templates. A lógica de transição e validação deve residir no domínio / use cases.

---

## 4. Regras de Negócio e Casos de Borda (SPECIFICATION.md)

### 4.1 Regras de Negócio (RN)
- **RN-01 (Validação de Título):** O título da tarefa deve conter entre 3 e 100 caracteres e não pode ser composto apenas por espaços em branco.
- **RN-02 (Data de Vencimento Futura):** A `due_date` de uma nova tarefa deve obrigatoriamente ser posterior ao momento da requisição (`due_date > agora`).
- **RN-03 (Valores Permitidos de Enums):**
  - `status`: `PENDING`, `IN_PROGRESS`, `COMPLETED`
  - `priority`: `LOW`, `MEDIUM`, `HIGH`
  - `role`: `ADMIN`, `MEMBER`
- **RN-04 (Ciclo de Vida do Status):**
  - Transições permitidas:
    - `PENDING` ➔ `IN_PROGRESS`
    - `IN_PROGRESS` ➔ `COMPLETED`
    - `IN_PROGRESS` ➔ `PENDING`
  - **Transição proibida:** Uma tarefa com status `COMPLETED` **não pode** retornar para `PENDING` ou `IN_PROGRESS`.
- **RN-05 (Atribuição de Responsável):** Se `assignee_id` for informado, deve ser validado se o UUID existe na tabela de usuários.

### 4.2 Casos de Borda (CB)
- **CB-01 (Projeto Inexistente):** Criar tarefa com `project_id` inexistente ➔ Retornar `404 Not Found` (`"Projeto não encontrado"`).
- **CB-02 (Data no Passado):** Criar tarefa com data retroativa ➔ Pydantic intercepta e retorna `422 Unprocessable Entity` (`"A data de vencimento não pode ser no passado."`).
- **CB-03 (Reabertura Inválida):** Alterar de `COMPLETED` para `IN_PROGRESS` ou `PENDING` ➔ Retornar `400 Bad Request` com código `"INVALID_STATUS_TRANSITION"`.
- **CB-04 (Usuário Inexistente):** `assignee_id` inválido/inexistente ➔ Retornar `404 Not Found` (`"Usuário atribuído não existe"`).

---

## 5. Modelo de Dados

### 5.1 Entidades Principais
- **User:** `id` (UUID), `name` (VARCHAR 100), `email` (VARCHAR 255 UNIQUE), `role` (`ADMIN` | `MEMBER`), `created_at`.
- **Project:** `id` (UUID), `title` (VARCHAR 120), `description` (TEXT), `owner_id` (FK User ON DELETE RESTRICT), `created_at`.
- **Task:** `id` (UUID), `project_id` (FK Project ON DELETE CASCADE), `title` (VARCHAR 100), `description` (TEXT), `status` (`PENDING` | `IN_PROGRESS` | `COMPLETED`), `priority` (`LOW` | `MEDIUM` | `HIGH`), `assignee_id` (FK User ON DELETE SET NULL, opcional), `due_date` (TIMESTAMP WITH TIME ZONE), `created_at`, `updated_at`.

---

## 6. Diretrizes de Implementação e Código

Antes de modificar ou criar qualquer módulo:
1. Verifique `SPECIFICATION.md` para garantir conformidade de contratos e nomes de campos.
2. Implemente validações Pydantic v2 para payloads de entrada.
3. Não use `except Exception: pass`. Trate erros de forma explícita com mensagens informativas e logs adequados.
4. Escreva testes automatizados para cobrir todos os cenários felizes e casos de borda especificados.

---

## 7. Comandos Recomendados

### Django & Testes
- Checagem do Django:
  ```bash
  python manage.py check
  ```
- Criação e execução de migrações:
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- Executar suíte de testes:
  ```bash
  python manage.py test
  ```
  ou com pytest:
  ```bash
  pytest
  ```

### Docker
- Subir banco de dados e aplicação:
  ```bash
  docker compose up -d
  ```