from cryptography.fernet import Fernet
import json
import os


def get_fernet():
    key = os.environ.get("FERNET_KEY")
    if not key:
        raise ValueError("FERNET_KEY environment variable not set")
    return Fernet(key.encode())


def encrypt_token(token_dict: dict) -> str:
    f = get_fernet()
    json_str = json.dumps(token_dict)
    encrypted = f.encrypt(json_str.encode())
    return encrypted.decode()


def decrypt_token(ciphertext: str) -> dict:
    f = get_fernet()
    decrypted = f.decrypt(ciphertext.encode())
    return json.loads(decrypted.decode())
