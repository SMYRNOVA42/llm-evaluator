"""The assistant's methods — what the orchestrator can route a user message to.

An assistant method is NOT a backend endpoint. `vacation_balance` is a capability of the
model; `GET /employees/{id}/vacation-balance` is the API call that capability happens to
need. The evaluator tests the former and uses the latter as ground truth.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssistantMethod:
    name: str
    description: str


VACATION_BALANCE = AssistantMethod(
    name="vacation_balance",
    description="The employee asks how many vacation, sick-leave or extra days they have left.",
)

ADD_EMPLOYEE = AssistantMethod(
    name="add_employee",
    description=(
        "The employee asks to hire someone or add a new person to the company, "
        "giving a name and usually a role and a department."
    ),
)

NOT_MATCHED = AssistantMethod(
    name="not_matched",
    description=(
        "Greetings, farewells, small talk, and anything outside HR self-service. "
        "The fallback whenever no other method clearly fits."
    ),
)

METHODS: tuple[AssistantMethod, ...] = (VACATION_BALANCE, ADD_EMPLOYEE, NOT_MATCHED)
BY_NAME = {method.name: method for method in METHODS}
FALLBACK = NOT_MATCHED
