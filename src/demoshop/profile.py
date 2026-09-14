"""In-memory user profile store. Independent of checkout/payments/gateway."""
import re
from dataclasses import dataclass, replace
from typing import Dict, Optional

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ProfileError(Exception):
    """Raised for unknown profiles or invalid profile field values."""


@dataclass(frozen=True)
class Profile:
    username: str
    email: str
    display_name: str


class ProfileStore:
    """Deterministic in-memory profile store. No network calls."""

    def __init__(self) -> None:
        self._profiles: Dict[str, Profile] = {}

    def create(self, username: str, email: str, display_name: str) -> Profile:
        profile = Profile(username=username, email=email, display_name=display_name)
        self._profiles[username] = profile
        return profile

    def get(self, username: str) -> Optional[Profile]:
        return self._profiles.get(username)

    def update(self, username: str, email: Optional[str] = None,
               display_name: Optional[str] = None) -> Profile:
        existing = self._profiles.get(username)
        if existing is None:
            raise ProfileError(f"unknown profile '{username}'")

        if email is not None and not _EMAIL_RE.match(email):
            raise ProfileError(f"invalid email '{email}'")

        updated = replace(
            existing,
            email=email if email is not None else existing.email,
            display_name=display_name if display_name is not None else existing.display_name,
        )
        self._profiles[username] = updated
        return updated
