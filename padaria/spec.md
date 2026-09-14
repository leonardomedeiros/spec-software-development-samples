# Arquivo de Especificação: spec.md (Sistema de Gestão de Padaria)

## 0. Preparação do Projeto

Este arquivo deve ser executado a partir da raiz do diretório `padaria`.

Se não hovuer o ambiente virtual padaria-venv, crie-o e ative-o.

Se o Django ainda não estiver instalado, instale-o antes:

```bash
python -m pip install "Django>=5,<6"
```

Antes de implementar qualquer funcionalidade, verifique se o projeto Django já existe. Se `manage.py` não existir, crie a estrutura inicial nesta pasta:

```bash
python -m django startproject config .
python manage.py startapp core
```



O app `core` deve ser adicionado a `INSTALLED_APPS` em `config/settings.py`. A implementação inicial deve criar e alterar os seguintes arquivos:

- `core/models.py`: entidades e validações do domínio;
- `core/forms.py`: formulários e widgets Bootstrap 5;
- `core/admin.py`: registros e configurações do Django Admin;
- `core/tests.py`: testes automatizados.

Não recrie o projeto, o app ou arquivos existentes. Se essa estrutura já estiver presente, continue a implementação nela. Depois da criação ou alteração dos modelos, execute:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
```

## 1. Visão Geral do Módulo
O objetivo deste módulo é gerenciar o catálogo de produtos, controle de fornadas/lotes de produção e vendas de balcão (PDV rápido) de uma padaria. O sistema deve permitir que atendentes registrem vendas por unidade ou peso (kg), controlem a saída de estoque em tempo real e visualizem quais produtos estão saindo quentinhos da produção.

---

## 2. Modelagem de Dados (Entidades)

### Categoria (`Categoria`)
- `id`: PrimaryKey (Auto)
- `nome`: CharField(max_length=50, unique=True)
- `descricao`: TextField(blank=True, null=True)

### Produto (`Produto`)
- `id`: PrimaryKey (Auto)
- `categoria`: ForeignKey(Categoria, on_delete=PROTECT)
- `nome`: CharField(max_length=100)
- `preco_unitario`: DecimalField(max_digits=8, decimal_places=2)
- `unidade_medida`: CharField(max_length=2, choices=[('UN', 'Unidade'), ('KG', 'Quilograma')])
- `estoque_atual`: DecimalField(max_digits=8, decimal_places=3, default=0.000)
- `is_active`: BooleanField(default=True)

### Lote de Produção (`LoteProducao`)
- `id`: PrimaryKey (Auto)
- `produto`: ForeignKey(Produto, on_delete=CASCADE)
- `quantidade`: DecimalField(max_digits=8, decimal_places=3)
- `data_hora_saida`: DateTimeField()
- `status`: CharField(max_length=20, choices=[('EM_PRODUCAO', 'Em Produção'), ('PRONTO', 'Pronto / Na Estufa'), ('ESGOTADO', 'Esgotado')], default='EM_PRODUCAO')

### Venda (`Venda`)
- `id`: PrimaryKey (Auto)
- `data_hora`: DateTimeField(auto_now_add=True)
- `atendente`: ForeignKey(User, on_delete=PROTECT)
- `valor_total`: DecimalField(max_digits=10, decimal_places=2, default=0.00)
- `status`: CharField(max_length=20, choices=[('EM_ABERTO', 'Em Aberto'), ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada')], default='EM_ABERTO')

### Item da Venda (`ItemVenda`)
- `id`: PrimaryKey (Auto)
- `venda`: ForeignKey(Venda, on_delete=CASCADE, related_name='itens')
- `produto`: ForeignKey(Produto, on_delete=PROTECT)
- `quantidade`: DecimalField(max_digits=8, decimal_places=3) # Suporta ex: 0.350 kg ou 5.000 un
- `preco_unitario_aplicado`: DecimalField(max_digits=8, decimal_places=2) # Congela o preço no momento da venda
- `subtotal`: DecimalField(max_digits=10, decimal_places=2)

---

## 3. Regras de Negócio & Casos de Borda

### Regras de Negócio (RN)
- **RN01 (Unidade de Medida):** Produtos com `unidade_medida='UN'` só podem aceitar números inteiros no campo `quantidade` dos itens da venda. Produtos `'KG'` aceitam até 3 casas decimais.
- **RN02 (Histórico de Preço):** O campo `preco_unitario_aplicado` em `ItemVenda` deve armazenar o valor exato do `Produto.preco_unitario` no instante em que o item é inserido, protegendo o histórico caso o preço do produto mude no futuro.
- **RN03 (Atualização do Estoque por Lote):** Quando um `LoteProducao` altera seu status para `'PRONTO'`, o sistema deve somar automaticamente a `quantidade` do lote ao `estoque_atual` do `Produto` correspondente.
- **RN04 (Baixa de Estoque):** Ao finalizar uma `Venda` (status alterado para `'CONCLUIDA'`), o estoque de cada produto associado aos itens da venda deve ser deduzido.
- **RN05 (Estorno de Estoque):** Se uma venda com status `'CONCLUIDA'` for alterada para `'CANCELADA'`, o estoque de todos os seus itens deve ser estornado (recomposto).

### Casos de Borda
- **CB01 (Estoque Insuficiente):** Impedir a inclusão ou finalização de venda de um item cuja `quantidade` seja maior do que o `estoque_atual` disponível. Retornar erro de validação no formulário.
- **CB02 (Produto Inativo):** Produtos com `is_active=False` não podem aparecer na listagem de venda do balcão e nem permitir abertura de novos lotes de produção.
- **CB03 (Venda Vazia):** Uma venda não pode ser finalizada se não possuir ao menos um `ItemVenda` cadastrado.

---

## 4. Contratos de Views e URLs

| URL | Método | View Class/Function | Descrição | Redirecionamento (Sucesso) |
|---|---|---|---|---|
| `/produtos/` | `GET` | `ProductListView` | Lista produtos e seus estoques atuais | - |
| `/produtos/novo/` | `GET`, `POST` | `ProductCreateView` | Cadastro de novos produtos | `/produtos/` |
| `/lotes/` | `GET` | `BatchListView` | Painel de controle de fornadas / estufa | - |
| `/lotes/novo/` | `GET`, `POST` | `BatchCreateView` | Registrar nova fornada | `/lotes/` |
| `/pdv/` | `GET`, `POST` | `SaleCreateView` | Abre uma nova venda no balcão | `/pdv/<id>/` |
| `/pdv/<int:pk>/` | `GET` | `SaleDetailView` | Tela do caixa com os itens da venda | - |
| `/pdv/<int:pk>/adicionar/` | `POST` | `SaleAddItemView` | Adiciona item à venda em aberto | `/pdv/<int:pk>/` |
| `/pdv/<int:pk>/finalizar/` | `POST` | `SaleFinalizeView` | Baixa estoque e encerra a venda | `/pdv/` |
| `/pdv/<int:pk>/cancelar/` | `POST` | `SaleCancelView` | Cancela venda e estorna estoque | `/pdv/` |

---

## 5. Requisitos de UI/Bootstrap

- **Layout Geral:** Herança do `base.html` com container responsivo e Navbar fixa contendo links para "PDV / Caixa", "Fornadas", "Produtos" e "Relatórios".
- **Tela de PDV / Caixa (`SaleDetailView`):**
  - Grid responsivo em 2 colunas: `col-md-7` para busca e seleção de produtos (Cards) e `col-md-5` para o resumo do cupom da venda (Tabela).
  - Componente `input-group` do Bootstrap para buscar produtos e definir a quantidade.
  - Exibição de valor total da venda em destaque utilizando a classe `display-6` ou `badge bg-success`.
- **Painel de Fornadas (`BatchListView`):**
  - Exibição dos lotes no formato de Cards (`card`).
  - Uso de Badges coloridas conforme o status: `bg-warning` (Em Produção), `bg-success` (Pronto / Saindo Quentinho), `bg-secondary` (Esgotado).
- **Formulários:**
  - Todos os inputs com a classe `form-control` e `form-select`.
  - Exibição de erros de validação em linha com a div `invalid-feedback` ativada.
- **Mensagens do Sistema:**
  - Inclusão do partial `_messages.html` para exibir notificações do `django.contrib.messages` usando alertas do Bootstrap (`alert-success`, `alert-danger`, `alert-warning`) com botão de fechar `btn-close`.# Arquivo de Especificação: spec.md (Sistema de Gestão de Padaria)

## 1. Visão Geral do Módulo
O objetivo deste módulo é gerenciar o catálogo de produtos, controle de fornadas/lotes de produção e vendas de balcão (PDV rápido) de uma padaria. O sistema deve permitir que atendentes registrem vendas por unidade ou peso (kg), controlem a saída de estoque em tempo real e visualizem quais produtos estão saindo quentinhos da produção.

---

## 2. Modelagem de Dados (Entidades)

### Categoria (`Categoria`)
- `id`: PrimaryKey (Auto)
- `nome`: CharField(max_length=50, unique=True)
- `descricao`: TextField(blank=True, null=True)

### Produto (`Produto`)
- `id`: PrimaryKey (Auto)
- `categoria`: ForeignKey(Categoria, on_delete=PROTECT)
- `nome`: CharField(max_length=100)
- `preco_unitario`: DecimalField(max_digits=8, decimal_places=2)
- `unidade_medida`: CharField(max_length=2, choices=[('UN', 'Unidade'), ('KG', 'Quilograma')])
- `estoque_atual`: DecimalField(max_digits=8, decimal_places=3, default=0.000)
- `is_active`: BooleanField(default=True)

### Lote de Produção (`LoteProducao`)
- `id`: PrimaryKey (Auto)
- `produto`: ForeignKey(Produto, on_delete=CASCADE)
- `quantidade`: DecimalField(max_digits=8, decimal_places=3)
- `data_hora_saida`: DateTimeField()
- `status`: CharField(max_length=20, choices=[('EM_PRODUCAO', 'Em Produção'), ('PRONTO', 'Pronto / Na Estufa'), ('ESGOTADO', 'Esgotado')], default='EM_PRODUCAO')

### Venda (`Venda`)
- `id`: PrimaryKey (Auto)
- `data_hora`: DateTimeField(auto_now_add=True)
- `atendente`: ForeignKey(User, on_delete=PROTECT)
- `valor_total`: DecimalField(max_digits=10, decimal_places=2, default=0.00)
- `status`: CharField(max_length=20, choices=[('EM_ABERTO', 'Em Aberto'), ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada')], default='EM_ABERTO')

### Item da Venda (`ItemVenda`)
- `id`: PrimaryKey (Auto)
- `venda`: ForeignKey(Venda, on_delete=CASCADE, related_name='itens')
- `produto`: ForeignKey(Produto, on_delete=PROTECT)
- `quantidade`: DecimalField(max_digits=8, decimal_places=3) # Suporta ex: 0.350 kg ou 5.000 un
- `preco_unitario_aplicado`: DecimalField(max_digits=8, decimal_places=2) # Congela o preço no momento da venda
- `subtotal`: DecimalField(max_digits=10, decimal_places=2)

---

## 3. Regras de Negócio & Casos de Borda

### Regras de Negócio (RN)
- **RN01 (Unidade de Medida):** Produtos com `unidade_medida='UN'` só podem aceitar números inteiros no campo `quantidade` dos itens da venda. Produtos `'KG'` aceitam até 3 casas decimais.
- **RN02 (Histórico de Preço):** O campo `preco_unitario_aplicado` em `ItemVenda` deve armazenar o valor exato do `Produto.preco_unitario` no instante em que o item é inserido, protegendo o histórico caso o preço do produto mude no futuro.
- **RN03 (Atualização do Estoque por Lote):** Quando um `LoteProducao` altera seu status para `'PRONTO'`, o sistema deve somar automaticamente a `quantidade` do lote ao `estoque_atual` do `Produto` correspondente.
- **RN04 (Baixa de Estoque):** Ao finalizar uma `Venda` (status alterado para `'CONCLUIDA'`), o estoque de cada produto associado aos itens da venda deve ser deduzido.
- **RN05 (Estorno de Estoque):** Se uma venda com status `'CONCLUIDA'` for alterada para `'CANCELADA'`, o estoque de todos os seus itens deve ser estornado (recomposto).

### Casos de Borda
- **CB01 (Estoque Insuficiente):** Impedir a inclusão ou finalização de venda de um item cuja `quantidade` seja maior do que o `estoque_atual` disponível. Retornar erro de validação no formulário.
- **CB02 (Produto Inativo):** Produtos com `is_active=False` não podem aparecer na listagem de venda do balcão e nem permitir abertura de novos lotes de produção.
- **CB03 (Venda Vazia):** Uma venda não pode ser finalizada se não possuir ao menos um `ItemVenda` cadastrado.

---

## 4. Contratos de Views e URLs

| URL | Método | View Class/Function | Descrição | Redirecionamento (Sucesso) |
|---|---|---|---|---|
| `/produtos/` | `GET` | `ProductListView` | Lista produtos e seus estoques atuais | - |
| `/produtos/novo/` | `GET`, `POST` | `ProductCreateView` | Cadastro de novos produtos | `/produtos/` |
| `/lotes/` | `GET` | `BatchListView` | Painel de controle de fornadas / estufa | - |
| `/lotes/novo/` | `GET`, `POST` | `BatchCreateView` | Registrar nova fornada | `/lotes/` |
| `/pdv/` | `GET`, `POST` | `SaleCreateView` | Abre uma nova venda no balcão | `/pdv/<id>/` |
| `/pdv/<int:pk>/` | `GET` | `SaleDetailView` | Tela do caixa com os itens da venda | - |
| `/pdv/<int:pk>/adicionar/` | `POST` | `SaleAddItemView` | Adiciona item à venda em aberto | `/pdv/<int:pk>/` |
| `/pdv/<int:pk>/finalizar/` | `POST` | `SaleFinalizeView` | Baixa estoque e encerra a venda | `/pdv/` |
| `/pdv/<int:pk>/cancelar/` | `POST` | `SaleCancelView` | Cancela venda e estorna estoque | `/pdv/` |

---

## 5. Requisitos de UI/Bootstrap

- **Layout Geral:** Herança do `base.html` com container responsivo e Navbar fixa contendo links para "PDV / Caixa", "Fornadas", "Produtos" e "Relatórios".
- **Tela de PDV / Caixa (`SaleDetailView`):**
  - Grid responsivo em 2 colunas: `col-md-7` para busca e seleção de produtos (Cards) e `col-md-5` para o resumo do cupom da venda (Tabela).
  - Componente `input-group` do Bootstrap para buscar produtos e definir a quantidade.
  - Exibição de valor total da venda em destaque utilizando a classe `display-6` ou `badge bg-success`.
- **Painel de Fornadas (`BatchListView`):**
  - Exibição dos lotes no formato de Cards (`card`).
  - Uso de Badges coloridas conforme o status: `bg-warning` (Em Produção), `bg-success` (Pronto / Saindo Quentinho), `bg-secondary` (Esgotado).
- **Formulários:**
  - Todos os inputs com a classe `form-control` e `form-select`.
  - Exibição de erros de validação em linha com a div `invalid-feedback` ativada.
- **Mensagens do Sistema:**
  - Inclusão do partial `_messages.html` para exibir notificações do `django.contrib.messages` usando alertas do Bootstrap (`alert-success`, `alert-danger`, `alert-warning`) com botão de fechar `btn-close`.