"""T08 - profile edit (independent of the checkout->payments->gateway chain)."""
import pytest

from demoshop.profile import ProfileError, ProfileStore


def test_update_profile_changes_email():
    store = ProfileStore()
    store.create("alice", email="alice@example.com", display_name="Alice")

    updated = store.update("alice", email="alice.new@example.com")

    assert updated.email == "alice.new@example.com"
    assert updated.display_name == "Alice"


def test_update_profile_rejects_invalid_email():
    store = ProfileStore()
    store.create("alice", email="alice@example.com", display_name="Alice")

    with pytest.raises(ProfileError):
        store.update("alice", email="not-an-email")


def test_update_unknown_profile_raises():
    store = ProfileStore()

    with pytest.raises(ProfileError):
        store.update("nobody", email="a@b.com")
