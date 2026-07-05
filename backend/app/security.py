"""Gemeinsame Passwort-Hilfen (Argon2).

Wird für Lehrer- und Schüler-Passwörter genutzt. Passwörter werden ausschließlich
als Argon2-Hash gespeichert und sind nicht rückrechenbar – auch der Admin kann
sie nicht einsehen.
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

_ph = PasswordHasher()

# Mindestlänge für Schüler-Passwörter (bewusst niedrig gehalten).
MIN_PASSWORD_LENGTH = 4


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False
