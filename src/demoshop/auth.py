"""Demo-only authentication smoke layer.

NOT production auth: credentials are plaintext, stored in-memory, and exist
solely to gate the checkout journey in this synthetic demo application.
"""
from dataclasses import dataclass


class AuthError(Exception):
    """Raised when login credentials are invalid or unknown."""


@dataclass(frozen=True)
class AuthSession:
    username: str
    is_authenticated: bool = True


class InMemoryAuthGateway:
    """Deterministic in-memory user store. No network calls."""

    _DEMO_USERS = {
        "alice": "wonderland",
        "bob": "builder",
    }

    def login(self, username: str, password: str) -> AuthSession:
        expected_password = self._DEMO_USERS.get(username)
        if expected_password is None or expected_password != password:
            raise AuthError(f"invalid credentials for user '{username}'")
        return AuthSession(username=username, is_authenticated=True)
