from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.performance import Questionnaire
from app.repositories.performance import QuestionnaireRepository

_SEED_DIR = Path(__file__).resolve().parent / "data" / "performance_questionnaires"
_RESERVED_KEYS = {"code", "title", "description", "is_active", "questionnaire_content"}


def _read_seed_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Seed file must contain a JSON object: {path.name}")
    return raw


def _required_string_field(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"Missing required field '{key}'.")
    if not isinstance(value, str):
        raise ValueError(f"Field '{key}' must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Field '{key}' cannot be empty.")
    return cleaned


def _optional_string_field(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Field '{key}' must be a string when provided.")
    cleaned = value.strip()
    return cleaned if cleaned else None


def _normalize_content(payload: dict[str, Any], source_file: str) -> dict[str, Any]:
    questionnaire_content = payload.get("questionnaire_content")
    if not isinstance(questionnaire_content, list):
        raise ValueError("Field 'questionnaire_content' must be a list.")

    content: dict[str, Any] = {
        "questionnaire_content": questionnaire_content,
        "source_seed_file": source_file,
    }

    for key, value in payload.items():
        if key not in _RESERVED_KEYS:
            content[key] = value

    return content


async def import_performance_questionnaires(
    session: AsyncSession,
    *,
    seed_dir: Path | None = None,
) -> tuple[int, int]:
    repository = QuestionnaireRepository(session)
    directory = seed_dir or _SEED_DIR

    if not directory.exists():
        raise FileNotFoundError(f"Seed directory not found: {directory}")

    created = 0
    updated = 0

    for path in sorted(directory.glob("*.json")):
        payload = _read_seed_payload(path)
        code = _required_string_field(payload, "code")
        title = _required_string_field(payload, "title")
        description = _optional_string_field(payload, "description")
        is_active = payload.get("is_active")
        if is_active is None:
            is_active = True
        if not isinstance(is_active, bool):
            raise ValueError("Field 'is_active' must be a boolean when provided.")

        content = _normalize_content(payload, path.name)
        existing = await repository.get_by_code(code)
        if existing is None:
            await repository.create(
                Questionnaire(
                    code=code.upper(),
                    title=title,
                    description=description,
                    content=content,
                    is_active=is_active,
                )
            )
            created += 1
            continue

        existing.title = title
        existing.description = description
        existing.content = content
        existing.is_active = is_active
        await repository.save(existing)
        updated += 1

    return created, updated
