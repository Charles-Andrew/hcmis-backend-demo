# HCMIS Backend

FastAPI backend for the HCMIS migration.

## Local development

1. Copy `.env.example` to `.env`.
2. Start database and Redis with Docker.
3. Run the API with:

```bash
uv run uvicorn app.main:app --reload
```

## Reset And Seed (QA)

From `hcmis-backend/`:

```bash
make db-clear
make seed-initial
```

Or run both in one shot:

```bash
make reset-and-seed
```

## Shared Resources File Storage

- Uploaded shared resource files are stored on the local filesystem.
- Default storage path: `./storage/shared-resources`
- Override path with: `SHARED_RESOURCES_STORAGE_DIR`
- Default max upload size: `50 MB` (`SHARED_RESOURCES_MAX_FILE_SIZE_MB`)
- Allowed file classes: document files (`pdf/doc/docx/xls/xlsx/ppt/pptx/txt/csv`) and media files (image/video/audio common types)
