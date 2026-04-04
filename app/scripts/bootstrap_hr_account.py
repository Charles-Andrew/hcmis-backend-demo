from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.base  # noqa: F401
from app.core.security import hash_password
from app.db.session import async_session_maker
from app.models.department import Department
from app.models.user import User

DEFAULT_DEPARTMENT_CODE = "HR"
DEFAULT_DEPARTMENT_NAME = "Human Resources"
DEFAULT_EMPLOYEE_NUMBER = "HR-001"


@dataclass(frozen=True)
class BootstrapConfig:
    email: str
    password: str
    first_name: str
    last_name: str
    employee_number: str
    department_code: str
    department_name: str


def _get_config() -> BootstrapConfig:
    email = os.getenv("BOOTSTRAP_HR_EMAIL")
    password = os.getenv("BOOTSTRAP_HR_PASSWORD")
    if not email or not password:
        raise ValueError(
            "BOOTSTRAP_HR_EMAIL and BOOTSTRAP_HR_PASSWORD are required."
        )

    return BootstrapConfig(
        email=email.strip().lower(),
        password=password,
        first_name=os.getenv("BOOTSTRAP_HR_FIRST_NAME", "HR"),
        last_name=os.getenv("BOOTSTRAP_HR_LAST_NAME", "Admin"),
        employee_number=os.getenv("BOOTSTRAP_HR_EMPLOYEE_NUMBER", DEFAULT_EMPLOYEE_NUMBER),
        department_code=os.getenv("BOOTSTRAP_HR_DEPARTMENT_CODE", DEFAULT_DEPARTMENT_CODE),
        department_name=os.getenv(
            "BOOTSTRAP_HR_DEPARTMENT_NAME",
            DEFAULT_DEPARTMENT_NAME,
        ),
    )


async def _get_user_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one() or 0)


async def _get_or_create_department(session: AsyncSession, config: BootstrapConfig) -> Department:
    result = await session.execute(
        select(Department).where(Department.code == config.department_code)
    )
    department = result.scalar_one_or_none()
    if department is None:
        department = Department(code=config.department_code, name=config.department_name)
        session.add(department)
        await session.flush()
        return department

    department.name = config.department_name
    return department


async def _bootstrap_hr_account() -> None:
    config = _get_config()

    async with async_session_maker() as session:
        user_count = await _get_user_count(session)
        if user_count > 0:
            raise RuntimeError(
                "Bootstrap aborted: users already exist. "
                "This script is only for the first HR account."
            )

        department = await _get_or_create_department(session, config)
        existing_user = await session.execute(
            select(User).where(User.email == config.email)
        )
        user = existing_user.scalar_one_or_none()
        if user is None:
            user = User(
                email=config.email,
                password_hash=hash_password(config.password),
                first_name=config.first_name,
                last_name=config.last_name,
                employee_number=config.employee_number,
                role="HR",
                department_id=department.id,
                can_modify_shift=False,
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
        else:
            user.password_hash = hash_password(config.password)
            user.first_name = config.first_name
            user.last_name = config.last_name
            user.employee_number = config.employee_number
            user.role = "HR"
            user.department_id = department.id
            user.can_modify_shift = False
            user.is_active = True
            user.is_superuser = True

        await session.commit()

    print("Bootstrapped initial HR account:")
    print(f"- {config.email}")
    print("- role: HR")
    print(f"- department: {config.department_code} / {config.department_name}")


def main() -> None:
    asyncio.run(_bootstrap_hr_account())


if __name__ == "__main__":
    main()
