"""Transport for every HTTP client in this project.

Holds the verbs, the header building and the base URL, and nothing else. It does not
know a single endpoint, and it deliberately does not inspect what comes back: no
`raise_for_status`, no status checks, no retries, no exception handling. Every method
hands the caller the raw `Response` so a test can assert on the status code, the body or
the headers — and so a backend defect never gets disguised as a client defect.
"""

import requests

from .config import HTTP_TIMEOUT_SECONDS


class BaseClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def build_headers(self, token: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}"

    def get(self, endpoint, headers=None, params=None) -> requests.Response:
        return self.session.get(
            self.url(endpoint), headers=headers, params=params, timeout=HTTP_TIMEOUT_SECONDS
        )

    def post(self, endpoint, data=None, headers=None) -> requests.Response:
        return self.session.post(
            self.url(endpoint), json=data, headers=headers, timeout=HTTP_TIMEOUT_SECONDS
        )

    def put(self, endpoint, data=None, headers=None) -> requests.Response:
        return self.session.put(
            self.url(endpoint), json=data, headers=headers, timeout=HTTP_TIMEOUT_SECONDS
        )

    def delete(self, endpoint, headers=None) -> requests.Response:
        return self.session.delete(
            self.url(endpoint), headers=headers, timeout=HTTP_TIMEOUT_SECONDS
        )
