from uuid import UUID

from jose import JWTError
from starlette.requests import Request

from app.core.security import decode_access_token
from app.db.session import async_session_maker
from app.services.logs import create_app_log

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_EXCLUDED_PATH_PREFIXES = {
    "/health",
    "/app-logs",
    "/docs",
    "/redoc",
    "/openapi.json",
}
_ACTION_VERBS = {
    "respond": "Responded to",
    "escalate": "Escalated",
    "ack": "Acknowledged",
    "read": "Marked as read",
    "read-all": "Marked all as read",
    "publish": "Published",
    "archive": "Archived",
    "unarchive": "Unarchived",
    "draft": "Moved to draft",
    "close": "Closed",
    "reopen": "Reopened",
    "submit": "Submitted",
    "reset": "Reset",
    "release-toggle": "Updated release status for",
    "finalize-toggle": "Updated finalization status for",
    "end": "Ended",
    "votes": "Recorded vote for",
    "shares": "Updated share access for",
    "confidential-access": "Updated confidential access for",
    "access": "Updated access for",
}
_METHOD_VERBS = {
    "POST": "Created",
    "PUT": "Updated",
    "PATCH": "Updated",
    "DELETE": "Deleted",
}


def _is_id_segment(segment: str) -> bool:
    if segment.isdigit():
        return True
    try:
        UUID(segment)
        return True
    except ValueError:
        return False


def _humanize_resource_name(value: str) -> str:
    label = value.replace("-", " ").strip().lower()
    if label.endswith("ies"):
        return f"{label[:-3]}y"
    if label.endswith("s"):
        return label[:-1]
    return label


def _build_human_readable_detail(request: Request) -> str:
    method = request.method.upper()
    segments = [segment for segment in request.url.path.strip("/").split("/") if segment]
    if not segments:
        return f"{_METHOD_VERBS.get(method, 'Updated')} resource."

    action_segment = None
    if segments and not _is_id_segment(segments[-1]) and segments[-1] in _ACTION_VERBS:
        action_segment = segments[-1]
        segments = segments[:-1]

    target_id = None
    if segments and _is_id_segment(segments[-1]):
        target_id = segments[-1]
        segments = segments[:-1]

    resource_segment = segments[-1] if segments else "resource"
    context_segment = segments[-2] if len(segments) > 1 else None
    resource = _humanize_resource_name(resource_segment)
    context = (
        f"{_humanize_resource_name(context_segment)} "
        if context_segment and context_segment not in {"auth"}
        else ""
    )

    if action_segment is not None:
        verb = _ACTION_VERBS[action_segment]
    else:
        verb = _METHOD_VERBS.get(method, "Updated")

    id_suffix = f" #{target_id}" if target_id is not None else ""
    return f"{verb} {context}{resource}{id_suffix}."


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "").strip()
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _resolve_user_id_from_request(request: Request) -> UUID | None:
    token = _extract_bearer_token(request)
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None
    try:
        return UUID(subject)
    except ValueError:
        return None


def should_log_request(request: Request, status_code: int) -> bool:
    if request.method.upper() not in _MUTATING_METHODS:
        return False
    if status_code >= 400:
        return False
    path = request.url.path
    return not any(path.startswith(prefix) for prefix in _EXCLUDED_PATH_PREFIXES)


async def write_audit_log(request: Request, status_code: int) -> None:
    if not should_log_request(request, status_code):
        return
    user_id = _resolve_user_id_from_request(request)
    if user_id is None:
        return

    details = _build_human_readable_detail(request)

    async with async_session_maker() as session:
        await create_app_log(session, user_id=user_id, details=details)
