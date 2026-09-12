# ESPECIFICAÇÃO DE SOFTWARE: [Nome do Projeto]

## 1. Visão Geral
- **Objetivo:** [Descreva em 2 a 3 frases o problema que o software resolve]
- **Atores:** [Ex: Usuário Comum, Administrador]

## 2. Modelo de Dados (Django ORM)
### Entidade: `Tarefa`
- `titulo`: CharField (max_length=200, obrigatório)
- `descricao`: TextField (opcional)
- `concluida`: BooleanField (default=False)
- `data_criacao`: DateTimeField (auto_now_add=True)
- `usuario`: ForeignKey -> User (on_delete=CASCADE)

**Relacionamentos e Restrições:**
- Um usuário pode ter várias tarefas.
- O título da tarefa deve ser único por usuário.

## 3. Regras de Negócio e Casos de Teste (BDD / Gherkin)
- **Cenário 1:** Criar tarefa com sucesso
  - **Dado** que o usuário está autenticado
  - **Quando** ele enviar o formulário com o título "Estudar Django"
  - **Então** a tarefa deve ser salva no banco e retornada na lista via HTMX sem recarregar a página.

- **Cenário 2:** Validação de título duplicado
  - **Dado** que o usuário já possui uma tarefa chamada "Estudar Django"
  - **Quando** tentar criar outra tarefa com o mesmo título
  - **Então** o sistema deve retornar o erro "Tarefa já existente" com status HTTP 400.

## 4. Rotas e Comportamento HTMX
| Rota | Método | View | Comportamento HTMX |
| :--- | :--- | :--- | :--- |
| `/tarefas/` | GET | `tarefa_list` | Retorna o template completo `tarefas.html`. |
| `/tarefas/criar/` | POST | `tarefa_create` | Retorna apenas o partial `_tarefa_item.html` para ser anexado em `#lista-tarefas`. |
| `/tarefas/<id>/concluir/` | POST | `tarefa_toggle` | Atualiza o estado e retorna o elemento atualizado. |

## 5. Interface do Usuário (Design & Bootstrap)
- **Tela Principal:** Layout de coluna única com formulário no topo e lista abaixo.
- **Estados Visuais:**
  - *Lista vazia:* Exibir mensagem "Nenhuma tarefa cadastrada".
  - *Erro de validação:* Borda vermelha no input e mensagem logo abaixo.