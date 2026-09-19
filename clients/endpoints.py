"""HR backend endpoints, as read off the Swagger page at /docs."""

AUTH_TOKEN = "/auth/token"
AUTH_ME = "/auth/me"
DEPARTMENTS = "/departments"
POSITIONS = "/positions"
EMPLOYEES = "/employees"          # GET lists the directory, POST hires
VACATION_BALANCE = "/employees/{employee_id}/vacation-balance"
STAND_RESET = "/_stand/reset"
