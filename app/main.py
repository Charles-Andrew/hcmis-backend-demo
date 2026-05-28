from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes import auth, attendance, chat, health, leave, payroll, performance, reports
from app.api.routes import departments, logs, notifications, profile, special_requests, users
from app.api.routes import trainings
from app.core.exceptions import HCMISException
from app.core.config import settings
from app.core.audit import write_audit_log


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(logs.router)
app.include_router(profile.router)
app.include_router(attendance.router)
app.include_router(leave.router)
app.include_router(special_requests.router)
app.include_router(payroll.router)
app.include_router(performance.router)
app.include_router(chat.router)
app.include_router(reports.router)
app.include_router(trainings.router)


@app.middleware("http")
async def audit_mutations_middleware(request, call_next):
    response = await call_next(request)
    await write_audit_log(request, response.status_code)
    return response


@app.exception_handler(HCMISException)
async def handle_hcmis_exception(_request, exc: HCMISException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
