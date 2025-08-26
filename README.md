Minimal FastAPI app with a `/health` endpoint and Swagger UI.

Using Poetry (preferred)

1. Install Poetry if you don't have it: follow https://python-poetry.org/docs/

2. Create an in-project virtualenv and install dependencies:

```bash
poetry config virtualenvs.in-project true --local
poetry install
```

3. Activate the virtualenv created by Poetry:

```bash
source .venv/bin/activate
```

4. Run the app with uvicorn:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

5. Open the Swagger UI at: http://127.0.0.1:8000/docs

Run tests

```bash
pytest -q
```
