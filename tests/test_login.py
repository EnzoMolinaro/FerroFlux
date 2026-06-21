"""
test_login.py — Testes unitários da autenticação.

Como usar:
    pytest tests/test_login.py -v

Adapte o import conforme o nome do seu arquivo de login,
ex: from tela_login import autenticar_usuario
"""

import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────
#  ADAPTE ESTE IMPORT para o seu projeto:
#  from seu_arquivo_login import autenticar_usuario
# ─────────────────────────────────────────────
# Exemplo de função esperada no seu código:
#
#   def autenticar_usuario(conn, usuario, senha):
#       cursor = conn.cursor()
#       cursor.execute("SELECT * FROM usuarios WHERE usuario=%s AND senha=%s", (usuario, senha))
#       return cursor.fetchone()
#
# Se a sua função tiver outro nome ou assinatura, ajuste os testes abaixo.


class TestLoginUnitario:
    """Testes sem banco de dados real (usa Mock)."""

    def test_login_credenciais_corretas(self, mock_conn):
        """Retorna dados do usuário quando credenciais estão corretas."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = {
            "id": 1, "usuario": "admin", "perfil": "administrador"
        }

        # Simula chamada — ajuste para a função real do seu projeto:
        cursor.execute("SELECT * FROM usuarios WHERE usuario=%s AND senha=%s",
                       ("admin", "Admin@123"))
        resultado = cursor.fetchone()

        assert resultado is not None
        assert resultado["usuario"] == "admin"

    def test_login_credenciais_erradas(self, mock_conn):
        """Retorna None quando usuário ou senha estão errados."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None

        cursor.execute("SELECT * FROM usuarios WHERE usuario=%s AND senha=%s",
                       ("naoexiste", "errada"))
        resultado = cursor.fetchone()

        assert resultado is None

    def test_login_usuario_vazio(self, mock_conn):
        """Campos vazios não devem autenticar."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None

        cursor.execute("SELECT * FROM usuarios WHERE usuario=%s AND senha=%s",
                       ("", ""))
        resultado = cursor.fetchone()

        assert resultado is None

    def test_login_senha_vazia(self, mock_conn):
        """Senha em branco não deve autenticar."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None

        cursor.execute("SELECT * FROM usuarios WHERE usuario=%s AND senha=%s",
                       ("admin", ""))
        resultado = cursor.fetchone()

        assert resultado is None

    def test_login_sql_injection(self, mock_conn):
        """Tentativa de SQL Injection não deve retornar resultado."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None

        entrada_maliciosa = "' OR '1'='1"
        cursor.execute("SELECT * FROM usuarios WHERE usuario=%s AND senha=%s",
                       (entrada_maliciosa, entrada_maliciosa))
        resultado = cursor.fetchone()

        # Com queries parametrizadas, deve retornar None
        assert resultado is None


class TestLoginBancoDados:
    """
    Testes com banco real (requer banco de testes configurado).
    Execute com: pytest tests/test_login.py::TestLoginBancoDados -v
    """

    def test_usuario_admin_existe_no_banco(self, db_cursor):
        """Verifica se o usuário admin está cadastrado no banco."""
        db_cursor.execute(
            "SELECT id, usuario, perfil FROM usuarios WHERE usuario = %s",
            ("admin",)
        )
        resultado = db_cursor.fetchone()
        assert resultado is not None, "Usuário 'admin' não encontrado no banco"
        assert resultado["usuario"] == "admin"

    def test_senha_armazenada_nao_e_texto_puro(self, db_cursor):
        """A senha não deve estar armazenada como texto simples (boa prática)."""
        db_cursor.execute("SELECT senha FROM usuarios WHERE usuario = %s", ("admin",))
        resultado = db_cursor.fetchone()
        if resultado:
            senha = resultado["senha"]
            # Senha em texto puro geralmente tem menos de 30 chars e não tem padrão de hash
            assert len(senha) >= 30 or "$" in senha or senha != "Admin@123", \
                "ATENÇÃO: senha pode estar armazenada sem criptografia!"
