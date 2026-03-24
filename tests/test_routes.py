from fastapi.routing import APIRoute

from app.main import app


def test_core_routes_are_registered():
    paths = {
        route.path
        for route in app.router.routes
        if isinstance(route, APIRoute)
    }

    assert "/departments" in paths
    assert "/users" in paths
    assert "/notifications" in paths
    assert "/app-logs" in paths
    assert "/profile/me" in paths
    assert "/attendance/shifts" in paths
    assert "/attendance/device/getrequest" in paths
    assert "/attendance/me/{year}/{month}" in paths
    assert "/attendance/users/{user_id}/{year}/{month}" in paths
    assert "/users/{user_id}/biometric" in paths
    assert "/leave/requests/me" in paths
    assert "/leave/requests/review" in paths
    assert "/leave/approvers" in paths
    assert "/leave/credits/me" in paths
    assert "/payroll/settings" in paths
    assert "/payroll/jobs" in paths
    assert "/payroll/payslips" in paths
    assert "/payroll/thirteenth-month-pays" in paths
    assert "/performance/questionnaires" in paths
    assert "/performance/user-evaluations" in paths
    assert "/chat/users" in paths
    assert "/chat/conversations/{other_user_id}" in paths
    assert "/chat/messages" in paths
    assert "/reports/catalog" in paths
    assert "/reports/payroll/yearly-expense" in paths
    assert "/reports/users/demographics/gender" in paths
