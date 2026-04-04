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
make db-reset
make seed-initial
make seed-performance-questionnaires
```

Or run both in one shot:

```bash
make reset-and-seed
```

## Production Bootstrap

If you are deploying a fresh production database with no users yet, bootstrap the first HR account with:

```bash
BOOTSTRAP_HR_EMAIL=hr@company.com \
BOOTSTRAP_HR_PASSWORD='choose-a-strong-password' \
make seed-bootstrap-hr
```

Optional overrides:

- `BOOTSTRAP_HR_FIRST_NAME` and `BOOTSTRAP_HR_LAST_NAME`
- `BOOTSTRAP_HR_EMPLOYEE_NUMBER`
- `BOOTSTRAP_HR_DEPARTMENT_CODE` and `BOOTSTRAP_HR_DEPARTMENT_NAME`

This command refuses to run if users already exist, so it is safe for a one-time prod bootstrap.

## Shared Resources File Storage

- Uploaded shared resource files are stored on the local filesystem.
- Default storage path: `./storage/shared-resources`
- Override path with: `SHARED_RESOURCES_STORAGE_DIR`
- Default max upload size: `50 MB` (`SHARED_RESOURCES_MAX_FILE_SIZE_MB`)
- Allowed file classes: document files (`pdf/doc/docx/xls/xlsx/ppt/pptx/txt/csv`) and media files (image/video/audio common types)
