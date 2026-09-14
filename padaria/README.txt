Para gerar o código do sistema de padaria a partir do arquivo spec.md, utilize a abordagem por fases em uma IDE assistida por IA (como Cursor, Windsurf ou Continue.dev).

1. Preparação do Ambiente

    Salve o texto da especificação em um arquivo chamado spec.md na raiz do seu projeto Django.

    Certifique-se de que as regras mestre (System Prompt / .cursorrules) do Django 5 e Bootstrap 5 estejam configuradas na sua IDE.


2. Prompts Sequenciais para o Chat da IDE

### Execução com OpenCode local

Abra o terminal integrado do VS Code e entre na pasta correta antes de iniciar o OpenCode:

```powershell
Set-Location D:\git\spec-software-development-samples\padaria
opencode --agent build --auto
```

Use o agente `build`. O agente `plan` pode apenas analisar a especificação e propor uma atividade, sem editar arquivos ou executar comandos. A opção `--auto` aprova automaticamente as permissões de edição e execução já permitidas pelo projeto.

Se preferir executar uma solicitação diretamente, sem usar a interface interativa:

```powershell
Set-Location D:\git\spec-software-development-samples\padaria
opencode run --agent build --auto "Leia integralmente spec.md. Se manage.py não existir, prepare o projeto Django conforme a seção 0. Depois crie o app core, adicione-o em INSTALLED_APPS e implemente a Fase 1 em core/models.py, core/forms.py e core/admin.py. Faça as alterações nos arquivos, não apenas descreva uma solução. Execute python manage.py check e informe o resultado."
```

Antes de executar, confirme que o prompt do terminal mostra `D:\git\spec-software-development-samples\padaria`. Se o OpenCode apenas descrever a solução, interrompa a sessão e reinicie com `--agent build`; não continue no agente `plan`.

    Leia integralmente @spec.md e siga também as instruções do projeto.

    Verifique se manage.py existe. Se não existir, crie o projeto Django conforme a seção 0 de spec.md. Depois crie o app core, adicione-o em INSTALLED_APPS e implemente a fase solicitada.

    Não apenas explique. Faça as alterações no workspace e execute:
    python manage.py check


Fase 1 — Backend Base (models.py, forms.py, admin.py)

    Leia e siga integralmente @spec.md. Primeiro prepare o projeto Django conforme a seção 0, caso manage.py ainda não exista. Depois implemente a fase inicial criando core/models.py, core/forms.py e core/admin.py. Não apenas explique: execute as alterações no workspace e valide com python manage.py check.

Ação no terminal após esta etapa:
Bash

python manage.py makemigrations
python manage.py migrate

Fase 2 — Testes e Lógica de Negócio (tests.py, views.py, urls.py)

    @spec.md Com base nas Regras de Negócio (RN01 a RN05), Casos de Borda (CB01 a CB03) e contratos de URLs da seção 3 e 4, crie a suíte completa de testes automatizados em tests.py. Em seguida, implemente as views em views.py e configure o urls.py de forma que 100% dos testes passem.

Ação no terminal após esta etapa:
Bash

python manage.py test

(Não avance até que todos os testes passem com sucesso)

Fase 3 — Interfaces e Templates (base.html e Telas)

    @spec.md Com base na seção 5 da especificação, crie a estrutura de templates HTML dentro da pasta templates/. Crie o base.html com a Navbar fixa e o partial _messages.html para os alertas. Em seguida, crie os templates das views (em especial o PDV em 2 colunas com suporte aos cards de produtos e tabela de itens).

3. Validação Final
Inicie o servidor local para validar o resultado no navegador:
Bash

python manage.py runserver

Teste o fluxo completo: cadastrar um produto, simular uma fornada de pão de queijo no painel de lotes e realizar uma venda de balcão no PDV para checar a baixa do estoque e as mensagens de confirmação.