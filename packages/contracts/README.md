# API contracts

Run `apps/api/.venv/bin/python apps/api/scripts/export_openapi.py` and then
`npm --workspace @aba/contracts run generate`. The generated client types are
derived from FastAPI's OpenAPI document and are the source of truth for clients.
