"""敏感字段落库加密（Fernet）。

密钥来自环境变量 FIELD_ENCRYPTION_KEY；未配置时自动生成并落到
backend/.local_key（gitignore），保证本地零配置可跑，但不进版本库。
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from app.core.config import BASE_DIR, settings

_KEY_FILE = BASE_DIR / ".local_key"


def _get_fernet() -> Fernet:
    key = settings.field_encryption_key.strip()
    if not key:
        if _KEY_FILE.exists():
            key = _KEY_FILE.read_text(encoding="utf-8").strip()
        else:
            key = Fernet.generate_key().decode()
            _KEY_FILE.write_text(key, encoding="utf-8")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plain: str | float | int | None) -> str | None:
    if plain is None:
        return None
    return _get_fernet().encrypt(str(plain).encode()).decode()


def decrypt(token: str | None) -> str | None:
    """解密失败返回 None 而非抛异常——避免脏数据导致整个列表接口500。"""
    if not token:
        return None
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def decrypt_float(token: str | None) -> float | None:
    raw = decrypt(token)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None