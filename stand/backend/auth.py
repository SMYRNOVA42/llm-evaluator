"""Opaque bearer tokens, held in memory.

Not a security design — a stand needs an auth step so that `ApiClient` in the
evaluator has a real one to exercise.
"""

from uuid import uuid4

from .config import DEMO_PASSWORD
from .errors import EmployeeNotFound, InvalidCredentials
from .models import Credentials, Employee
from .repository import HrRepository


class TokenStore:
    def __init__(self, repository: HrRepository) -> None:
        self._repository = repository
        self._tokens: dict[str, int] = {}

    def issue(self, credentials: Credentials) -> str:
        employee = self._repository.employee_by_login(credentials.login)
        if employee is None or credentials.password != DEMO_PASSWORD:
            raise InvalidCredentials
        token = uuid4().hex
        self._tokens[token] = employee.id
        return token

    def resolve(self, token: str) -> Employee | None:
        employee_id = self._tokens.get(token)
        if employee_id is None:
            return None
        try:
            return self._repository.employee(employee_id)
        except EmployeeNotFound:
            # The stand was re-seeded under this token. Treat it as expired, not as a crash.
            del self._tokens[token]
            return None
