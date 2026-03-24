# HCMIS Backend

FastAPI backend for the HCMIS migration.

## Local development

1. Copy `.env.example` to `.env`.
2. Start database and Redis with Docker.
3. Run the API with:

```bash
uv run uvicorn app.main:app --reload
```

