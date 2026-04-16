#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import base64
from cryptography.fernet import Fernet
from src.config.settings import PAYLOAD_ENCRYPTION_KEY

def _get_cipher():
    try:
        return Fernet(PAYLOAD_ENCRYPTION_KEY.encode('utf-8'))
    except Exception:
        # Fallback to a valid default if the environment variable is messed up
        default_key = b'f8SxB5xMZyCjV2kI4uJ2T0-G9R3gU4L8M-5I0K2oBqc='
        return Fernet(default_key)

_cipher = _get_cipher()

def encrypt_payload(data: dict) -> str:
    """Encrypt a dictionary payload to a base64 encoded Fernet token."""
    json_str = json.dumps(data, ensure_ascii=False)
    encrypted_bytes = _cipher.encrypt(json_str.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_payload(token_str: str) -> dict:
    """Decrypt a Fernet token back to a dictionary payload."""
    decrypted_bytes = _cipher.decrypt(token_str.encode('utf-8'))
    json_str = decrypted_bytes.decode('utf-8')
    return json.loads(json_str)
