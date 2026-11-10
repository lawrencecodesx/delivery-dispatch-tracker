from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# Initialize password hash engine
password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hashes a plain text password using Argon2."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against its stored hash."""
    return password_hash.verify(plain_password, hashed_password)