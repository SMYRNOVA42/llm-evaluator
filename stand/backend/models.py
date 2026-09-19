"""Wire schemas of the HR backend.

`position` and `department` are integer ids into their own collections, not names —
the backend links entities the way a relational store does.
"""

from datetime import date

from pydantic import BaseModel, Field


class Department(BaseModel):
    id: int
    name: str


class Position(BaseModel):
    id: int
    title: str


class NewEmployee(BaseModel):
    full_name: str = Field(min_length=1)
    date_of_birth: date
    position: int
    department: int


class Employee(NewEmployee):
    id: int


class VacationBalance(BaseModel):
    all_days: int
    vacation: int
    sick_leave: int
    additional: int


class Credentials(BaseModel):
    login: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
