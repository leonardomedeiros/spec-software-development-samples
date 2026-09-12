1. Certifique-se de que o SPECIFICATION.md e o AGENTS.md estão na raiz.
2. No Windows (PowerShell), execute o OpenCode:
      docker run --name opencode -it --rm -v "$($PWD.Path):/workspace" -w /workspace ghcr.io/anomalyco/opencode

   No Linux/WSL/macOS:
      docker run --name opencode -it --rm -v "$($PWD.Path):/workspace" -w /workspace ghcr.io/anomalyco/opencode

3. No OpenCode passe o prompt:
   > "

   Crie o módulo de Domínio em /workspace/tasktrack/domain/models.py seguindo as entidades, enums e regras de status definidas em /workspace/SPECIFICATION.md. Salve o arquivo usando a ferramenta 'write'.
   "


   