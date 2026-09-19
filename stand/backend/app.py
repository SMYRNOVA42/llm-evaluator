"""HR backend of the demo stand.

API methods here are ordinary REST endpoints. They are *not* the assistant's methods —
the assistant's methods live in `stand/assistant/methods.py` and are a different concept.
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import TokenStore
from .config import HR_DEPARTMENT_ID
from .errors import EmployeeNotFound, InvalidCredentials, NotAuthorized, UnknownReference
from .models import (
    Credentials,
    Department,
    Employee,
    NewEmployee,
    Position,
    Token,
    VacationBalance,
)
from .repository import InMemoryHrRepository

repository = InMemoryHrRepository()
tokens = TokenStore(repository)
bearer = HTTPBearer(auto_error=True)

app = FastAPI(title="HR backend (demo stand)")


def current_employee(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> Employee:
    employee = tokens.resolve(credentials.credentials)
    if employee is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    return employee


Caller = Annotated[Employee, Depends(current_employee)]


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness only. No auth, no storage access — just "this process is answering"."""
    return {"status": "ok", "service": "backend"}


@app.post("/auth/token", response_model=Token)
def issue_token(credentials: Credentials) -> Token:
    try:
        return Token(access_token=tokens.issue(credentials))
    except InvalidCredentials as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error


@app.get("/auth/me", response_model=Employee)
def whoami(caller: Caller) -> Employee:
    return caller


@app.get("/departments", response_model=list[Department])
def list_departments(caller: Caller) -> list[Department]:
    return repository.departments()


@app.get("/positions", response_model=list[Position])
def list_positions(caller: Caller) -> list[Position]:
    return repository.positions()


@app.get("/employees", response_model=list[Employee])
def list_employees(caller: Caller) -> list[Employee]:
    """The company directory. Open to any authenticated employee."""
    return repository.employees()


@app.post("/employees", response_model=Employee)
def add_new_employee(new_employee: NewEmployee, caller: Caller) -> Employee:
    if caller.department != HR_DEPARTMENT_ID:
        error = NotAuthorized("hire")
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error))
    try:
        return repository.add_employee(new_employee)
    except UnknownReference as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@app.get("/employees/{employee_id}/vacation-balance", response_model=VacationBalance)
def get_vacation_balance(employee_id: int, caller: Caller) -> VacationBalance:
    try:
        return repository.vacation_balance(employee_id)
    except EmployeeNotFound as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@app.post("/_stand/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_stand() -> None:
    """Stand-only. Re-seeds state so a suite starts from a known fixture."""
    repository.reset()
