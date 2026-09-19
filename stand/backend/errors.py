"""Backend-specific failures, translated to HTTP once, in the router layer."""


class BackendError(Exception):
    """Base class for everything this backend refuses to do."""


class EmployeeNotFound(BackendError):
    def __init__(self, employee_id: int) -> None:
        super().__init__(f"employee {employee_id} does not exist")
        self.employee_id = employee_id


class UnknownReference(BackendError):
    """A foreign key pointing at a row that is not there."""

    def __init__(self, field: str, value: int) -> None:
        super().__init__(f"{field}={value} does not exist")
        self.field = field
        self.value = value


class InvalidCredentials(BackendError):
    def __init__(self) -> None:
        super().__init__("unknown login or password")


class NotAuthorized(BackendError):
    """The caller is authenticated but not allowed to do this."""

    def __init__(self, action: str) -> None:
        super().__init__(f"only People & Culture may {action}")
        self.action = action
