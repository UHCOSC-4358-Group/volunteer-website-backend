"""
How Auth is going to work:
Begins when user logins in with email and password
They'll hit a different route depending on whether admin or vol, giving us context
We'll use different db statements based on that
Website hits our route. First, we grab the user data from db, including hashed password
If user doesn't exist, then we reject
We check hashed vs input with bcrypt, if not correct, reject
If pass, then we return a token with user's data
Should we handle refreshing? idk
"""

from bcrypt import hashpw, gensalt, checkpw

SALT_ROUNDS = 12


# Hashes password by turning into bytes, salting it, then hashing
def hash_password(plain_pw: str) -> str:
    bytes_pw = plain_pw.encode("utf-8")
    salt = gensalt(SALT_ROUNDS)
    hashed_pw = hashpw(bytes_pw, salt).decode("utf-8")  # Hashes and turns to string
    return hashed_pw


def verify_password(plaintext_pw: str, hashed_pw: str) -> bool:
    return checkpw(plaintext_pw.encode("utf-8"), hashed_pw.encode("utf-8"))
