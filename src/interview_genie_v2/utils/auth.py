import bcrypt

BCRYPT_MAX_BYTES = 72  # bcrypt ignores or rejects anything longer


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode())
    except ValueError:  # malformed stored hash
        return False


# Used to keep login timing the same when the user does not exist
DUMMY_HASH = hash_password("dummy-password")