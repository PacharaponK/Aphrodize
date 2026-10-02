import base64
import hashlib
import hmac
import secrets

_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return (
        f"pbkdf2_sha256${_ITERATIONS}${base64.b64encode(salt).decode()}$"
        f"{base64.b64encode(derived_key).decode()}"
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_key = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(encoded_salt)
        expected = base64.b64decode(encoded_key)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(derived, expected)
