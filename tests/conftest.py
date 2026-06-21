"""
conftest.py — Fixtures compartilhadas para todos os testes.
Adaptado para FerroFlux: pyodbc + MySQL ODBC Driver.
"""

import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────
#  CONFIGURAÇÃO DO BANCO DE TESTES
#  Crie um banco separado: ferroflux_test
# ─────────────────────────────────────────────
from database.conexao import ConfigConexao

CONFIG_TESTE = ConfigConexao(
    servidor="localhost",
    porta=3307,
    usuario="root",
    senha="",              # ajuste se necessário
    banco="ferroflux_test",
)


# ── Conexão real ao banco de testes ──────────
@pytest.fixture(scope="session")
def db_connection():
    """
    Conexão real ao banco ferroflux_test.
    Escopo 'session': aberta uma vez, reutilizada em todos os testes.
    """
    import pyodbc
    from database.conexao import _detectar_driver, _montar_string_conexao

    driver = _detectar_driver()
    conn = pyodbc.connect(_montar_string_conexao(CONFIG_TESTE, driver), timeout=5)
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture
def db_cursor(db_connection):
    """Cursor com rollback automático — testes não poluem o banco."""
    cursor = db_connection.cursor()
    yield cursor
    db_connection.rollback()
    cursor.close()


# ── Conexão mockada (sem banco real) ─────────
@pytest.fixture
def mock_conn():
    """
    Mock de pyodbc.Connection.
    Para testes unitários que não devem tocar o banco.
    """
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── Dados de exemplo ─────────────────────────
@pytest.fixture
def usuario_adm():
    from repositories.usuario_repo import Usuario
    return Usuario(id=1, login="admin", nome_completo="Administrador",
                   perfil="ADM", ativo=True)

@pytest.fixture
def usuario_funcionario():
    from repositories.usuario_repo import Usuario
    return Usuario(id=2, login="joao", nome_completo="João Silva",
                   perfil="FUNCIONARIO", ativo=True)

@pytest.fixture
def material_exemplo():
    from repositories.material_repo import Material
    return Material(
        nome="Chapa de Aço",
        unidade="KG",
        descricao="Chapa laminada",
        preco_custo=15.00,
        preco_venda=22.50,
        estoque_atual=100.0,
        estoque_minimo=10.0,
        localizacao="Galpão A",
    )
