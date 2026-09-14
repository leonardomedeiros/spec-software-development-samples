# AGENTS.md

## 1. Objetivo e fonte de verdade

Este diretório contém o sistema de gestão de uma padaria. O sistema deve gerenciar:

- catálogo de categorias e produtos;
- fornadas/lotes de produção e estoque disponível;
- vendas rápidas de balcão (PDV), por unidade ou por quilograma.

`spec.md` é a fonte de verdade para requisitos, nomes de entidades, regras de negócio, URLs e requisitos de interface. Antes de implementar ou alterar qualquer comportamento, consulte o trecho correspondente da especificação e preserve seus contratos.

## 2. Stack e convenções

- Python 3.11+;
- Django 5.x;
- Django ORM e migrations para persistência;
- Django templates com Bootstrap 5 para a interface;
- Django Forms para entrada e validação de dados;
- testes automatizados com `django.test`.

Não introduza Pydantic, uma API REST ou outro framework sem requisito explícito. Use as convenções e os recursos nativos do Django já adotados pelo projeto.

## 3. Modelo de domínio

Implemente as entidades definidas em `spec.md` com os campos, limites, escolhas e relacionamentos especificados:

- `Categoria`: nome único, descrição opcional;
- `Produto`: categoria protegida, preço, unidade (`UN` ou `KG`), estoque atual e flag `is_active`;
- `LoteProducao`: produto, quantidade, data/hora de saída e status (`EM_PRODUCAO`, `PRONTO` ou `ESGOTADO`);
- `Venda`: atendente, data/hora, valor total e status (`EM_ABERTO`, `CONCLUIDA` ou `CANCELADA`);
- `ItemVenda`: venda, produto, quantidade, preço unitário aplicado e subtotal.

Use `PROTECT`, `CASCADE` e os demais comportamentos de exclusão exatamente como descritos na especificação. Preços e quantidades devem usar `Decimal`, nunca `float`.

## 4. Regras de negócio obrigatórias

As regras devem ser aplicadas no domínio/formulários/serviços e não somente na apresentação:

1. Produtos `UN` aceitam apenas quantidades inteiras; produtos `KG` aceitam até três casas decimais.
2. Ao inserir um item, copie o preço atual do produto para `preco_unitario_aplicado`; alterações futuras do preço não podem modificar o histórico da venda.
3. Ao mudar um lote para `PRONTO`, some sua quantidade ao estoque do produto correspondente.
4. Ao finalizar uma venda, deduza do estoque as quantidades de todos os itens.
5. Ao cancelar uma venda que já foi concluída, recomponha o estoque de todos os seus itens.
6. Nunca permita estoque negativo. Valide estoque suficiente tanto ao adicionar o item quanto ao finalizar a venda.
7. Produtos inativos não devem aparecer no PDV nem aceitar novos lotes de produção.
8. Uma venda sem itens não pode ser finalizada.

Operações que alteram estoque e status devem ser atômicas e idempotentes quando aplicável. Evite aplicar duas vezes a baixa ou o estorno ao salvar novamente o mesmo objeto. Quando houver concorrência, proteja a leitura e atualização do estoque com transação e bloqueio apropriados do banco.

## 5. Arquitetura e responsabilidades

- **Models:** estrutura persistida, relacionamentos, escolhas e validações simples de campo.
- **Forms:** validação dos dados recebidos pelo usuário e mensagens exibidas no formulário.
- **Services/use cases:** transições de status, cálculo de totais e operações atômicas de estoque.
- **Views:** autenticação/autorização necessária, composição do contexto, delegação aos serviços e redirecionamentos.
- **Templates:** apresentação, formulários e mensagens; não devem conter regras de negócio ou alterações de estoque.
- **URLs:** mantenha os nomes e caminhos definidos na seção de contratos de `spec.md`.

Não duplique a mesma regra em várias views. Erros de validação devem ser explícitos, informativos e exibidos com `invalid-feedback`; não use `except Exception: pass` nem esconda falhas de persistência.

## 6. Contratos de URLs

Implemente os seguintes contratos:

| URL | Método | View | Resultado de sucesso |
|---|---|---|---|
| `/produtos/` | GET | `ProductListView` | lista produtos e estoque |
| `/produtos/novo/` | GET, POST | `ProductCreateView` | redireciona para `/produtos/` |
| `/lotes/` | GET | `BatchListView` | painel de fornadas |
| `/lotes/novo/` | GET, POST | `BatchCreateView` | redireciona para `/lotes/` |
| `/pdv/` | GET, POST | `SaleCreateView` | redireciona para `/pdv/<id>/` |
| `/pdv/<int:pk>/` | GET | `SaleDetailView` | exibe o cupom |
| `/pdv/<int:pk>/adicionar/` | POST | `SaleAddItemView` | redireciona para o detalhe da venda |
| `/pdv/<int:pk>/finalizar/` | POST | `SaleFinalizeView` | baixa estoque e redireciona para `/pdv/` |
| `/pdv/<int:pk>/cancelar/` | POST | `SaleCancelView` | estorna estoque e redireciona para `/pdv/` |

## 7. Interface

- Todos os templates devem herdar de `base.html`.
- A navbar fixa deve oferecer links para PDV/Caixa, Fornadas, Produtos e Relatórios.
- O detalhe do PDV deve usar duas colunas responsivas: `col-md-7` para produtos e `col-md-5` para o cupom.
- Use cards para produtos no seletor, `input-group` para busca/quantidade e tabela para itens da venda.
- Destaque o total com `display-6` ou `badge bg-success`.
- O painel de lotes deve usar cards e badges: `bg-warning` para `EM_PRODUCAO`, `bg-success` para `PRONTO` e `bg-secondary` para `ESGOTADO`.
- Inputs devem usar `form-control` ou `form-select`. Erros devem aparecer em `invalid-feedback`.
- Inclua o partial `_messages.html` para mensagens do Django com `alert-success`, `alert-danger` e `alert-warning`, além de `btn-close`.

## 8. Testes e validação

Cubra fluxos felizes e casos de borda definidos em `spec.md`, especialmente quantidade inválida por unidade, congelamento de preço, entrada de lote no estoque, baixa, estorno, estoque insuficiente, produto inativo e venda vazia.

Execute, a partir deste diretório:

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

Não considere uma implementação concluída enquanto os testes relevantes não passarem e os fluxos de cadastro de produto, registro de lote, finalização e cancelamento de venda não puderem ser verificados.
