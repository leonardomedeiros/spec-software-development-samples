# Especificação Técnica: Aplicação FullStack de Gestão de Tarefas (TaskTrack)

---

## 1. Visão Geral e Stack

### 1.1 Objetivo
O **TaskTrack** é uma aplicação FullStack com Django responsável pelo gerenciamento de projetos e suas respectivas tarefas. O sistema permite a criação de projetos, cadastro de tarefas com prioridades e prazos, atribuição de usuários responsáveis e controle rigoroso do ciclo de vida dos status das tarefas.

### 1.2 Stack Tecnológica
* **Linguagem:** Python 3.11+
* **Framework Web:** Django usando o ORM para gerar em PostGresSql 16+ e a view sendo feito por Django Template com Bootstrap
* **Persistência / ORM:** PostGresSql 16+ 
* **Validação de Dados:** Pydantic v2
* **Testes Unitários:** Usar o módulo django.tests para criar os tests unitários da aplicação
* **Containerização:** Docker e Docker Compose

### 1.3 Arquitetura e Restrições
* **Padrão Arquitetural:** Usar a arquitetura padrão do Django MVT (Model Vview Template)
  1. `Domain`: Entidades puras, objetos de valor e exceções de domínio.
  2. `Use Cases`: Regras de negócio da aplicação e orquestração.
  3. `Adapters / Controllers`: Controllers do Django, Models do Django.
  4. `Infrastructure`: Repositórios do Models do Django integração com Banco de Dados e configurações externas.
* **Restrição de Camadas:** É proibido interpor as camadas da MVT do django.

---

## 2. Entidades e Dados

### 2.1 Modelo de Dados (DDL SQL)

```sql
-- Tabela de Usuários
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'MEMBER', -- 'ADMIN', 'MEMBER'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Projetos
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(120) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Tarefas
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'IN_PROGRESS', 'COMPLETED'
    priority VARCHAR(10) NOT NULL DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH'
    assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Relacionamentos
* **User -> Project:** 1 Usuário pode ser proprietário (*owner*) de N Projetos (1:N).
* **Project -> Task:** 1 Projeto possui N Tarefas (1:N). Ao excluir um Projeto, suas Tarefas são excluídas em cascata (`CASCADE`).
* **User -> Task:** 1 Usuário pode ser atribuído como responsável a N Tarefas (1:N).

---

## 3. Interface Gráfica WEB (Django Templates + Bootstrap 5)

A aplicação disponibiliza uma interface visual completa renderizada via Django Templates e estilizada com Bootstrap 5:

### 3.1 Página Inicial / Dashboard (`GET /`)
* **Rota:** `/` (ou `/?project_id={uuid}`)
* **Recursos visuais:**
  * **Barra de Métricas:** Contadores em tempo real do total de Projetos, Tarefas Pendentes, Em Andamento e Concluídas.
  * **Filtro por Projeto:** Navegação rápida para filtrar as tarefas por projeto selecionado.
  * **Quadro Kanban de Tarefas:** Dividido em 3 colunas de status:
    * `PENDING` (Pendentes): Cartões com badge de prioridade, prazo e botão *"Iniciar"* para transição direta para `IN_PROGRESS`.
    * `IN_PROGRESS` (Em Andamento): Cartões com botões *"Voltar"* (para `PENDING`) e *"Concluir"* (para `COMPLETED`).
    * `COMPLETED` (Concluídas): Cartões arquivados, aplicando a **RN-04** (bloqueio de reabertura).
  * **Modais Interativos:**
    * Modal de Criação de Projeto.
    * Modal de Cadastro de Tarefa (com seleção de prioridade, projeto, responsável e data de vencimento).
    * Modal de Cadastro de Usuários (para membros da equipe).

### 3.2 Ações e Formulários Web
* **Criar Projeto:** `POST /web/projects` (Campos: `title`, `description`, `owner_id`).
* **Cadastrar Tarefa:** `POST /web/tasks` (Campos: `project_id`, `title`, `description`, `priority`, `assignee_id`, `due_date`).
* **Alterar Status:** `POST /web/tasks/{task_id}/status` (Campo: `status`).
* **Cadastrar Usuário:** `POST /web/users` (Campos: `name`, `email`, `role`).

---

## 4. Contratos de API REST (v1)

### 4.1 Criar Projeto
* **Endpoint:** `POST /api/v1/projects`
* **Descrição:** Cria um novo projeto no sistema.
* **Headers:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "title": "Reformulação do E-commerce",
  "description": "Projeto focado na migração da vitrine de produtos.",
  "owner_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
}
```
* **Respostas:**
  * `201 Created`:
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Reformulação do E-commerce",
  "description": "Projeto focado na migração da vitrine de produtos.",
  "owner_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "created_at": "2026-09-12T08:00:00Z"
}
```
  * `400 Bad Request`: Usuário proprietário não encontrado.
  * `422 Unprocessable Entity`: Dados de entrada inválidos.

---

### 4.2 Criar Tarefa
* **Endpoint:** `POST /api/v1/projects/{project_id}/tasks`
* **Descrição:** Cadastra uma nova tarefa vinculada a um projeto existente.
* **Path Parameter:** `project_id` (UUID)
* **Request Body:**
```json
{
  "title": "Implementar Gateway de Pagamento",
  "description": "Integrar API da Zoop para checkout transparente.",
  "priority": "HIGH",
  "assignee_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "due_date": "2026-10-15T23:59:59Z"
}
```
* **Respostas:**
  * `201 Created`:
```json
{
  "id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "project_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Implementar Gateway de Pagamento",
  "description": "Integrar API da Zoop para checkout transparente.",
  "status": "PENDING",
  "priority": "HIGH",
  "assignee_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "due_date": "2026-10-15T23:59:59Z",
  "created_at": "2026-09-12T08:30:00Z",
  "updated_at": "2026-09-12T08:30:00Z"
}
```
  * `404 Not Found`: Projeto não encontrado.
  * `422 Unprocessable Entity`: Data retroativa ou campos obrigatórios ausentes.

---

### 4.3 Atualizar Status da Tarefa
* **Endpoint:** `PATCH /api/v1/tasks/{task_id}/status`
* **Descrição:** Altera o status de uma tarefa específica.
* **Path Parameter:** `task_id` (UUID)
* **Request Body:**
```json
{
  "status": "IN_PROGRESS"
}
```
* **Respostas:**
  * `200 OK`: Retorna o objeto completo da tarefa com o status atualizado.
  * `400 Bad Request`: Transição de status inválida.
  * `404 Not Found`: Tarefa não encontrada.

---

## 5. Regras de Negócio e Casos de Borda

### 5.1 Regras de Negócio (RN)
* **RN-01 (Validação de Título):** O título da tarefa deve conter entre 3 e 100 caracteres e não pode ser composto apenas por espaços em branco.
* **RN-02 (Data de Vencimento Futura):** A `due_date` de uma nova tarefa deve obrigatoriamente ser posterior ao momento da requisição (`due_date > agora`).
* **RN-03 (Valores Permitidos de Enums):**
  * `status`: Apenas `PENDING`, `IN_PROGRESS`, `COMPLETED`.
  * `priority`: Apenas `LOW`, `MEDIUM`, `HIGH`.
* **RN-04 (Ciclo de Vida do Status):**
  * Transições permitidas: `PENDING` ➔ `IN_PROGRESS`, `IN_PROGRESS` ➔ `COMPLETED`, `IN_PROGRESS` ➔ `PENDING`.
  * Transição proibida: Uma tarefa no status `COMPLETED` não pode retornar para `PENDING` ou `IN_PROGRESS`.
* **RN-05 (Atribuição de Responsável):** Se o `assignee_id` for informado, o sistema deve validar se o UUID existe na tabela `users`.

### 5.2 Casos de Borda (CB)
* **CB-01 (Projeto Inexistente):** Tentar criar uma tarefa enviando um `project_id` inexistente deve retornar `404 Not Found` com mensagem `"Projeto não encontrado"`.
* **CB-02 (Data no Passado):** Enviar `due_date = "2020-01-01T00:00:00Z"` deve ser interceptado pelo Pydantic e retornar `422 Unprocessable Entity` com mensagem `"A data de vencimento não pode ser no passado."`.
* **CB-03 (Reabertura Inválida):** Tentar alterar o status de `COMPLETED` para `IN_PROGRESS` deve retornar `400 Bad Request` com código de erro de domínio `"INVALID_STATUS_TRANSITION"`.
* **CB-04 (Usuário Inexistente):** Informar um `assignee_id` não cadastrado deve retornar `404 Not Found` com a mensagem `"Usuário atribuído não existe"`.

---

## 6. Critérios de Aceite (Exemplos para Testes Automatizados)

Estes cenários devem orientar a geração de testes automatizados com `pytest` e `httpx`.

### Cenário 1: Sucesso na Criação de Tarefa
* **Dado** que existe um projeto cadastrado com `id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"`
* **Quando** for enviada uma requisição `POST` para `/api/v1/projects/f47ac10b-58cc-4372-a567-0e02b2c3d479/tasks` com o payload:
  ```json
  {
    "title": "Criar Testes de Integração",
    "description": "Cobrir casos felizes e de erro.",
    "priority": "HIGH",
    "due_date": "2026-12-31T23:59:59Z"
  }
  ```
* **Então** o código de status HTTP retornado deve ser `201 Created`
* **E** o corpo da resposta deve conter o campo `id` em formato UUID
* **E** o campo `status` deve ser inicializado automaticamente como `"PENDING"`.

### Cenário 2: Falha por Data Retroativa
* **Dado** que a data atual é `2026-09-12`
* **Quando** for enviada uma requisição `POST` com `due_date = "2025-01-01T00:00:00Z"`
* **Então** o código de status HTTP retornado deve ser `422 Unprocessable Entity`
* **E** o corpo da resposta deve detalhar o erro:
  ```json
  {
    "detail": [
      {
        "loc": ["body", "due_date"],
        "msg": "A data de vencimento não pode ser no passado.",
        "type": "value_error"
      }
    ]
  }
  ```

### Cenário 3: Transição Inválida de Status
* **Dado** uma tarefa salva no banco com status `COMPLETED`
* **Quando** for enviada uma requisição `PATCH` para `/api/v1/tasks/{task_id}/status` com `{"status": "IN_PROGRESS"}`
* **Então** o status HTTP deve ser `400 Bad Request`
* **E** o corpo da resposta deve conter:
  ```json
  {
    "error": "INVALID_STATUS_TRANSITION",
    "message": "Tarefas concluídas não podem ter seu status alterado."
  }
  ```


