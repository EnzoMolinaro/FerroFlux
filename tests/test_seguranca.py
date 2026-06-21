"""
test_seguranca.py — Testes de utils/seguranca.py
Estes testes são 100% unitários, não precisam do banco.

Execute:
    pytest tests/test_seguranca.py -v
"""

import pytest
from utils.seguranca import hash_senha, senha_valida, login_valido


class TestHashSenha:
    """Testes da função hash_senha (SHA-256)."""

    def test_retorna_string_de_64_chars(self):
        """SHA-256 em hex sempre tem 64 caracteres."""
        resultado = hash_senha("minhasenha")
        assert len(resultado) == 64

    def test_hash_e_deterministico(self):
        """A mesma senha sempre gera o mesmo hash."""
        assert hash_senha("Admin@123") == hash_senha("Admin@123")

    def test_senhas_diferentes_geram_hashes_diferentes(self):
        """Senhas distintas nunca devem colidir."""
        assert hash_senha("senha1") != hash_senha("senha2")

    def test_hash_nao_e_texto_puro(self):
        """O hash jamais deve ser igual à senha original."""
        senha = "ferroflux"
        assert hash_senha(senha) != senha

    def test_hash_conhecido(self):
        """Verifca valor SHA-256 esperado para uma string fixa."""
        # echo -n "abc" | sha256sum → ba7816bf...
        assert hash_senha("abc").startswith("ba7816bf")

    def test_senha_vazia_tem_hash(self):
        """Até senha vazia tem hash definido (SHA-256 de string vazia)."""
        resultado = hash_senha("")
        assert len(resultado) == 64

    def test_caracteres_especiais_nao_quebram(self):
        """Senhas com acentos e símbolos devem funcionar."""
        resultado = hash_senha("São@Paulo#2025!")
        assert len(resultado) == 64


class TestSenhaValida:
    """Testes da função senha_valida."""

    def test_senha_valida_6_chars(self):
        ok, msg = senha_valida("abc123")
        assert ok is True
        assert msg == ""

    def test_senha_valida_longa(self):
        ok, msg = senha_valida("SenhaForte@2025!")
        assert ok is True

    def test_senha_curta_invalida(self):
        ok, msg = senha_valida("abc")
        assert ok is False
        assert "6" in msg  # menciona o mínimo exigido

    def test_senha_vazia_invalida(self):
        ok, msg = senha_valida("")
        assert ok is False

    def test_senha_5_chars_invalida(self):
        """Limite inferior: 5 caracteres não deve passar."""
        ok, msg = senha_valida("12345")
        assert ok is False

    def test_senha_exatamente_6_chars_valida(self):
        """6 é o mínimo aceito."""
        ok, msg = senha_valida("123456")
        assert ok is True


class TestLoginValido:
    """Testes da função login_valido."""

    def test_login_simples_valido(self):
        ok, msg = login_valido("admin")
        assert ok is True
        assert msg == ""

    def test_login_com_underscore_valido(self):
        ok, msg = login_valido("joao_silva")
        assert ok is True

    def test_login_com_numeros_valido(self):
        ok, msg = login_valido("user123")
        assert ok is True

    def test_login_muito_curto(self):
        ok, msg = login_valido("ab")
        assert ok is False
        assert "3" in msg

    def test_login_muito_longo(self):
        ok, msg = login_valido("a" * 31)
        assert ok is False
        assert "30" in msg

    def test_login_exatamente_3_chars_valido(self):
        ok, msg = login_valido("adm")
        assert ok is True

    def test_login_exatamente_30_chars_valido(self):
        ok, msg = login_valido("a" * 30)
        assert ok is True

    def test_login_com_espaco_invalido(self):
        ok, msg = login_valido("joao silva")
        assert ok is False

    def test_login_com_arroba_invalido(self):
        ok, msg = login_valido("joao@silva")
        assert ok is False

    def test_login_com_hifen_invalido(self):
        """Hífen não é permitido (só \w = letras, números, _)."""
        ok, msg = login_valido("joao-silva")
        assert ok is False

    def test_login_vazio_invalido(self):
        ok, msg = login_valido("")
        assert ok is False
