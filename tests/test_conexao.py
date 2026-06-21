"""
test_conexao.py — Testes de database/conexao.py

100% unitários (sem banco real) — testam a lógica de
montar string de conexão, configurar e detectar erros.

Execute:
    pytest tests/test_conexao.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

from database.conexao import (
    ConfigConexao,
    ConexaoError,
    DriverNaoEncontradoError,
    _montar_string_conexao,
    configurar,
    testar_conexao,
)


class TestConfigConexao:
    """Testes do dataclass ConfigConexao."""

    def test_str_mostra_usuario_servidor_porta_banco(self):
        cfg = ConfigConexao("localhost", 3307, "root", "senha123", "ferroflux")
        resultado = str(cfg)
        assert "root" in resultado
        assert "localhost" in resultado
        assert "3307" in resultado
        assert "ferroflux" in resultado

    def test_str_nao_exibe_senha(self):
        """A representação textual NÃO deve expor a senha."""
        cfg = ConfigConexao("localhost", 3307, "root", "senha_secreta", "ferroflux")
        assert "senha_secreta" not in str(cfg)

    def test_config_padrao_porta_3307(self):
        """Porta padrão do projeto é 3307."""
        from database.conexao import _Estado
        assert _Estado.config.porta == 3307

    def test_config_padrao_banco_ferroflux(self):
        from database.conexao import _Estado
        assert _Estado.config.banco == "ferroflux"


class TestMontarStringConexao:
    """Testa a montagem da connection string ODBC."""

    def _cfg(self):
        return ConfigConexao("localhost", 3307, "root", "senha", "ferroflux")

    def test_contem_driver(self):
        s = _montar_string_conexao(self._cfg(), "MySQL ODBC 8.0 Unicode Driver")
        assert "DRIVER={MySQL ODBC 8.0 Unicode Driver}" in s

    def test_contem_servidor(self):
        s = _montar_string_conexao(self._cfg(), "MySQL ODBC 8.0 Unicode Driver")
        assert "SERVER=localhost" in s

    def test_contem_porta(self):
        s = _montar_string_conexao(self._cfg(), "MySQL ODBC 8.0 Unicode Driver")
        assert "PORT=3307" in s

    def test_contem_banco(self):
        s = _montar_string_conexao(self._cfg(), "MySQL ODBC 8.0 Unicode Driver")
        assert "DATABASE=ferroflux" in s

    def test_contem_usuario(self):
        s = _montar_string_conexao(self._cfg(), "MySQL ODBC 8.0 Unicode Driver")
        assert "UID=root" in s

    def test_contem_charset_utf8mb4(self):
        s = _montar_string_conexao(self._cfg(), "MySQL ODBC 8.0 Unicode Driver")
        assert "utf8mb4" in s


class TestConfigurar:
    """Testes da função configurar()."""

    def test_configurar_muda_estado(self):
        from database.conexao import _Estado
        nova = ConfigConexao("servidor2", 3306, "user2", "pass2", "outro_banco")
        configurar(nova)
        assert _Estado.config.servidor == "servidor2"
        assert _Estado.config.banco == "outro_banco"
        # Restaura padrão para não afetar outros testes
        configurar(ConfigConexao("localhost", 3307, "root", "", "ferroflux"))


class TestDetectarDriver:
    """Testes de _detectar_driver()."""

    def test_levanta_erro_se_pyodbc_nao_instalado(self):
        import sys
        from database.conexao import DriverNaoEncontradoError
        with patch.dict(sys.modules, {"pyodbc": None}):
            from database import conexao
            conexao._Estado.driver_cache = None
            # Reimporta para forçar ImportError
            import importlib
            with pytest.raises(Exception):
                importlib.reload(conexao)

    def test_levanta_erro_se_nenhum_driver_encontrado(self):
        from database.conexao import _detectar_driver, _Estado
        _Estado.driver_cache = None

        mock_pyodbc = MagicMock()
        mock_pyodbc.drivers.return_value = []  # nenhum driver disponível

        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            with pytest.raises(DriverNaoEncontradoError):
                _detectar_driver()

    def test_usa_cache_na_segunda_chamada(self):
        from database.conexao import _detectar_driver, _Estado
        _Estado.driver_cache = "MySQL ODBC 8.0 Unicode Driver"

        resultado = _detectar_driver()
        assert resultado == "MySQL ODBC 8.0 Unicode Driver"
        # Restaura
        _Estado.driver_cache = None


class TestTestarConexao:
    """Testa a função testar_conexao() com mocks."""

    def test_retorna_false_sem_driver(self):
        from database.conexao import _Estado
        _Estado.driver_cache = None

        mock_pyodbc = MagicMock()
        mock_pyodbc.drivers.return_value = []

        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            ok, msg = testar_conexao(
                ConfigConexao("localhost", 3307, "root", "", "ferroflux")
            )
        assert ok is False
        assert len(msg) > 0

    def test_retorna_true_com_conexao_mockada(self):
        from database.conexao import _Estado
        _Estado.driver_cache = "MySQL ODBC 8.0 Unicode Driver"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("8.0.35",)
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc = MagicMock()
        mock_pyodbc.drivers.return_value = ["MySQL ODBC 8.0 Unicode Driver"]
        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            ok, msg = testar_conexao(
                ConfigConexao("localhost", 3307, "root", "", "ferroflux")
            )
        assert ok is True
        assert "8.0.35" in msg
        _Estado.driver_cache = None
