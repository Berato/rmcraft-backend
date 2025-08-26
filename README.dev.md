Developer setup quickstart

1. Create and activate a virtualenv using Poetry:

```bash
cd /Users/berato/Sites/rmcraft-backend
poetry install
poetry shell
```

2. If you prefer a local `.venv` inside the project (recommended for VS Code):

```bash
poetry config virtualenvs.in-project true
poetry install
```

3. In VS Code, pick the interpreter at `.venv/bin/python` (the workspace settings include this path).

4. If the editor still shows unresolved imports, run:

```bash
# ensure poetry created the .venv and dependencies are installed
poetry install
# then reload the VS Code window (Developer: Reload Window)
```
