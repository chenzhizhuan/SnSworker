#!/usr/bin/env python3
"""Encrypt and decrypt the local Xingchen credential config."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigCryptor:
    """Fernet config cryptor compatible with the reference package."""

    def __init__(self, password: str | None = None):
        self.password = password or os.getenv(
            "OFFLINE_ASR_ENCRYPT_KEY", "default-encrypt-key-change-me"
        )
        self._fernet: Fernet | None = None

    @property
    def fernet(self) -> Fernet:
        if self._fernet is None:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"offline-asr-salt",
                iterations=100000,
                backend=default_backend(),
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt_dict(self, data: dict) -> str:
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        return base64.urlsafe_b64encode(self.fernet.encrypt(raw)).decode("utf-8")

    def decrypt_dict(self, encrypted: str) -> dict:
        token = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
        raw = self.fernet.decrypt(token)
        return json.loads(raw.decode("utf-8"))

    def decrypt_file_to_dict(self, input_path: str | Path) -> dict:
        encrypted = Path(input_path).read_text(encoding="utf-8").strip()
        return self.decrypt_dict(encrypted)
