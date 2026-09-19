"""Fixtures for the evaluation suite.

A test receives `client`, `model` and `judge` already built and authenticated. It never
constructs one itself, so swapping a backend, a transport or a judge provider touches
this file and nothing else.
"""

import pytest
import requests

from clients import HRClient, ModelClient
from clients.config import (
    HR_BACKEND_URL,
    HR_LOGIN,
    HR_PASSWORD,
    MODEL_WS_URL,
    PEOPLE_TEAM_LOGIN,
)
from evaluator.judges import AnthropicJudge

SERVICES = (("backend", f"{HR_BACKEND_URL}/health"), ("assistant", "http://127.0.0.1:8000/health"))


@pytest.fixture(scope="session")
def services_are_up() -> None:
    """Stop the run outright if the product is not there.

    Required by the client fixtures rather than autouse, so that checks which never touch
    the product — the judge agreement set — still run when the stand is down. That is
    exactly when you want them: right after editing a prompt.

    A suite that quietly skips when the thing under test is down reports green and means
    nothing. Better to refuse to start and say which service is missing.
    """
    for name, url in SERVICES:
        try:
            requests.get(url, timeout=3).raise_for_status()
        except requests.RequestException as error:
            pytest.exit(
                f"{name} is not answering at {url} ({type(error).__name__}). "
                f"Start the stand first - see README.md - then re-run.",
                returncode=2,
            )


@pytest.fixture(scope="session")
def client(services_are_up: None) -> HRClient:
    """The HR backend, authenticated as the employee under test. Ground truth lives here."""
    return HRClient(login=HR_LOGIN, password=HR_PASSWORD)


@pytest.fixture(scope="session")
def hr_client(services_are_up: None) -> HRClient:
    """Authenticated as People & Culture — the only role permitted to hire."""
    return HRClient(login=PEOPLE_TEAM_LOGIN, password=HR_PASSWORD)


@pytest.fixture
def clean_backend(hr_client: HRClient) -> None:
    """Re-seed around any test that changes backend state.

    Before as well as after: a test must not inherit whatever the previous one left,
    and must not leave anything for the next. This is what keeps mutating tests
    order-independent without a database to roll back.
    """
    hr_client.reset()
    yield
    hr_client.reset()


@pytest.fixture
def model(client: HRClient) -> ModelClient:
    """The assistant under test.

    Function-scoped on purpose: every test gets a fresh connection, so no conversation
    state can leak from one phrasing into the next and make results depend on order.
    """
    with ModelClient(token=client.token, url=MODEL_WS_URL) as connection:
        yield connection


@pytest.fixture
def hr_model(hr_client: HRClient) -> ModelClient:
    """The assistant, talking to a People & Culture employee."""
    with ModelClient(token=hr_client.token, url=MODEL_WS_URL) as connection:
        yield connection


@pytest.fixture(scope="session")
def judge() -> AnthropicJudge:
    """The judge. Stateless, so one per session is enough, and it needs no stand."""
    return AnthropicJudge()
