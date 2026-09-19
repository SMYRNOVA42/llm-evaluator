import os

from dotenv import load_dotenv

load_dotenv()

DEMO_PASSWORD = os.getenv("STAND_PASSWORD", "demo")

# Hiring is an HR task. Membership of this department is what authorises it - the stand
# keeps authorisation in the backend, where it belongs, not in the assistant's prompt.
HR_DEPARTMENT_ID = int(os.getenv("STAND_HR_DEPARTMENT_ID", "2"))
