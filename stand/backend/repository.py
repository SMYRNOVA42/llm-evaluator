"""Storage for the stand.

Deliberately in-memory: a pet-project stand should start with one command and no
database server. The `HrRepository` protocol is the seam — swapping in SQLite or
Postgres means adding one class here and changing nothing in the routers.
"""

import json
from pathlib import Path
from typing import Protocol

from .errors import EmployeeNotFound, UnknownReference
from .models import Department, Employee, NewEmployee, Position, VacationBalance

SEED_PATH = Path(__file__).with_name("seed.json")


class HrRepository(Protocol):
    def employees(self) -> list[Employee]: ...
    def departments(self) -> list[Department]: ...
    def positions(self) -> list[Position]: ...
    def employee(self, employee_id: int) -> Employee: ...
    def employee_by_login(self, login: str) -> Employee | None: ...
    def add_employee(self, new_employee: NewEmployee) -> Employee: ...
    def vacation_balance(self, employee_id: int) -> VacationBalance: ...
    def reset(self) -> None: ...


class InMemoryHrRepository:
    """Seeded from `seed.json`. State lives for the process only."""

    def __init__(self, seed_path: Path = SEED_PATH) -> None:
        self._seed_path = seed_path
        self.reset()

    def reset(self) -> None:
        seed = json.loads(self._seed_path.read_text(encoding="utf-8"))
        self._departments = {d["id"]: Department(**d) for d in seed["departments"]}
        self._positions = {p["id"]: Position(**p) for p in seed["positions"]}
        self._logins = {e["login"]: e["id"] for e in seed["employees"]}
        self._employees = {
            e["id"]: Employee(**{k: v for k, v in e.items() if k != "login"})
            for e in seed["employees"]
        }
        self._balances = {
            int(employee_id): VacationBalance(**balance)
            for employee_id, balance in seed["vacation_balances"].items()
        }

    def employees(self) -> list[Employee]:
        return list(self._employees.values())

    def departments(self) -> list[Department]:
        return list(self._departments.values())

    def positions(self) -> list[Position]:
        return list(self._positions.values())

    def employee(self, employee_id: int) -> Employee:
        try:
            return self._employees[employee_id]
        except KeyError:
            raise EmployeeNotFound(employee_id) from None

    def employee_by_login(self, login: str) -> Employee | None:
        employee_id = self._logins.get(login)
        return None if employee_id is None else self._employees[employee_id]

    def add_employee(self, new_employee: NewEmployee) -> Employee:
        if new_employee.position not in self._positions:
            raise UnknownReference("position", new_employee.position)
        if new_employee.department not in self._departments:
            raise UnknownReference("department", new_employee.department)

        employee = Employee(id=max(self._employees, default=0) + 1, **new_employee.model_dump())
        self._employees[employee.id] = employee
        self._balances[employee.id] = VacationBalance(
            all_days=0, vacation=0, sick_leave=0, additional=0
        )
        return employee

    def vacation_balance(self, employee_id: int) -> VacationBalance:
        if employee_id not in self._employees:
            raise EmployeeNotFound(employee_id)
        return self._balances[employee_id]
