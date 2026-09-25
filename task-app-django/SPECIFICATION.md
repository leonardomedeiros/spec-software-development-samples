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

-- Tabela de Requisitos
CREATE TABLE requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE, -- seção 2.6 e 2.8
    code VARCHAR(20) UNIQUE NOT NULL, -- código único, gerado automaticamente pelo sistema a partir de req_type (ex: 'RF-01', 'RNF-01'); não é informado pelo cliente
    title VARCHAR(150) NOT NULL,
    description TEXT,
    req_type VARCHAR(25) NOT NULL DEFAULT 'FUNCTIONAL', -- 'FUNCTIONAL', 'NON_FUNCTIONAL', 'BUSINESS_RULE', 'TECHNICAL_CONSTRAINT'
    priority VARCHAR(10) NOT NULL DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH'
    status VARCHAR(15) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'APPROVED', 'IMPLEMENTED', 'DEPRECATED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

  -- Vínculo N:N entre requisitos e tarefas
  CREATE TABLE requirement_task_links (
    requirement_id UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (requirement_id, task_id)
  );

-- Tabela de Atores do Sistema
CREATE TABLE actors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE, -- seção 2.7 e 2.8
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

  -- Vínculo N:N entre atores e requisitos
  CREATE TABLE actor_requirement_links (
    actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE CASCADE,
    requirement_id UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (actor_id, requirement_id)
  );
```

### 2.2 Relacionamentos
* **Contract -> Project:** 1 Contrato possui N Projetos (1:N). Ao excluir um Contrato, seus Projetos são excluídas em cascata (`CASCADE`).
* **Contrato:** é a entidade raiz do vínculo; não possui `contract_id` nem referencia outro contrato.
* **User -> Project:** 1 Usuário pode ser proprietário (*owner*) de N Projetos (1:N).
* **Project -> Task:** 1 Projeto possui N Tarefas (1:N). Ao excluir um Projeto, suas Tarefas são excluídas em cascata (`CASCADE`).
* **User -> Task:** 1 Usuário pode ser atribuído como responsável a N Tarefas (1:N).
* **Project -> Requirement:** 1 Projeto possui N Requisitos (1:N). Ao excluir um Projeto, seus Requisitos são excluídos em cascata (`CASCADE`) — ver seção 2.6.
* **Contract -> Actor:** 1 Contrato possui N Atores (1:N). Ao excluir um Contrato, seus Atores são excluídos em cascata (`CASCADE`) — ver seção 2.7.
* **Requirement <-> Task:** 1 Requisito pode ser vinculado a N Tarefas e 1 Tarefa pode atender a N Requisitos (N:N), por meio da tabela `requirement_task_links` (ver seção 2.6). Excluir um Requisito ou uma Tarefa remove os vínculos correspondentes em cascata, sem excluir a entidade do outro lado.
* **Actor <-> Requirement:** 1 Ator pode ser vinculado a N Requisitos e 1 Requisito pode estar vinculado a N Atores (N:N), por meio da tabela `actor_requirement_links` (ver seção 2.7). Excluir um Ator ou um Requisito remove os vínculos correspondentes em cascata, sem excluir a entidade do outro lado.

### 2.4 Equipes de Projetos

* Um projeto pode possuir vários membros e um usuário pode participar de vários projetos (N:N), por meio da tabela `project_memberships`.
* A combinação `project_id` + `user_id` é única; adicionar um membro já vinculado não cria duplicidade.
* Ao excluir um projeto ou usuário, seus vínculos de equipe são removidos em cascata.
* O proprietário do projeto continua sendo armazenado em `projects.owner_id`; membros da equipe são usuários adicionais autorizados a participar do projeto.

### 2.5 Autenticação e Funções de Usuário

* O acesso à interface web deve usar a autenticação nativa do Django (`django.contrib.auth`), com sessão, login por e-mail e senha e logout.
* O usuário de autenticação do Django deve ser criado com `username` igual ao e-mail; a senha deve ser armazenada somente pelo mecanismo de hash do Django.
* O perfil de domínio (`users`) deve manter a função do usuário. Os valores permitidos são `ADMIN`, `MEMBER`, `DEVELOPER`, `TEST`, `MANAGER` e `PRODUCT_OWNER`. Essa função determina quais Contratos/Projetos/Tarefas/Requisitos/Atores o usuário pode ver e alterar — ver seção 2.8.
* A sessão web (usuário Django autenticado) é resolvida para o perfil de domínio correspondente pelo e-mail (`users.email` = `username` do usuário Django); usada para aplicar as regras de visibilidade da seção 2.8.
* O cadastro de usuário deve exigir nome, e-mail, senha, confirmação de senha e função, criando o usuário Django e o perfil de domínio correspondente.
* O dashboard e as ações web devem exigir usuário autenticado; endpoints REST permanecem independentes da sessão web.
* Para inicializar uma base sem usuários, disponibilizar o comando:
  `python manage.py create_tasktrack_user --name "Nome" --email usuario@exemplo.com --password "senha-segura" --role MANAGER`.

### 2.6 Requisitos e Vínculo com Tarefas

* Todo Requisito pertence a exatamente um Projeto (`project_id`, obrigatório, FK para `projects`, `ON DELETE CASCADE`) — ver seção 2.8 para as regras de visibilidade derivadas dessa associação. Além disso, um Requisito (`code`, `title`, `description` em Markdown, `type`, `priority`, `status`) pode ser vinculado a uma ou mais Tarefas, e uma Tarefa pode atender a vários Requisitos (N:N), por meio da tabela `requirement_task_links`.
* O campo `code` **não é informado pelo cliente**: é gerado automaticamente pelo servidor no momento do cadastro, com base no `type` do requisito, seguindo o mesmo mecanismo de sequência atômica usado para o `display_id` de Tarefa e Projeto (seções 2.1/2.4). O prefixo depende do tipo — `FUNCTIONAL` → `RF-NN`, `NON_FUNCTIONAL` → `RNF-NN`, `BUSINESS_RULE` → `RN-NN`, `TECHNICAL_CONSTRAINT` → `RT-NN` —, com numeração sequencial própria por prefixo (ex.: `RF-01`, `RF-02`, `RNF-01`). Por ser gerado pelo servidor, `code` é sempre único e **não pode ser alterado** na edição do requisito (campo somente leitura).
* O `project_id` é exigido na criação (`POST /web/requirements` ou `POST /api/v1/requirements`) e pode ser alterado na edição; tentar informar um `project_id` inexistente é rejeitado com `404 Not Found`/`ProjectNotFoundError`.
* `type` aceita `FUNCTIONAL`, `NON_FUNCTIONAL`, `BUSINESS_RULE` ou `TECHNICAL_CONSTRAINT`. `priority` aceita `LOW`, `MEDIUM` ou `HIGH`.
* `status` é um campo próprio do requisito (não é calculado a partir das tarefas vinculadas, ao contrário do status do Projeto — ver seção 2.3), com transições: `DRAFT -> {APPROVED, DEPRECATED}`, `APPROVED -> {IMPLEMENTED, DRAFT, DEPRECATED}`, `IMPLEMENTED -> {APPROVED, DEPRECATED}`. `DEPRECATED` é um estado final e não pode retornar para outro status.
* A combinação `requirement_id` + `task_id` é única; vincular uma tarefa já vinculada não cria duplicidade. Ao excluir um requisito ou uma tarefa, os vínculos correspondentes são removidos em cascata.
* O vínculo com Tarefas pode ser feito de duas formas: (1) já no momento do cadastro do requisito, selecionando uma ou mais tarefas no modal de criação (`task_ids`, seção 3.2); ou (2) posteriormente, pela tabela de Requisitos (`POST /web/requirements/{requirement_id}/tasks`). Ambas usam o mesmo vínculo N:N e produzem o mesmo resultado.
* Os requisitos cadastrados podem ser exportados/refletidos no próprio `SPECIFICATION.md` (ver seção 7).

### 2.7 Atores do Sistema e Vínculo com Requisitos

* Um Ator (`name`, `description` em Markdown) é uma entidade independente do cadastro de Usuários (`users`) — representa um papel/persona de negócio que interage com o sistema (ex.: *Cliente*, *Administrador*, *Atendente*), sem estar necessariamente associado a uma conta de acesso.
* Todo Ator pertence a exatamente um Contrato (`contract_id`, obrigatório, FK para `contracts`, `ON DELETE CASCADE`) — ver seção 2.8 para as regras de visibilidade derivadas dessa associação. O `contract_id` é exigido na criação (`POST /web/actors`) e pode ser alterado na edição; tentar informar um `contract_id` inexistente é rejeitado com `ContractNotFoundError`.
* Um Ator pode ser vinculado a um ou mais Requisitos, e um Requisito pode estar vinculado a vários Atores (N:N), por meio da tabela `actor_requirement_links`, no mesmo padrão do vínculo Requisito↔Tarefa (seção 2.6).
* A combinação `actor_id` + `requirement_id` é única; vincular um ator já vinculado não cria duplicidade. Ao excluir um ator ou um requisito, os vínculos correspondentes são removidos em cascata.
* Assim como o vínculo com Tarefas (seção 2.6), o vínculo com Atores pode ser feito já no momento do cadastro do requisito, selecionando um ou mais atores no modal de criação (`actor_ids`, seção 3.2), ou posteriormente pela tabela de Requisitos.
* A gestão do vínculo após a criação (adicionar/remover) é centralizada na tabela de Requisitos do dashboard (`POST /web/requirements/{requirement_id}/actors`, seção 3.2), no mesmo padrão adotado para o vínculo com Tarefas — evitando duas interfaces divergentes para a mesma operação. A tabela de Atores exibe, de forma recíproca e somente leitura, os requisitos vinculados a cada ator.
* Os atores vinculados a cada requisito também são refletidos na seção 7 (Requisitos Rastreáveis) do `SPECIFICATION.md`, junto com as tarefas vinculadas.

### 2.8 Controle de Acesso e Visibilidade por Perfil

A visibilidade de Contratos, Projetos, Tarefas, Requisitos e Atores no dashboard (e a autorização das
ações de escrita sobre eles) depende do perfil (`role`) do usuário autenticado. As regras abaixo se
aplicam à interface web (`/`, `/web/...`); os endpoints REST (`/api/v1/...`) permanecem independentes
da sessão web (seção 2.5) e não aplicam este filtro.

#### 2.8.1 Regras por perfil

| Perfil | Projetos visíveis | Como navega |
|---|---|---|
| `ADMIN` | Todos os projetos do sistema. | Combo box de contrato (opcional) apenas filtra a visão; sem seleção, vê tudo. |
| `MEMBER` | Todos os projetos do contrato selecionado. | Combo box de contrato **obrigatório**: sem seleção, não vê nenhum projeto. |
| `DEVELOPER` | Apenas os projetos dos quais é `owner` ou membro da equipe (`project_memberships`). | Não possui combo box de contrato; a visão independe de qualquer contrato. |
| `TEST` | Idêntico a `DEVELOPER`. | Idêntico a `DEVELOPER`. |
| `MANAGER` | Idêntico a `DEVELOPER`. | Idêntico a `DEVELOPER`. |
| `PRODUCT_OWNER` | Idêntico a `DEVELOPER`. | Idêntico a `DEVELOPER`. |

A partir do conjunto de Projetos visíveis, os demais dados são derivados:
* **Tarefas e Requisitos:** visíveis apenas se pertencerem a um Projeto visível (`task.project_id` /
  `requirement.project_id` no conjunto visível — seção 2.6).
* **Atores e a tabela de Contratos:** visíveis apenas se pertencerem a um Contrato visível. Para
  `ADMIN`/`MEMBER`, o Contrato visível é o selecionado no combo box (ou todos, se `ADMIN` não
  selecionou nenhum). Para os demais perfis, são os contratos dos seus próprios Projetos visíveis
  (seção 2.7).
* O filtro por Projeto já existente (`?project_id=`, seção 3.1) só é aplicado se o projeto informado
  estiver dentro do conjunto visível; caso contrário, é ignorado silenciosamente e a listagem completa
  (dentro do que é visível) é exibida — isso evita que um usuário force a visualização de outro
  projeto manipulando a URL.

#### 2.8.2 Combo box de seleção de contrato (Painel de Gestão de Tarefas)

* Exibido apenas para `ADMIN` e `MEMBER` (`GET /?contract_id={uuid}`), no topo do dashboard.
* Lista **todos** os contratos do sistema, independentemente do que já está filtrado — é o ponto de
  entrada para "desbloquear" a visão de um contrato específico.
* Para `ADMIN`, selecionar um contrato apenas restringe a visão a ele (não é uma restrição de
  segurança, já que `ADMIN` já enxerga tudo por padrão). Para `MEMBER`, a seleção é o único jeito de
  ver projetos, atores e tarefas — sem seleção, o dashboard exibe um estado vazio.

#### 2.8.3 Aplicação em ações de escrita (defesa em profundidade)

A filtragem acima cobre a *visualização*; as ações que alteram dados (criar/editar/excluir Tarefa,
Requisito, Ator e Projeto, e vincular/desvincular Tarefa ou Ator a um Requisito) também validam, no
servidor, se o usuário tem acesso ao Projeto/Contrato do recurso-alvo — mesmo que o dashboard já
esconda o botão correspondente, o endpoint recusa a operação (mensagem de erro e redirecionamento,
sem erro 500) caso o `project_id`/`contract_id` informado (ou o Projeto/Contrato do recurso já
existente) não seja acessível ao usuário. `ADMIN` sempre tem acesso; `MEMBER` tem acesso amplo (pode
agir em qualquer contrato, dado que sua limitação é apenas de navegação); os demais perfis só têm
acesso a Projetos dos quais são `owner` ou membros da equipe, e a Contratos desses mesmos Projetos.

A criação/edição/exclusão de Contratos em si (`/web/contracts...`) **não** é restrita por perfil —
esta seção trata apenas da visibilidade e autorização em torno de Projetos, Tarefas, Requisitos e
Atores, conforme solicitado.

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
  * A alteração para `IN_PROGRESS` **não move nenhuma tarefa** — é um status calculado, então só é aceita se já existir ao menos uma tarefa `IN_PROGRESS`; caso contrário a operação é rejeitada com `INVALID_STATUS_TRANSITION` (o usuário deve iniciar uma tarefa individualmente pelo botão *"Iniciar"* de cada tarefa);
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
  * **Barra de Métricas:** Contadores em tempo real do total de Projetos, Tarefas Pendentes, Em Andamento e Concluídas (já refletindo a visibilidade do perfil — seção 2.8).
  * **Seletor de Contrato (`GET /?contract_id={uuid}`):** exibido apenas para `ADMIN` e `MEMBER` (seção 2.8.2). Combo box com todos os contratos do sistema; ao selecionar um, o dashboard passa a exibir os projetos, atores e tarefas daquele contrato. Para `MEMBER`, é obrigatório selecionar um contrato para ver qualquer projeto.
  * **Filtro por Projeto:** Navegação rápida para filtrar as tarefas por projeto selecionado, dentro do conjunto de projetos visível ao usuário (seção 2.8).
  * **Status dos Contratos:** Dividido em 3 colunas de status:
    * `PROSPECTING` (Prospecção): Cartões com título, descrição, proprietário, download do arquivo (quando existir) e botão *"Iniciar"* para transição direta para `IN_PROGRESS`.
    * `IN_PROGRESS` (Em Andamento): Contrato em Assinatura com botões *"Voltar"* (para `PROSPECTING`) e *"Concluir"* (para `SIGNED`).
    * `SIGNED` (Assinados): Contrato Aprovado — estado final, exibido com badge "Assinado" e sem botões de transição.
    * Todos os cartões, independente da coluna/status, exibem botões *"Editar"* (lápis) e *"Excluir"* (lixeira).
  * **Equipes dos Projetos:** Cada projeto deve exibir seus membros e oferecer controles para adicionar ou remover usuários, sem permitir duplicidades. A tabela de projetos também exibe botões *"Editar"* (lápis) e *"Excluir"* (lixeira) por projeto.
  * **Atores do Sistema (ver seções 2.7 e 2.8):** Tabela dedicada ao gerenciamento de atores (`contract_id`, `name`, `description`), independente do cadastro de Usuários, filtrada aos contratos visíveis ao usuário. Cada linha exibe ID, nome, descrição, os requisitos vinculados (badges, somente leitura — o vínculo é gerido pela tabela de Requisitos) e botões *"Editar"* (lápis) e *"Excluir"* (lixeira). O botão **"Novo Ator"** na barra de ferramentas abre o modal de cadastro, que exige a seleção de um Contrato (dentre os visíveis ao usuário).
  * **Rastreabilidade Ator ↔ Requisito (vínculo N:N, seção 2.7):** a tabela de Requisitos exibe, junto às tarefas vinculadas, os atores vinculados a cada requisito, com controles para vincular/desvincular (`POST /web/requirements/{requirement_id}/actors`, seção 3.2). A tabela de Atores mostra, de forma recíproca e somente leitura, quais requisitos cada ator está vinculado.
  * **Quadro Kanban de Tarefas:** Dividido em 3 colunas de status:
    * `PENDING` (Pendentes): Cartões com badge de prioridade, prazo, botão *"Iniciar"* para transição direta para `IN_PROGRESS`, botão *"Editar"* (lápis) e botão *"Excluir"* (lixeira).
    * `IN_PROGRESS` (Em Andamento): Cartões com botões *"Voltar"* (para `PENDING`) e *"Concluir"* (para `COMPLETED`), além de botões expandidos *"Editar"* e *"Excluir"*.
    * `COMPLETED` (Concluídas): Cartões com badge de conclusão, rastreamento de histórico completo, botões *"Editar"* (para reabertura ou alteração de metadata) e *"Excluir"* (para remover).
    * **Rastreabilidade Requisito ↔ Tarefa (vínculo N:N, seção 2.6):** todo cartão de tarefa que estiver vinculado a um ou mais requisitos exibe, abaixo do prazo/responsável, uma linha "Requisitos:" com um badge por código de requisito vinculado (ex.: `RF-01`, `RF-02`). Isso torna a rastreabilidade visível a partir de qualquer ponto do dashboard: a tabela de Requisitos mostra quais tarefas atendem a cada requisito (seção já existente), e o Kanban de Tarefas mostra, de forma recíproca e somente leitura, quais requisitos cada tarefa atende — sem exigir navegação até a tabela de requisitos. A gestão do vínculo (adicionar/remover) permanece centralizada na tabela de Requisitos (`POST /web/requirements/{requirement_id}/tasks`, seção 3.2), evitando duas interfaces divergentes para a mesma operação.
  * **Modais Interativos:**
    * Modal de Criação do Contrato (descrição expandida 400px min-height = ~20 linhas, redimensionável, suporta Markdown).
    * Modal de Edição de Contrato (título, descrição em Markdown e proprietário; pré-preenchido com dados do contrato selecionado; `contract_file` e `status` não são editáveis por este modal).
    * Modal de Criação de Projeto (descrição expandida 400px min-height = ~20 linhas, redimensionável, suporta Markdown).
    * Modal de Edição de Projeto (título, descrição em Markdown e proprietário; pré-preenchido com dados do projeto selecionado; `contract_id` não é editável).
    * Modal de Cadastro de Tarefa (descrição expandida 400px min-height = ~20 linhas, redimensionável, suporta Markdown, com seleção de prioridade, projeto, responsável e data de vencimento).
    * Modal de Edição de Tarefa (permite atualizar todos os campos incluindo descrição em Markdown com 400px min-height = ~20 linhas, redimensionável, github_url; pré-preenchido com dados da tarefa selecionada).
    * Modal de Cadastro de Usuários (para membros da equipe).
    * Modal de Cadastro de Requisito (exige a seleção de um Projeto, dentre os visíveis ao usuário; descrição em Markdown, com seleção múltipla de Tarefas e de Atores a vincular já na criação — ver seções 2.6/2.7/2.8; o campo `code` não é solicitado, é gerado automaticamente a partir do `type` escolhido).
    * Modal de Edição de Requisito (título, descrição, tipo e prioridade; `code` é exibido somente leitura, pois é imutável após o cadastro).
    * Modal de Cadastro de Ator (nome e descrição em Markdown).
    * Modal de Edição de Ator (pré-preenchido com dados do ator selecionado).

### 3.2 Ações e Formulários Web

> **Autorização (seção 2.8):** todas as ações abaixo sobre Projeto, Tarefa, Requisito e Ator (criar,
> editar, excluir, alterar status, gerenciar equipe/vínculos) validam no servidor se o usuário
> autenticado tem acesso ao Projeto/Contrato envolvido, mesmo que o botão correspondente já esteja
> oculto na interface para quem não tem acesso. Quando a validação falha, a resposta é um
> redirecionamento para `/` com mensagem de erro (`"Você não tem permissão para..."`), nunca um erro
> 500. As ações sobre Contrato (`/web/contracts...`) não são restritas por perfil.

* **Adicionar Contrato:** `POST /web/contracts` (Campos: `title`, `description`, `contract_file`, `owner_id`). Um contrato não recebe `contract_id`.
* **Criar Projeto:** `POST /web/projects` (Campos: `contract_id`, `title`, `description`, `owner_id`). O formulário deve exigir a seleção de um contrato existente; não é permitido criar projeto sem contrato.
* **Baixar Contrato:** `GET /download/<contract_file_path>` (Autenticado).
  * Rota: `/download/contracts/uuid_filename.pdf`
  * Headers: `Content-Disposition: attachment` (força download em vez de abrir no navegador)
  * Validação: Usuário deve estar autenticado
  * Resposta: Arquivo com mimetype `application/octet-stream`
  * Erro: 404 se arquivo não existir

* **Alterar status do contrato:** `POST /web/contracts/{contract_id}/status` (Campo: `status`, com valores `PROSPECTING`, `IN_PROGRESS` ou `SIGNED`). A interface web expõe apenas as transições válidas conforme a seção 2.3; transições inválidas são rejeitadas no domínio com erro `INVALID_STATUS_TRANSITION`.
* **Editar Contrato:** `POST /web/contracts/{contract_id}` (Campos opcionais: `title`, `description`, `owner_id` — atualização parcial, igual à edição de tarefa: campos deixados vazios não são alterados).
  * Botão (lápis) disponível em contratos de qualquer status (`PROSPECTING`, `IN_PROGRESS`, `SIGNED`)
  * Modal pré-preenchido com dados do contrato através de `data-*` attributes
  * `contract_file` e `status` não são editáveis por este formulário (arquivo é definido na criação; status é alterado pelo fluxo de transição da seção 3.2)
  * Validação no servidor: título não pode ser vazio, `owner_id` deve existir
* **Excluir Contrato:** `POST /web/contracts/{contract_id}/delete` (Sem campos).
  * Botão (lixeira) disponível em contratos de qualquer status
  * Exibe modal de confirmação alertando que **projetos e tarefas vinculados também serão excluídos** (exclusão em cascata via FK `ON DELETE CASCADE`: `projects.contract_id` → `contracts.id`, `tasks.project_id` → `projects.id`)
  * Exclusão permanente e irreversível
  * Responde com redirecionamento para `/` e mensagem de sucesso
* **Alterar status do projeto:** `POST /web/projects/{project_id}/status` (Campo: `status`). A operação sincroniza o status das tarefas do projeto conforme as regras da seção 2.3.
* **Gerenciar equipe do projeto:** `POST /web/projects/{project_id}/team` (Campos: `action` com `add` ou `remove`, e `user_id`).
* **Editar Projeto:** `POST /web/projects/{project_id}` (Campos opcionais: `title`, `description`, `owner_id` — atualização parcial, igual à edição de tarefa).
  * Botão (lápis) na tabela de "Status dos Projetos", disponível independente do status
  * Modal pré-preenchido com dados do projeto através de `data-*` attributes
  * `contract_id` não é editável (vínculo definido na criação do projeto)
  * Validação no servidor: título não pode ser vazio, `owner_id` deve existir
* **Excluir Projeto:** `POST /web/projects/{project_id}/delete` (Sem campos).
  * Botão (lixeira) na tabela de "Status dos Projetos"
  * Exibe modal de confirmação alertando que **as tarefas vinculadas também serão excluídas** (exclusão em cascata via FK `tasks.project_id` → `projects.id`)
  * Exclusão permanente e irreversível
  * Responde com redirecionamento para `/` e mensagem de sucesso
* **Cadastrar Tarefa:** `POST /web/tasks` (Campos: `project_id`, `title`, `description`, `priority`, `assignee_id` [opcional], `due_date` [opcional, formato `YYYY-MM-DD`]). Modal pré-seleciona o projeto se filtrado. Campos opcionais podem ser deixados vazios e preenchidos posteriormente.
* **Alterar Status:** `POST /web/tasks/{task_id}/status` (Campo: `status`). Disponível via botão *"Iniciar"*, *"Voltar"* ou *"Concluir"* nos cartões.
* **Editar Tarefa:** `POST /web/tasks/{task_id}` (Campos opcionais: `title`, `description`, `priority`, `assignee_id`, `due_date` [formato `YYYY-MM-DD`], `github_url`). 
  * Modal pré-preenchido com dados da tarefa através de `data-*` attributes
  * JavaScript converte data do banco para formato `YYYY-MM-DD` para exibição no input type="date"
  * Suporta atualização parcial: apenas campos alterados são enviados
  * Campos deixados vazios não são atualizados
  * Campos vazios são convertidos para `None` (não atualizam o BD)
  * `due_date` só é reenviado para validação/atualização se o valor no formulário for diferente da data já cadastrada na tarefa; se o campo permanecer igual (ex.: tarefa já vencida ou com vencimento hoje), ele é tratado como `None` (sem alteração) e não aciona a regra RN-02, evitando bloquear a edição de outros campos de tarefas com `due_date` no passado.
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
* **Cadastrar Requisito:** `POST /web/requirements` (Campos: `project_id` [obrigatório], `code`, `title`, `description`, `type`, `priority`, `task_ids` [opcional, lista de UUIDs de tarefas a vincular] e `actor_ids` [opcional, lista de UUIDs de atores a vincular]). A criação do requisito e os vínculos com tarefas/atores ocorrem em uma única transação: se algum `task_id`/`actor_id` informado não existir, nada é persistido (o requisito não é criado). Se o usuário não tiver acesso ao `project_id` informado (seção 2.8), a operação é recusada.
* **Editar Requisito:** `POST /web/requirements/{requirement_id}` (Campos opcionais: `title`, `description`, `type`, `priority` — atualização parcial, igual à edição de tarefa; `code` não é aceito, pois é imutável — ver RN-08).
* **Alterar status do Requisito:** `POST /web/requirements/{requirement_id}/status` (Campo: `status`, conforme transições da seção 2.6).
* **Vincular/Desvincular Tarefa ao Requisito:** `POST /web/requirements/{requirement_id}/tasks` (Campos: `action` com `add` ou `remove`, e `task_id`).
* **Vincular/Desvincular Ator ao Requisito:** `POST /web/requirements/{requirement_id}/actors` (Campos: `action` com `add` ou `remove`, e `actor_id`, conforme seção 2.7).
* **Excluir Requisito:** `POST /web/requirements/{requirement_id}/delete` (Sem campos).
* **Cadastrar Ator:** `POST /web/actors` (Campos: `contract_id` [obrigatório], `name`, `description`). Se o usuário não tiver acesso ao `contract_id` informado (seção 2.8), a operação é recusada.
* **Editar Ator:** `POST /web/actors/{actor_id}` (Campos opcionais: `name`, `description` — atualização parcial, igual à edição de requisito).
* **Excluir Ator:** `POST /web/actors/{actor_id}/delete` (Sem campos). Os vínculos com Requisitos são removidos em cascata (seção 2.7).
* **Exportar Requisitos para SPECIFICATION.md:** `POST /web/specification/export` (Sem campos). Regenera apenas o bloco gerado automaticamente da seção 7 (Requisitos Rastreáveis), preservando o restante do documento.

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

### 4.1a Editar Contrato
* **Endpoint:** `PUT /api/v1/contracts/{contract_id}` ou `PATCH /api/v1/contracts/{contract_id}`
* **Descrição:** Atualiza título, descrição e/ou proprietário de um contrato existente. `contract_file` e `status` não são alterados por este endpoint.
* **Path Parameter:** `contract_id` (UUID)
* **Request Body (todos os campos opcionais):**
```json
{
  "title": "Novo título do contrato",
  "description": "Nova descrição.",
  "owner_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
}
```
* **Respostas:**
  * `200 OK`: Retorna o objeto completo do contrato atualizado.
  * `404 Not Found`: Contrato não encontrado.
  * `422 Unprocessable Entity`: Dados de entrada inválidos (ex: título vazio).

### 4.1b Excluir Contrato
* **Endpoint:** `DELETE /api/v1/contracts/{contract_id}`
* **Descrição:** Remove um contrato do sistema de forma permanente. Exclui em cascata todos os projetos e tarefas vinculados (FK `ON DELETE CASCADE`).
* **Path Parameter:** `contract_id` (UUID)
* **Respostas:**
  * `204 No Content`: Contrato excluído com sucesso.
  * `404 Not Found`: Contrato não encontrado.

---

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

### 4.2a Editar Projeto
* **Endpoint:** `PUT /api/v1/projects/{project_id}` ou `PATCH /api/v1/projects/{project_id}`
* **Descrição:** Atualiza título, descrição e/ou proprietário de um projeto existente. `contract_id` não é alterado por este endpoint.
* **Path Parameter:** `project_id` (UUID)
* **Request Body (todos os campos opcionais):**
```json
{
  "title": "Novo título do projeto",
  "description": "Nova descrição.",
  "owner_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
}
```
* **Respostas:**
  * `200 OK`: Retorna o objeto completo do projeto atualizado.
  * `404 Not Found`: Projeto não encontrado.
  * `422 Unprocessable Entity`: Dados de entrada inválidos (ex: título vazio).

### 4.2b Excluir Projeto
* **Endpoint:** `DELETE /api/v1/projects/{project_id}`
* **Descrição:** Remove um projeto do sistema de forma permanente. Exclui em cascata todas as tarefas vinculadas (FK `ON DELETE CASCADE`).
* **Path Parameter:** `project_id` (UUID)
* **Respostas:**
  * `204 No Content`: Projeto excluído com sucesso.
  * `404 Not Found`: Projeto não encontrado.

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

### 4.7 Requisitos (Requirements)
* **Listar / Criar:** `GET /api/v1/requirements` (lista todos) e `POST /api/v1/requirements`
* **Request Body (criação):** o campo `code` **não é enviado pelo cliente** — é gerado automaticamente pelo servidor a partir de `type` (ver seção 2.6).
```json
{
  "project_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Autenticação de Usuários",
  "description": "O sistema deve permitir login via e-mail e senha.",
  "type": "FUNCTIONAL",
  "priority": "HIGH"
}
```
* **Respostas (criação):**
  * `201 Created`: Retorna o objeto completo do requisito criado (inclui `project_id` e o `code` gerado automaticamente, ex.: `"RF-01"`).
  * `400 Bad Request`: `project_id` inexistente.
  * `422 Unprocessable Entity`: Dados de entrada inválidos (ex.: `project_id` ausente).
* **Editar / Excluir:** `PUT`/`PATCH /api/v1/requirements/{requirement_id}` (campos opcionais, mesmo padrão da edição de tarefa; `code` não é aceito no corpo — é imutável) e `DELETE /api/v1/requirements/{requirement_id}`.
  * `200 OK` / `204 No Content` em caso de sucesso; `404 Not Found` se o requisito não existir.
* **Alterar Status:** `PATCH /api/v1/requirements/{requirement_id}/status` com `{"status": "APPROVED"}` (transições conforme seção 2.6).
  * `400 Bad Request` com `"INVALID_STATUS_TRANSITION"` se a transição não for permitida.
* **Vincular/Desvincular Tarefa:** `POST /api/v1/requirements/{requirement_id}/tasks` com `{"task_id": "...", "action": "add"}` (ou `"remove"`).
  * `200 OK`: Retorna `{"linked_task_ids": [...]}` com o estado atual do vínculo.
  * `404 Not Found`: Requisito ou tarefa não encontrados.

---

## 5. Regras de Negócio e Casos de Borda

### 5.1 Regras de Negócio (RN)
* **RN-01 (Validação de Título):** O título da tarefa deve conter entre 3 e 100 caracteres e não pode ser composto apenas por espaços em branco.
* **RN-02 (Data de Vencimento Futura - Opcional):** A `due_date` é opcional na criação. Quando fornecida (na criação, ou na edição com um valor diferente do já cadastrado), deve obrigatoriamente ser posterior ao dia atual (só é aceito data futura, não o próprio dia). Pode ser atribuída posteriormente através da edição. Formato: `YYYY-MM-DD`. Na edição, se o valor enviado for igual à `due_date` já existente na tarefa, ele é tratado como campo não alterado e a validação de data futura não é reaplicada — isso evita que a simples reabertura do modal de edição de uma tarefa com vencimento no passado impeça a atualização de outros campos.
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
* **RN-08 (Código Gerado Automaticamente):** O campo `code` de um Requisito não é informado pelo cliente; é gerado automaticamente pelo servidor na criação, a partir do `type` (prefixo `RF`/`RNF`/`RN`/`RT`) e de uma sequência numérica própria por prefixo (mesmo mecanismo de `display_id` de Tarefa/Projeto — seções 2.1/2.4), garantindo unicidade. O campo é imutável após o cadastro (não pode ser alterado na edição).
* **RN-09 (Ciclo de Vida do Status do Requisito):** Transições permitidas: `DRAFT ➔ APPROVED`, `DRAFT ➔ DEPRECATED`, `APPROVED ➔ IMPLEMENTED`, `APPROVED ➔ DRAFT`, `APPROVED ➔ DEPRECATED`, `IMPLEMENTED ➔ APPROVED`, `IMPLEMENTED ➔ DEPRECATED`. `DEPRECATED` é um estado final (não retorna a outro status). Ao contrário do status do Projeto, o status do Requisito **não** é calculado a partir das tarefas vinculadas.

### 5.2 Casos de Borda (CB)
* **CB-01 (Projeto Inexistente):** Tentar criar uma tarefa enviando um `project_id` inexistente deve retornar `404 Not Found` com mensagem `"Projeto não encontrado"`.
* **CB-02 (Data no Passado):** Enviar `due_date = "2020-01-01"` deve ser interceptado pelo Pydantic e retornar `422 Unprocessable Entity` com mensagem `"A data de vencimento não pode ser no passado."`.
* **CB-03 (Reabertura de Tarefa Concluída):** Alterar o status de uma tarefa `COMPLETED` para `PENDING` ou `IN_PROGRESS` é uma operação válida (reabertura, RN-04) e deve retornar `200 OK` com o novo status, não um erro.
* **CB-04 (Usuário Inexistente):** Informar um `assignee_id` não cadastrado deve retornar `404 Not Found` com a mensagem `"Usuário atribuído não existe"`.
* **CB-05 (Edição Parcial):** Ao editar uma tarefa, enviar apenas `title` e `due_date` deve atualizar apenas esses campos, mantendo os demais inalterados.
* **CB-06 (Edição de Tarefa Inexistente):** Tentar editar uma tarefa com `task_id` inexistente deve retornar `404 Not Found` com mensagem `"Tarefa não encontrada"`.
* **CB-07 (Exclusão de Tarefa Inexistente):** Tentar excluir uma tarefa com `task_id` inexistente deve retornar `404 Not Found` com mensagem `"Tarefa não encontrada"`.
* **CB-08 (Edição de Tarefa com Vencimento já Vencido):** Editar via web (`POST /web/tasks/{task_id}`) qualquer campo (ex.: `title`) de uma tarefa cuja `due_date` já é hoje ou passada, reenviando essa mesma `due_date` inalterada (comportamento do formulário, que pré-preenche o campo), deve ser aceito normalmente (`302` redirect + mensagem de sucesso), sem disparar o erro de RN-02, pois o valor não mudou.
* **CB-09 (Código de Requisito Gerado pelo Servidor):** Um `code` enviado pelo cliente na criação ou edição de um Requisito é ignorado; o valor persistido é sempre o gerado automaticamente pelo servidor (RN-08), portanto colisões de código não podem ocorrer via API/formulário.
* **CB-10 (Vínculo com Requisito ou Tarefa Inexistente):** Tentar vincular/desvincular uma tarefa a um `requirement_id` inexistente, ou uma tarefa com `task_id` inexistente, deve retornar `404 Not Found`.
* **CB-11 (Edição/Exclusão de Contrato Inexistente):** Tentar editar (`PUT`/`PATCH`/`POST /web/contracts/{id}`) ou excluir (`DELETE`/`POST /web/contracts/{id}/delete`) um contrato com `contract_id` inexistente deve retornar `404 Not Found` (API) ou redirecionar com mensagem de erro (web), sem erro 500.
* **CB-12 (Edição/Exclusão de Projeto Inexistente):** Tentar editar ou excluir um projeto com `project_id` inexistente deve retornar `404 Not Found` (API) ou redirecionar com mensagem de erro (web), sem erro 500.
* **CB-13 (Exclusão em Cascata do Contrato):** Excluir um contrato remove automaticamente (via FK `ON DELETE CASCADE`) todos os projetos vinculados a ele e, transitivamente, todas as tarefas desses projetos.
* **CB-14 (Exclusão em Cascata do Projeto):** Excluir um projeto remove automaticamente (via FK `ON DELETE CASCADE`) todas as tarefas vinculadas a ele, sem afetar o contrato ao qual o projeto pertence.

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

### Cenário 4: Reabertura de Tarefa Concluída
* **Dado** uma tarefa salva no banco com status `COMPLETED`
* **Quando** for enviada uma requisição `PATCH` para `/api/v1/tasks/{task_id}/status` com `{"status": "IN_PROGRESS"}`
* **Então** o status HTTP deve ser `200 OK` (reabertura permitida, RN-04)
* **E** o corpo da resposta deve conter `"status": "IN_PROGRESS"`

---

## 7. Requisitos Rastreáveis (Requirements)

Esta seção mantém a rastreabilidade entre os **Requisitos** cadastrados (ver seção 2.6) e as **Tarefas**
que os implementam, bem como os **Atores** (ver seção 2.7) que os requisitam ou utilizam. Cada Requisito
tem um código único (`code`), título, descrição em Markdown, tipo
(`FUNCTIONAL`/`NON_FUNCTIONAL`/`BUSINESS_RULE`/`TECHNICAL_CONSTRAINT`), prioridade (`LOW`/`MEDIUM`/`HIGH`)
e um status próprio (`DRAFT`/`APPROVED`/`IMPLEMENTED`/`DEPRECATED`), e pode estar vinculado a uma ou mais
tarefas e a um ou mais atores.

O bloco abaixo, delimitado pelos marcadores `REQUISITOS:START`/`REQUISITOS:END`, é **gerado
automaticamente** — não deve ser editado manualmente. Para regenerá-lo a partir dos dados atuais:
* Pelo dashboard: clique em **"Exportar SPECIFICATION.md"**.
* Pela linha de comando: `python manage.py export_specification`.

Qualquer uma das duas opções substitui apenas o conteúdo entre os marcadores, preservando o restante
deste documento.

<!-- REQUISITOS:START -->
_Nenhum requisito cadastrado ainda. Use o dashboard ou `export_specification` para gerar esta seção._
<!-- REQUISITOS:END -->

