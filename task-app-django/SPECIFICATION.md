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

### 2.0 Formato de Texto - Markdown Support com Campos Expandidos

Todos os campos `TEXT` (descrições de contratos, projetos e tarefas) suportam **Markdown** para formatação de texto rico:
- **Negrito**: `**texto**`
- *Itálico*: `*texto*`
- `Código`: `` `código` ``
- Títulos: `# Título 1`, `## Título 2`, etc.
- Listas: `- Item 1`, `- Item 2`
- Links: `[texto](url)`

#### Dimensões dos Campos de Descrição

| Campo | Altura Mínima | Linhas | Redimensionável | Markdown |
|-------|:---:|:---:|:---:|:---:|
| Contrato (Descrição) | 400px | ~20 | ✅ Vertical | ✅ Sim |
| Projeto (Descrição) | 400px | ~20 | ✅ Vertical | ✅ Sim |
| Tarefa (Criar) | 400px | ~20 | ✅ Vertical | ✅ Sim |
| Tarefa (Editar) | 400px | ~20 | ✅ Vertical | ✅ Sim |

#### Exemplos de Uso

Descrição de tarefa:
```
**Requisito**: Implementar autenticação OAuth2

## Detalhes
- Validar PKCE
- Integrar com Google/GitHub
- Suportar SAML 2.0

## Aceitação
- [x] Testes unitários
- [x] Testes de integração
- [ ] Testes de segurança

## Referências
- [Issue #42](https://github.com/...)
- [RFC 6749](https://tools.ietf.org/html/rfc6749)
```

Descrição de projeto:
```
## Visão Geral
Refatoração completa do módulo de autenticação

## Escopo
- Fase 1: Análise e design
- Fase 2: Implementação
- Fase 3: Testes

## Riscos
- Risco de compatibilidade com clientes legados
- Impacto em performance durante transição
```

Os campos TEXT são armazenados como markdown puro no BD (até 65KB por campo).

### 2.0.1 Formato de Datas (Due Date)

A `due_date` (data de vencimento) é um campo **OPCIONAL** que usa o tipo `DATE` (sem hora):
* **Formato:** `YYYY-MM-DD` (ex: `"2026-12-31"`)
* **Armazenamento:** 
  - **PostgreSQL/SQL:** Tipo `DATE` (apenas data, sem componente de hora)
  - **Django ORM:** `models.DateField(null=True, blank=True)`
  - **Python:** Tipo `date` do módulo `datetime` (ou `None`)
  - **Banco de dados:** Pode ser `NULL`
* **Validação:**
  - Quando fornecida, deve ser **posterior ao dia atual** (não aceita datas passadas nem a data de hoje)
  - Campo vazio no formulário é equivalente a `null` no banco de dados
  - Pode ser preenchida durante a criação ou atribuída posteriormente via edição
* **Interface:** Input HTML `type="date"` no navegador (sem seletor de hora)
* **Conversão:** O JavaScript converte automaticamente datas do banco para formato `YYYY-MM-DD` para exibição no formulário de edição

### 2.1 Modelo de Dados (DDL SQL)

```sql
-- Tabela de Usuários
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'MEMBER', -- 'ADMIN', 'MEMBER', 'DEVELOPER', 'TEST', 'MANAGER', 'PRODUCT_OWNER'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- Tabela de Contratos
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(120) NOT NULL,
    description TEXT,
    contract_file VARCHAR(255), -- caminho do arquivo do contrato (ex: PDF)
    status VARCHAR(20) NOT NULL DEFAULT 'PROSPECTING', -- 'PROSPECTING', 'IN_PROGRESS', 'SIGNED'
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- Tabela de Projetos
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    title VARCHAR(120) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

  -- Membros das equipes de projeto
  CREATE TABLE project_memberships (
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id)
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
    due_date DATE, -- Data de vencimento (opcional, formato YYYY-MM-DD)
    github_url VARCHAR(255), -- URL relativa a esta tarefa no GitHub (issue, PR, etc)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Histórico de Auditoria de Tarefas
CREATE TABLE task_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    changed_by_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    field_name VARCHAR(50) NOT NULL, -- 'title', 'description', 'status', 'priority', 'assignee_id', 'due_date', 'github_url'
    old_value TEXT, -- Valor anterior do campo
    new_value TEXT, -- Novo valor do campo
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Relacionamentos
* **Contract -> Project:** 1 Contrato possui N Projetos (1:N). Ao excluir um Contrato, seus Projetos são excluídas em cascata (`CASCADE`).
* **Contrato:** é a entidade raiz do vínculo; não possui `contract_id` nem referencia outro contrato.
* **User -> Project:** 1 Usuário pode ser proprietário (*owner*) de N Projetos (1:N).
* **Project -> Task:** 1 Projeto possui N Tarefas (1:N). Ao excluir um Projeto, suas Tarefas são excluídas em cascata (`CASCADE`).
* **User -> Task:** 1 Usuário pode ser atribuído como responsável a N Tarefas (1:N).

### 2.4 Equipes de Projetos

* Um projeto pode possuir vários membros e um usuário pode participar de vários projetos (N:N), por meio da tabela `project_memberships`.
* A combinação `project_id` + `user_id` é única; adicionar um membro já vinculado não cria duplicidade.
* Ao excluir um projeto ou usuário, seus vínculos de equipe são removidos em cascata.
* O proprietário do projeto continua sendo armazenado em `projects.owner_id`; membros da equipe são usuários adicionais autorizados a participar do projeto.

### 2.5 Autenticação e Funções de Usuário

* O acesso à interface web deve usar a autenticação nativa do Django (`django.contrib.auth`), com sessão, login por e-mail e senha e logout.
* O usuário de autenticação do Django deve ser criado com `username` igual ao e-mail; a senha deve ser armazenada somente pelo mecanismo de hash do Django.
* O perfil de domínio (`users`) deve manter a função do usuário. Os valores permitidos são `ADMIN`, `MEMBER`, `DEVELOPER`, `TEST`, `MANAGER` e `PRODUCT_OWNER`.
* O cadastro de usuário deve exigir nome, e-mail, senha, confirmação de senha e função, criando o usuário Django e o perfil de domínio correspondente.
* O dashboard e as ações web devem exigir usuário autenticado; endpoints REST permanecem independentes da sessão web.
* Para inicializar uma base sem usuários, disponibilizar o comando:
  `python manage.py create_tasktrack_user --name "Nome" --email usuario@exemplo.com --password "senha-segura" --role MANAGER`.

### 2.3 Status de Contratos e Projetos

* **Contrato:** o campo `status` aceita `PROSPECTING`, `IN_PROGRESS` ou `SIGNED`, iniciando em `PROSPECTING`.
  * Transições permitidas: `PROSPECTING` -> `IN_PROGRESS`, `IN_PROGRESS` -> `PROSPECTING` e `IN_PROGRESS` -> `SIGNED`.
  * `SIGNED` é um estado final e não pode retornar para outro status.
* **Projeto:** o status é calculado a partir das tarefas relacionadas e não é armazenado como uma coluna própria:
  * `PENDING` quando houver tarefas pendentes e nenhuma tarefa em andamento;
  * `IN_PROGRESS` quando houver ao menos uma tarefa em andamento;
  * `COMPLETED` quando todas as tarefas estiverem concluídas;
  * `NO_TASKS` quando o projeto não possuir tarefas.
  * A alteração para `PENDING` move as tarefas do projeto para `PENDING`;
  * A alteração para `IN_PROGRESS` move as tarefas pendentes para `IN_PROGRESS`;
  * A alteração para `COMPLETED` conclui as tarefas pendentes ou em andamento;
  * Não é permitido reabrir um projeto com tarefas `COMPLETED` para `PENDING` ou `IN_PROGRESS`.
* O dashboard deve exibir os contratos e projetos com seus status e oferecer controles para alterá-los.

---

## 3. Interface Gráfica WEB (Django Templates + Bootstrap 5)

A aplicação disponibiliza uma interface visual completa renderizada via Django Templates e estilizada com Bootstrap 5:

### 3.1 Página Inicial / Dashboard (`GET /`)
* **Rota:** `/contract` (ou `/?contract_id={uuid}`)
* **Rota:** `/` (ou `/?project_id={uuid}`)
* **Pré-requisito de inicialização:** Antes de acessar a rota, executar `python manage.py migrate`. A migration inicial `tasktrack.0001_initial` cria as tabelas `users`, `contracts`, `projects` e `tasks` consultadas pelo dashboard.
* **Recursos visuais:**
  * **Barra de Métricas:** Contadores em tempo real do total de Projetos, Tarefas Pendentes, Em Andamento e Concluídas.
  * **Filtro por Projeto:** Navegação rápida para filtrar as tarefas por projeto selecionado.
  * **Status dos Contratos:** Dividido em 3 colunas de status:
    * `PROSPECTING` (Prospecção): Cartões com título, descrição, proprietário, download do arquivo (quando existir) e botão *"Iniciar"* para transição direta para `IN_PROGRESS`.
    * `IN_PROGRESS` (Em Andamento): Contrato em Assinatura com botões *"Voltar"* (para `PROSPECTING`) e *"Concluir"* (para `SIGNED`).
    * `SIGNED` (Assinados): Contrato Aprovado — estado final, exibido com badge "Assinado" e sem botões de transição.
  * **Equipes dos Projetos:** Cada projeto deve exibir seus membros e oferecer controles para adicionar ou remover usuários, sem permitir duplicidades.
  * **Quadro Kanban de Tarefas:** Dividido em 3 colunas de status:
    * `PENDING` (Pendentes): Cartões com badge de prioridade, prazo, botão *"Iniciar"* para transição direta para `IN_PROGRESS`, botão *"Editar"* (lápis) e botão *"Excluir"* (lixeira).
    * `IN_PROGRESS` (Em Andamento): Cartões com botões *"Voltar"* (para `PENDING`) e *"Concluir"* (para `COMPLETED`), além de botões expandidos *"Editar"* e *"Excluir"*.
    * `COMPLETED` (Concluídas): Cartões com badge de conclusão, rastreamento de histórico completo, botões *"Editar"* (para reabertura ou alteração de metadata) e *"Excluir"* (para remover).
  * **Modais Interativos:**
    * Modal de Criação do Contrato (descrição expandida 400px min-height = ~20 linhas, redimensionável, suporta Markdown).
    * Modal de Criação de Projeto (descrição expandida 400px min-height = ~20 linhas, redimensionável, suporta Markdown).
    * Modal de Cadastro de Tarefa (descrição expandida 400px min-height = ~20 linhas, redimensionável, suporta Markdown, com seleção de prioridade, projeto, responsável e data de vencimento).
    * Modal de Edição de Tarefa (permite atualizar todos os campos incluindo descrição em Markdown com 400px min-height = ~20 linhas, redimensionável, github_url; pré-preenchido com dados da tarefa selecionada).
    * Modal de Cadastro de Usuários (para membros da equipe).

### 3.2 Ações e Formulários Web
* **Adicionar Contrato:** `POST /web/contracts` (Campos: `title`, `description`, `contract_file`, `owner_id`). Um contrato não recebe `contract_id`.
* **Criar Projeto:** `POST /web/projects` (Campos: `contract_id`, `title`, `description`, `owner_id`). O formulário deve exigir a seleção de um contrato existente; não é permitido criar projeto sem contrato.
* **Baixar Contrato:** `GET /download/<contract_file_path>` (Autenticado).
  * Rota: `/download/contracts/uuid_filename.pdf`
  * Headers: `Content-Disposition: attachment` (força download em vez de abrir no navegador)
  * Validação: Usuário deve estar autenticado
  * Resposta: Arquivo com mimetype `application/octet-stream`
  * Erro: 404 se arquivo não existir

* **Alterar status do contrato:** `POST /web/contracts/{contract_id}/status` (Campo: `status`, com valores `PROSPECTING`, `IN_PROGRESS` ou `SIGNED`). A interface web expõe apenas as transições válidas conforme a seção 2.3; transições inválidas são rejeitadas no domínio com erro `INVALID_STATUS_TRANSITION`.
* **Alterar status do projeto:** `POST /web/projects/{project_id}/status` (Campo: `status`). A operação sincroniza o status das tarefas do projeto conforme as regras da seção 2.3.
* **Gerenciar equipe do projeto:** `POST /web/projects/{project_id}/team` (Campos: `action` com `add` ou `remove`, e `user_id`).
* **Cadastrar Tarefa:** `POST /web/tasks` (Campos: `project_id`, `title`, `description`, `priority`, `assignee_id` [opcional], `due_date` [opcional, formato `YYYY-MM-DD`]). Modal pré-seleciona o projeto se filtrado. Campos opcionais podem ser deixados vazios e preenchidos posteriormente.
* **Alterar Status:** `POST /web/tasks/{task_id}/status` (Campo: `status`). Disponível via botão *"Iniciar"*, *"Voltar"* ou *"Concluir"* nos cartões.
* **Editar Tarefa:** `POST /web/tasks/{task_id}` (Campos opcionais: `title`, `description`, `priority`, `assignee_id`, `due_date` [formato `YYYY-MM-DD`], `github_url`). 
  * Modal pré-preenchido com dados da tarefa através de `data-*` attributes
  * JavaScript converte data do banco para formato `YYYY-MM-DD` para exibição no input type="date"
  * Suporta atualização parcial: apenas campos alterados são enviados
  * Campos deixados vazios não são atualizados
  * Campos vazios são convertidos para `None` (não atualizam o BD)
  * **Botão (lápis) disponível em TODAS as tarefas** (PENDING, IN_PROGRESS, COMPLETED)
  * **Permite reabertura**: Tarefas COMPLETED podem voltar para PENDING ou IN_PROGRESS
  * **Rastreamento de auditoria**: Cada alteração registrada em `task_history` com usuário, campo, valor anterior/novo, data/hora
  * Validação no cliente: título 3-100 caracteres, data deve ser futura, URL do GitHub (opcional)
  * Validação no servidor: valida assignee_id, formato github_url, transições de status
  * Mensagens de sucesso/erro via Django messages
* **Excluir Tarefa:** `POST /web/tasks/{task_id}/delete` (Sem campos). 
  * Botão (lixeira) disponível em **todas** as tarefas (PENDING, IN_PROGRESS, COMPLETED)
  * Exibe confirmação JavaScript: *"Tem certeza que deseja excluir esta tarefa?"*
  * Exclusão permanente e irreversível
  * Responde com redirecionamento para `/` e mensagem de sucesso
* **Cadastrar Usuário:** `POST /web/users` (Campos: `name`, `email`, `password`, `password_confirmation`, `role`).
* **Entrar:** `POST /login` (Campos: `username` com o e-mail e `password`).
* **Sair:** `GET /logout`.

---

## 4. Contratos de API REST (v1)


### 4.1 Adicionar Contrato
* **Endpoint:** `POST /api/v1/contracts`
* **Descrição:** Adicionar um novo contrato ao sistema.
* **Headers:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "title": "Contrato com Empresa XX",
  "description": "Contrato de projeto para migração da vitrine de produtos.",
  "contract_file": "filetest.pdf",
  "owner_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
}
```
* **Respostas:**
  * `201 Added`:
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Contrato do E-commerce com XX",
  "description": "Contrato do Projeto",
  "contract_file": "filetest.pdf",
  "status": "PROSPECTING",
  "owner_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "created_at": "2026-09-11T08:00:00Z"
}
```
  * `400 Bad Request`: Usuário proprietário não encontrado.
  * `422 Unprocessable Entity`: Dados de entrada inválidos.

### 4.2 Criar Projeto
* **Endpoint:** `POST /api/v1/projects`
* **Descrição:** Cria um novo projeto no sistema.
* **Headers:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "contract_id": "b14e7bd1-6c42-4e27-9e94-19f79a8061a9",
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
  "contract_id": "b14e7bd1-6c42-4e27-9e94-19f79a8061a9",
  "title": "Reformulação do E-commerce",
  "description": "Projeto focado na migração da vitrine de produtos.",
  "owner_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "created_at": "2026-09-12T08:00:00Z"
}
```
  * `400 Bad Request`: Usuário proprietário ou contrato não encontrado.
  * `422 Unprocessable Entity`: Dados de entrada inválidos.

---

### 4.3 Criar Tarefa
* **Endpoint:** `POST /api/v1/projects/{project_id}/tasks`
* **Descrição:** Cadastra uma nova tarefa vinculada a um projeto existente. Responsável e data de vencimento são opcionais e podem ser atribuídos posteriormente.
* **Path Parameter:** `project_id` (UUID)
* **Request Body:**
```json
{
  "title": "Implementar Gateway de Pagamento",
  "description": "Integrar API da Zoop para checkout transparente.",
  "priority": "HIGH",
  "assignee_id": null,
  "due_date": null  <!-- null ou formato: "YYYY-MM-DD" -->
}
```
* **Campos Opcionais:**
  * `assignee_id`: UUID do usuário responsável (null = sem responsável)
  * `due_date`: Data de vencimento em formato `YYYY-MM-DD` (null = sem data definida). Exemplo: `"2026-12-31"`
  * Se fornecidos, devem ser: assignee_id válido no BD, due_date no futuro

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
  "assignee_id": null,
  "due_date": null,
  "created_at": "2026-09-12T08:30:00Z",
  "updated_at": "2026-09-12T08:30:00Z"
}
```
  * `404 Not Found`: Projeto não encontrado.
  * `422 Unprocessable Entity`: Data retroativa (se fornecida) ou campos obrigatórios ausentes.

---

### 4.4 Atualizar Status da Tarefa
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

### 4.5 Editar Tarefa
* **Endpoint:** `PUT /api/v1/tasks/{task_id}` ou `PATCH /api/v1/tasks/{task_id}`
* **Descrição:** Atualiza os campos de uma tarefa existente.
* **Path Parameter:** `task_id` (UUID)
* **Request Body (todos os campos opcionais):**
```json
{
  "title": "Novo título da tarefa",
  "description": "Nova descrição.",
  "priority": "HIGH",
  "assignee_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "due_date": "2026-11-30"
}
```
* **Respostas:**
  * `200 OK`: Retorna o objeto completo da tarefa atualizada.
  * `404 Not Found`: Tarefa não encontrada.
  * `422 Unprocessable Entity`: Dados de entrada inválidos (ex: data retroativa, título muito curto).

---

### 4.6 Excluir Tarefa
* **Endpoint:** `DELETE /api/v1/tasks/{task_id}`
* **Descrição:** Remove uma tarefa do sistema de forma permanente.
* **Path Parameter:** `task_id` (UUID)
* **Respostas:**
  * `204 No Content`: Tarefa excluída com sucesso.
  * `404 Not Found`: Tarefa não encontrada.

---

## 5. Regras de Negócio e Casos de Borda

### 5.1 Regras de Negócio (RN)
* **RN-01 (Validação de Título):** O título da tarefa deve conter entre 3 e 100 caracteres e não pode ser composto apenas por espaços em branco.
* **RN-02 (Data de Vencimento Futura - Opcional):** A `due_date` é opcional na criação. Quando fornecida, deve obrigatoriamente ser posterior ao dia atual (só é aceito data futura, não o próprio dia). Pode ser atribuída posteriormente através da edição. Formato: `YYYY-MM-DD`.
* **RN-03 (Valores Permitidos de Enums):**
  * `status`: Apenas `PENDING`, `IN_PROGRESS`, `COMPLETED`.
  * `priority`: Apenas `LOW`, `MEDIUM`, `HIGH`.
* **RN-04 (Ciclo de Vida do Status - Com Auditoria):**
  * Transições permitidas (todas as combinações com rastreamento):
    - `PENDING` ➔ `IN_PROGRESS`
    - `PENDING` ➔ `COMPLETED`
    - `IN_PROGRESS` ➔ `COMPLETED`
    - `IN_PROGRESS` ➔ `PENDING`
    - `COMPLETED` ➔ `PENDING` (reabertura)
    - `COMPLETED` ➔ `IN_PROGRESS` (reabertura)
  * **Rastreamento de Auditoria**: Toda alteração (status, título, descrição, prioridade, responsável, data, github_url) é registrada na tabela `task_history` com:
    - `task_id`: UUID da tarefa alterada
    - `changed_by_id`: UUID do usuário que realizou a alteração
    - `field_name`: Nome do campo alterado
    - `old_value`: Valor anterior
    - `new_value`: Novo valor
    - `changed_at`: Data/hora da alteração (UTC)
  * Histórico completo permite rastrear quem, o quê, quando e por quê cada mudança foi feita
* **RN-05 (Atribuição de Responsável):** Se o `assignee_id` for informado, o sistema deve validar se o UUID existe na tabela `users`.
* **RN-06 (Rastreabilidade via GitHub):** O campo `github_url` vincula tarefas a referências externas no GitHub (issues, pull requests, etc). Formato: URL relativa (ex: `https://github.com/owner/repo/issues/123`). Campo opcional, máximo 255 caracteres.
* **RN-07 (Campos TEXT com Markdown):** Todos os campos de descrição (contratos, projetos, tarefas) aceitam formatação Markdown:
  * Armazenamento: Markdown puro (até 65KB por campo)
  * Suporte: **negrito**, *itálico*, `código`, títulos, listas, links
  * Renderização: Cliente responsável por renderizar Markdown em exibição (se necessário)
  * UI: Campos textarea expandidos com `min-height: 400px` (~20 linhas) | Redimensionáveis verticalmente | Dicas de formatação
  * Experiência: Editor tem ampla visão das descrições para documenta completamente (contratos, projetos, tarefas)

### 5.2 Casos de Borda (CB)
* **CB-01 (Projeto Inexistente):** Tentar criar uma tarefa enviando um `project_id` inexistente deve retornar `404 Not Found` com mensagem `"Projeto não encontrado"`.
* **CB-02 (Data no Passado):** Enviar `due_date = "2020-01-01"` deve ser interceptado pelo Pydantic e retornar `422 Unprocessable Entity` com mensagem `"A data de vencimento não pode ser no passado."`.
* **CB-03 (Reabertura Inválida):** Tentar alterar o status de `COMPLETED` para `IN_PROGRESS` deve retornar `400 Bad Request` com código de erro de domínio `"INVALID_STATUS_TRANSITION"`.
* **CB-04 (Usuário Inexistente):** Informar um `assignee_id` não cadastrado deve retornar `404 Not Found` com a mensagem `"Usuário atribuído não existe"`.
* **CB-05 (Edição Parcial):** Ao editar uma tarefa, enviar apenas `title` e `due_date` deve atualizar apenas esses campos, mantendo os demais inalterados.
* **CB-06 (Edição de Tarefa Inexistente):** Tentar editar uma tarefa com `task_id` inexistente deve retornar `404 Not Found` com mensagem `"Tarefa não encontrada"`.
* **CB-07 (Exclusão de Tarefa Inexistente):** Tentar excluir uma tarefa com `task_id` inexistente deve retornar `404 Not Found` com mensagem `"Tarefa não encontrada"`.

---

## 6. Critérios de Aceite (Exemplos para Testes Automatizados)

Estes cenários devem orientar a geração de testes automatizados com `pytest` e `httpx`.

### Cenário 1: Sucesso na Criação do Contrato
* **Dado** que existe um projeto cadastrado com `id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"`
* **Quando** for enviada uma requisição `POST` para `/api/v1/projects/f47ac10b-58cc-4372-a567-0e02b2c3d479/contracts` com o payload:
  ```json
  {
    "title": "Criar Contrato",
    "description": "Cobrir casos felizes e de erro.",
    "priority": "HIGH",
    "due_date": "2026-12-31T23:59:59Z"
  }
  ```
* **Então** o código de status HTTP retornado deve ser `201 Created`
* **E** o corpo da resposta deve conter o campo `id` em formato UUID


### Cenário 2: Sucesso na Criação de Tarefa
* **Dado** que existe um projeto cadastrado com `id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"`
* **Quando** for enviada uma requisição `POST` para `/api/v1/projects/f47ac10b-58cc-4372-a567-0e02b2c3d479/tasks` com o payload:
  ```json
  {
    "title": "Criar Testes de Integração",
    "description": "Cobrir casos felizes e de erro.",
    "priority": "HIGH",
    "due_date": "2026-12-31"
  }
  ```
* **Então** o código de status HTTP retornado deve ser `201 Created`
* **E** o corpo da resposta deve conter o campo `id` em formato UUID
* **E** o campo `status` deve ser inicializado automaticamente como `"PENDING"`.

### Cenário 3: Falha por Data Retroativa
* **Dado** que a data atual é `2026-09-12`
* **Quando** for enviada uma requisição `POST` com `due_date = "2025-01-01"`
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

### Cenário 4: Transição Inválida de Status
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


