# Guia de Debug - Editar Tarefa

## Passos para Debugar

### 1. Abra o Console do Navegador
- Pressione **F12** (ou Ctrl+Shift+I)
- Vá para a aba **Console**

### 2. Teste a Edição
1. Clique em um botão de **Editar** (lápis) em uma tarefa
2. Verifique a console do navegador:
   - Deve aparecer: `Modal opened for task: {UUID} Form action: /web/tasks/{UUID}`
3. Edite algum campo (ex: título)
4. Clique em **Atualizar Tarefa**
5. Verifique a console:
   - Deve aparecer: `Form submitted for task: {UUID}`

### 3. Verifique os Logs do Django
Na terminal onde rodou `python manage.py runserver`:
```
POST /web/tasks/{UUID} HTTP/1.1" 302 
```

Se não ver essa linha, o formulário não está sendo enviado.

### 4. Erros Possíveis

#### Erro: "Tarefa não encontrada"
- Significa que o UUID está inválido ou a tarefa foi deletada
- Verifique o UUID no console

#### Erro: "Erro ao atualizar tarefa: ..."
- Anote a mensagem de erro exata
- Pode ser validação de dados

#### Sem mensagem de erro
- Pode ser redirecionamento silencioso
- Verifique se a página recarrega para "/"

### 5. Dados Que Serão Enviados
```
POST /web/tasks/{task_id}
title: {valor digitado}
description: {valor digitado}
priority: {LOW|MEDIUM|HIGH}
assignee_id: {UUID ou vazio}
due_date: {YYYY-MM-DDTHH:mm ou vazio}
csrfmiddlewaretoken: {token}
```

## Informações para Reportar

Se continuar não funcionando, reporte:
1. O que aparece na **console do navegador** (F12)
2. O UUID da tarefa que tentou editar
3. Qual campo tentou alterar
4. Mensagem de erro na página (se houver)
5. Logs do Django (últimas linhas quando clicou em atualizar)

## Teste Rápido com cURL (Terminal)

```bash
# Obtenha um UUID de tarefa primeiro, depois:
curl -X POST http://localhost:8000/web/tasks/{UUID} \
  -d "title=Novo Titulo&priority=HIGH" \
  -H "X-CSRFToken: {obtenha do HTML}" \
  -c cookies.txt -b cookies.txt
```
