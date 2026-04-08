class HCMISException(Exception):
    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ConflictError(HCMISException):
    status_code = 409


class NotFoundError(HCMISException):
    status_code = 404


class PermissionDeniedError(HCMISException):
    status_code = 403


class BadRequestError(HCMISException):
    status_code = 400
