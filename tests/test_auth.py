"""T01 - login mandatory.

Demo-only auth smoke coverage. This is explicitly NOT production auth:
passwords are compared in plaintext against an in-memory user store for
the sole purpose of gating the checkout journey in this synthetic app.
"""
import pytest

from demoshop.auth import AuthError, AuthSession, InMemoryAuthGateway


def test_login_with_valid_credentials_returns_session():
    gateway = InMemoryAuthGateway()

    session = gateway.login("alice", "wonderland")

    assert isinstance(session, AuthSession)
    assert session.username == "alice"
    assert session.is_authenticated is True


def test_login_with_invalid_password_raises_auth_error():
    gateway = InMemoryAuthGateway()

    with pytest.raises(AuthError):
        gateway.login("alice", "wrong-password")


def test_login_with_unknown_user_raises_auth_error():
    gateway = InMemoryAuthGateway()

    with pytest.raises(AuthError):
        gateway.login("nobody", "wonderland")


def test_checkout_requires_authenticated_session():
    from demoshop.checkout import CheckoutError, require_authenticated

    with pytest.raises(CheckoutError):
        require_authenticated(None)


def test_checkout_accepts_authenticated_session():
    from demoshop.checkout import require_authenticated

    gateway = InMemoryAuthGateway()
    session = gateway.login("alice", "wonderland")

    # Should not raise.
    require_authenticated(session)
