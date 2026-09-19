"""Are both stand services up?

Run before starting anything that depends on them. Exits 0 when every service answers,
1 otherwise, so it can gate a CI step later.

    python -m stand.healthcheck
"""

import sys

import httpx

SERVICES = (
    ("backend", "http://127.0.0.1:8001"),
    ("assistant", "http://127.0.0.1:8000"),
)
TIMEOUT_SECONDS = 3.0


def is_up(base_url: str) -> tuple[bool, str]:
    try:
        response = httpx.get(f"{base_url}/health", timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        return False, type(error).__name__
    if response.status_code != httpx.codes.OK:
        return False, f"HTTP {response.status_code}"
    return True, response.json().get("status", "")


def main() -> int:
    failed = 0
    for name, base_url in SERVICES:
        up, detail = is_up(base_url)
        failed += not up
        print(f"{'UP  ' if up else 'DOWN'}  {name:<10} {base_url}  {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
