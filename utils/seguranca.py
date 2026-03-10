"""
utils/seguranca.py
------------------
Funções de segurança — hash de senha e validações básicas.
"""

from __future__ import annotations

import hashlib
import re


def hash_senha(senha: str) -> str:
    """
    Retorna o SHA-256 da senha em hexadecimal (64 caracteres).
    Compatível com a coluna SenhaHash VARCHAR(64).
    """
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def senha_valida(senha: str) -> tuple[bool, str]:
    """
    Valida os requisitos mínimos de senha.

    Retorna:
        (True, "") se válida
        (False, motivo) se inválida
    """
    if len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres."
    return True, ""


def login_valido(login: str) -> tuple[bool, str]:
    """
    Valida o formato do login — só letras, números e underscore,
    entre 3 e 30 caracteres.

    Retorna:
        (True, "") se válido
        (False, motivo) se inválido
    """
    if not (3 <= len(login) <= 30):
        return False, "O login deve ter entre 3 e 30 caracteres."
    if not re.match(r"^\w+$", login):
        return False, "O login deve conter apenas letras, números e _."
    return True, ""
