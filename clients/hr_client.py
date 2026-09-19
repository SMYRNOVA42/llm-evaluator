"""Client for the HR backend, written against its Swagger page.

One method per API method, each returning the raw `Response`. Callers pull out whatever
they need — `.json()`, `.status_code`, headers. No argument validation and no error
handling here on purpose: input is the backend's business, and a test that sends a wrong
type must reach the backend to find out how it answers.
"""

from requests import Response

from . import endpoints
from .base_client import BaseClient
from .config import HR_BACKEND_URL


class HRClient(BaseClient):
    def __init__(self, login: str, password: str) -> None:
        super().__init__(HR_BACKEND_URL)
        self.login = login
        self.password = password
        self.token = self.get_token()
        self.headers = self.build_headers(self.token)
        self.employee_id = self.me().json()["id"]

    def get_token(self) -> str:
        """The one place a response is unwrapped: `__init__` needs the string, not a body."""
        response = self.auth_token(self.login, self.password)
        return response.json()["access_token"]

    def auth_token(self, login: str, password: str) -> Response:
        return self.post(
            endpoint=endpoints.AUTH_TOKEN,
            data={"login": login, "password": password},
            headers=self.build_headers(),
        )

    def me(self) -> Response:
        return self.get(endpoint=endpoints.AUTH_ME, headers=self.headers)

    def departments(self) -> Response:
        return self.get(endpoint=endpoints.DEPARTMENTS, headers=self.headers)

    def positions(self) -> Response:
        return self.get(endpoint=endpoints.POSITIONS, headers=self.headers)

    def employees(self) -> Response:
        return self.get(endpoint=endpoints.EMPLOYEES, headers=self.headers)

    def add_employee(self, full_name, date_of_birth, position, department) -> Response:
        data = {
            "full_name": full_name,
            "date_of_birth": date_of_birth,
            "position": position,
            "department": department,
        }
        return self.post(endpoint=endpoints.EMPLOYEES, data=data, headers=self.headers)

    def vacation_balance(self, employee_id=None) -> Response:
        """Defaults to the authenticated employee; pass an id to look at someone else."""
        if employee_id is None:
            employee_id = self.employee_id
        endpoint = endpoints.VACATION_BALANCE.format(employee_id=employee_id)
        return self.get(endpoint=endpoint, headers=self.headers)

    def reset(self) -> Response:
        """Stand-only. Re-seeds the backend so a test starts from known data."""
        return self.post(endpoint=endpoints.STAND_RESET, headers=self.headers)
