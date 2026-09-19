import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("STAND_BACKEND_URL", "http://127.0.0.1:8001")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("STAND_TIMEOUT", "30"))
