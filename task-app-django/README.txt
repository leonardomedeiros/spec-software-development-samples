## Ambiente e dependências

Este projeto usa `uv` para gerenciar dependências. O arquivo `uv.lock` deve ser versionado.

```powershell
uv sync
uv run python manage.py migrate
uv run python manage.py check
uv run python manage.py test
```

Depois de alterar as dependências no `pyproject.toml`, atualize o lockfile com:

```powershell
uv lock
uv sync
```

1. Certifique-se de que o SPECIFICATION.md e o AGENTS.md estão na raiz.
2. No Windows (PowerShell), execute o OpenCode:
      docker run --name opencode -it --rm -v "$($PWD.Path):/workspace" -w /workspace ghcr.io/anomalyco/opencode

   No Linux/WSL/macOS:
      docker run --name opencode -it --rm -v "$($PWD.Path):/workspace" -w /workspace ghcr.io/anomalyco/opencode

3. No OpenCode passe o prompt:
   > "

   Crie o módulo de Domínio em /workspace/tasktrack/domain/models.py seguindo as entidades, enums e regras de status definidas em /workspace/SPECIFICATION.md. Salve o arquivo usando a ferramenta 'write'.
   "
## Criação do Primeiro Usuário
* Para inicializar uma base sem usuários, disponibilizar o comando:
  `python manage.py create_tasktrack_user --name "Nome" --email usuario@exemplo.com --password "senha-segura" --role ADMIN`.
   