"""Evaluator settings. The only place the environment is read."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Sonnet rather than Opus: the judge runs once per phrasing, so tier cost compounds
# across a suite. Changing this invalidates every stored verdict - re-baseline, never mix.
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-sonnet-5")
JUDGE_EFFORT = os.getenv("JUDGE_EFFORT", "medium")
JUDGE_MAX_TOKENS = int(os.getenv("JUDGE_MAX_TOKENS", "8000"))

PROJECT_NAME = os.getenv("PROJECT_NAME", "HR assistant")
ALLURE_RESULTS_DIR = PROJECT_ROOT / os.getenv("ALLURE_RESULTS", "allure-results")
ALLURE_REPORT_DIR = PROJECT_ROOT / os.getenv("ALLURE_REPORT", "allure-report")

# Link to the published report, once there is one. GitHub Pages is the natural home:
# a workflow runs `allure generate` and publishes the result. Empty until then.
REPORT_URL = os.getenv("REPORT_URL", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
