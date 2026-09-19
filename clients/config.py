"""Where the clients point. Values come from the environment, never from source."""

import os

from dotenv import load_dotenv

load_dotenv()

HR_BACKEND_URL = os.getenv("HR_BACKEND_URL", "http://127.0.0.1:8001")
MODEL_WS_URL = os.getenv("MODEL_WS_URL", "ws://127.0.0.1:8000/ws")

# An ordinary employee: may read their own data, may not hire.
HR_LOGIN = os.getenv("HR_LOGIN", "e.carter")
HR_PASSWORD = os.getenv("HR_PASSWORD", "demo")

# A People & Culture employee, the only role allowed to add someone to the company.
PEOPLE_TEAM_LOGIN = os.getenv("PEOPLE_TEAM_LOGIN", "m.brooks")

HTTP_TIMEOUT_SECONDS = float(os.getenv("HR_TIMEOUT", "10"))
MODEL_TIMEOUT_SECONDS = float(os.getenv("MODEL_TIMEOUT", "60"))
