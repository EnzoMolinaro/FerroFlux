"""
test_usuario_repo.py — Testes de repositories/usuario_repo.py

Execute:
    pytest tests/test_usuario_repo.py -v
    pytest tests/test_usuario_repo.py::TestUsuarioRepoUnitario -v  # sem banco
"""

import pytest
from unittest.mock import MagicMock, patch, call

import repositories.usuario_repo as repo
from repositories.usuario_repo import Usuario, _row_para_usuario, _perfil_id


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def _row(id=1, login="admin", nome="Administrador", perfil="ADM", ativo=1):
    """Tupla que imita pyodbc.Row na ordem do _SELECT_BASE."""
    return (id, login, nome, perfil, ativo)


# ══════════════════════════════════════════════════════
#  TESTES UNITÁRIOS
# ══════════════════════════════════════════════════════

class TestRowParaUsuario:
    """Testa o helper de conversão de linha → Usuario."""

    def test_converte_campos_basicos(self):
        u = _row_para_usuario(_row())
        assert u.id == 1
        assert u.login == "admin"
        assert u.nome_completo == "Administrador"
        assert u.perfil == "ADM"
        assert u.ativo is True

    def test_ativo_false_quando_zero(self):
        u = _row_para_usuario(_row(ativo=0))
        assert u.ativo is False

    def test_ativo_true_quando_um(self):
        u = _row_para_usuario(_row(ativo=1))
        assert u.ativo is True

    def test_row_sem_campo_ativo_assume_true(self):
        """Linha com apenas 4 campos (sem Ativo) → ativo = True."""
        row_curta = (2, "joao", "João Silva", "FUNCIONARIO")
        u = _row_para_usuario(row_curta)
        assert u.ativo is True

    def test_perfil_preservado_como_string(self):
        u = _row_para_usuario(_row(perfil="FUNCIONARIO"))
        assert u.perfil == "FUNCIONARIO"


class TestPerfilId:
    """Testa _perfil_id com conn mockado."""

    def test_retorna_id_quando_perfil_existe(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (3,)

        resultado = _perfil_id(conn, "ADM")
        assert resultado == 3
        cursor.execute.assert_called_once()
        assert "ADM" in cursor.execute.call_args[0][1]

    def test_levanta_value_error_quando_perfil_nao_existe(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="VISITANTE"):
            _perfil_id(conn, "VISITANTE")


class TestBuscarPorLoginESenha:
    """Testa a função buscar_por_login_e_senha com obter_conexao mockada."""

    def test_retorna_usuario_quando_credenciais_corretas(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = _row()

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            resultado = repo.buscar_por_login_e_senha("admin", "abc123hash")

        assert resultado is not None
        assert resultado.login == "admin"
        assert resultado.perfil == "ADM"

    def test_retorna_none_quando_usuario_nao_encontrado(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            resultado = repo.buscar_por_login_e_senha("fantasma", "errada")

        assert resultado is None

    def test_query_inclui_ativo_igual_a_1(self):
        """A query deve filtrar apenas usuários ativos."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.buscar_por_login_e_senha("admin", "hash")

        sql = mock_cursor.execute.call_args[0][0]
        assert "Ativo = 1" in sql


class TestLoginExiste:
    """Testa a função login_existe."""

    def test_retorna_true_quando_login_em_uso(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            assert repo.login_existe("admin") is True

    def test_retorna_false_quando_login_disponivel(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            assert repo.login_existe("novo_usuario") is False

    def test_exceto_id_inclui_clausula_diferente(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.login_existe("admin", exceto_id=5)

        sql = mock_cursor.execute.call_args[0][0]
        assert "IDUsuario <>" in sql


class TestDesativarReativar:
    """Testa desativar() e reativar() com mock."""

    def test_desativar_usa_ativo_zero(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.desativar(7)

        sql = mock_cursor.execute.call_args[0][0]
        assert "Ativo = 0" in sql
        mock_conn.commit.assert_called_once()

    def test_reativar_usa_ativo_um(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.reativar(7)

        sql = mock_cursor.execute.call_args[0][0]
        assert "Ativo = 1" in sql

    def test_redefinir_senha_atualiza_senha_hash(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.redefinir_senha(3, "novo_hash_aqui")

        sql = mock_cursor.execute.call_args[0][0]
        assert "SenhaHash" in sql
        params = mock_cursor.execute.call_args[0][1]
        assert "novo_hash_aqui" in params


class TestCadastrarUsuario:
    """Testa cadastrar() com mock."""

    def _mock_ctx(self, id_perfil=1, id_usuario=10):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        # Primeira chamada: _perfil_id → IDPerfil; segunda: LAST_INSERT_ID
        mock_cursor.fetchone.side_effect = [(id_perfil,), (id_usuario,)]
        return mock_conn, mock_cursor

    def test_cadastrar_faz_commit(self):
        mock_conn, _ = self._mock_ctx()
        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.cadastrar("novouser", "hash123", "Novo Usuario", "FUNCIONARIO")
        mock_conn.commit.assert_called_once()

    def test_cadastrar_insere_em_usuario_e_usuario_perfil(self):
        mock_conn, mock_cursor = self._mock_ctx()
        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.cadastrar("novouser", "hash123", "Novo Usuario", "FUNCIONARIO")

        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        inserts = [s for s in sqls if "INSERT" in s]
        tabelas = " ".join(inserts)
        assert "Usuario" in tabelas
        assert "UsuarioPerfil" in tabelas

    def test_cadastrar_levanta_connexao_error_sem_id(self):
        from database.conexao import ConexaoError
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        # _perfil_id retorna OK, mas LAST_INSERT_ID retorna None
        mock_cursor.fetchone.side_effect = [(1,), None]

        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            with pytest.raises(ConexaoError):
                repo.cadastrar("x", "h", "Nome", "ADM")


class TestAtualizarUsuario:
    """Testa atualizar() com mock."""

    def _mock_ctx(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (2,)  # id_perfil
        return mock_conn, mock_cursor

    def test_atualizar_sem_senha_nao_inclui_senha_hash_no_update(self):
        mock_conn, mock_cursor = self._mock_ctx()
        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.atualizar(1, "admin", "Administrador", "ADM", senha_hash=None)

        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        update_usuario = [s for s in sqls if "UPDATE Usuario" in s]
        assert len(update_usuario) == 1
        assert "SenhaHash" not in update_usuario[0]

    def test_atualizar_com_senha_inclui_senha_hash(self):
        mock_conn, mock_cursor = self._mock_ctx()
        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.atualizar(1, "admin", "Administrador", "ADM", senha_hash="novo_hash")

        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        update_usuario = [s for s in sqls if "UPDATE Usuario" in s]
        assert "SenhaHash" in update_usuario[0]

    def test_atualizar_substitui_perfil(self):
        """Deve DELETE + INSERT em UsuarioPerfil."""
        mock_conn, mock_cursor = self._mock_ctx()
        with patch("repositories.usuario_repo.obter_conexao", return_value=mock_conn):
            repo.atualizar(1, "admin", "Administrador", "FUNCIONARIO")

        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        assert any("DELETE FROM UsuarioPerfil" in s for s in sqls)
        assert any("INSERT INTO UsuarioPerfil" in s for s in sqls)
