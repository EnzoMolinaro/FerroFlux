"""
test_material_repo.py — Testes do MaterialRepo (repositories/material_repo.py)

Dois grupos:
  - TestMaterialRepoUnitario  → usa Mock de pyodbc, sem banco real
  - TestMaterialRepoBanco     → usa banco ferroflux_test real

Execute:
    pytest tests/test_material_repo.py -v
    pytest tests/test_material_repo.py::TestMaterialRepoUnitario -v   # só unitários
"""

import pytest
from unittest.mock import MagicMock, call, patch

from repositories.material_repo import Material, MaterialRepo


# ══════════════════════════════════════════════════════
#  TESTES UNITÁRIOS (sem banco real)
# ══════════════════════════════════════════════════════

class TestMaterialRepoUnitario:

    # ── Construção do repositório ─────────────────────

    def test_repo_instanciado_com_conn(self, mock_conn):
        conn, _ = mock_conn
        repo = MaterialRepo(conn)
        assert repo._conn is conn

    # ── listar_todos ──────────────────────────────────

    def test_listar_todos_retorna_lista_de_materiais(self, mock_conn):
        conn, cursor = mock_conn
        # Simula 2 linhas retornadas pelo banco
        cursor.fetchall.return_value = [
            _row_fake(id=1, nome="Chapa de Aço", estoque=50.0, preco_venda=22.5),
            _row_fake(id=2, nome="Cobre",        estoque=10.0, preco_venda=45.0),
        ]
        repo = MaterialRepo(conn)
        resultado = repo.listar_todos()

        assert len(resultado) == 2
        assert resultado[0].nome == "Chapa de Aço"
        assert resultado[1].nome == "Cobre"

    def test_listar_todos_vazio(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = MaterialRepo(conn)
        assert repo.listar_todos() == []

    def test_listar_todos_apenas_ativos_usa_filtro(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = MaterialRepo(conn)
        repo.listar_todos(apenas_ativos=True)

        sql_chamado = cursor.execute.call_args[0][0]
        assert "Ativo = TRUE" in sql_chamado

    def test_listar_todos_sem_filtro_ativo(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = MaterialRepo(conn)
        repo.listar_todos(apenas_ativos=False)

        sql_chamado = cursor.execute.call_args[0][0]
        assert "Ativo" not in sql_chamado

    # ── buscar_por_id ─────────────────────────────────

    def test_buscar_por_id_encontrado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = _row_fake(id=5, nome="Alumínio")
        repo = MaterialRepo(conn)
        resultado = repo.buscar_por_id(5)

        assert resultado is not None
        assert resultado.id == 5
        assert resultado.nome == "Alumínio"

    def test_buscar_por_id_nao_encontrado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = MaterialRepo(conn)
        resultado = repo.buscar_por_id(999)
        assert resultado is None

    # ── buscar_por_nome ───────────────────────────────

    def test_buscar_por_nome_usa_like(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = MaterialRepo(conn)
        repo.buscar_por_nome("ferro")

        args = cursor.execute.call_args[0]
        assert "%ferro%" in args[1]  # parâmetro do LIKE

    # ── codigo_barras_existe ──────────────────────────

    def test_codigo_barras_existe_true(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (1,)  # encontrou
        repo = MaterialRepo(conn)
        assert repo.codigo_barras_existe("7894900011517") is True

    def test_codigo_barras_existe_false(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = MaterialRepo(conn)
        assert repo.codigo_barras_existe("7894900011517") is False

    def test_codigo_barras_existe_ignora_proprio_id(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = MaterialRepo(conn)
        repo.codigo_barras_existe("7894900011517", ignorar_id=3)

        sql = cursor.execute.call_args[0][0]
        assert "IDProduto <>" in sql

    # ── inserir ───────────────────────────────────────

    def test_inserir_executa_tres_inserts(self, mock_conn, material_exemplo):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (42,)  # LAST_INSERT_ID
        repo = MaterialRepo(conn)
        id_retornado = repo.inserir(material_exemplo)

        assert id_retornado == 42
        assert material_exemplo.id == 42
        assert cursor.execute.call_count == 4  # 3 INSERTs + 1 LAST_INSERT_ID
        conn.commit.assert_called_once()

    def test_inserir_falha_sem_id_retornado(self, mock_conn, material_exemplo):
        from database.conexao import ConexaoError
        conn, cursor = mock_conn
        # Simula: execute INSERT ok, mas LAST_INSERT_ID retorna None
        cursor.fetchone.return_value = None
        repo = MaterialRepo(conn)

        with pytest.raises(ConexaoError):
            repo.inserir(material_exemplo)
        conn.rollback.assert_called_once()

    # ── atualizar ─────────────────────────────────────

    def test_atualizar_sem_id_levanta_value_error(self, mock_conn):
        conn, cursor = mock_conn
        repo = MaterialRepo(conn)
        material_sem_id = Material(nome="Teste", preco_venda=10.0)

        with pytest.raises(ValueError, match="sem ID"):
            repo.atualizar(material_sem_id)

    def test_atualizar_sem_mudanca_preco_nao_insere_historico(self, mock_conn, material_exemplo):
        conn, cursor = mock_conn
        material_exemplo.id = 1
        # Simula preço igual ao que já está no banco
        cursor.fetchone.return_value = (
            material_exemplo.preco_custo,
            material_exemplo.preco_venda,
        )
        repo = MaterialRepo(conn)
        repo.atualizar(material_exemplo)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        inserts_historico = [s for s in sqls if "INSERT INTO HistoricoPrecos" in s]
        assert len(inserts_historico) == 0

    def test_atualizar_com_mudanca_preco_insere_historico(self, mock_conn, material_exemplo):
        conn, cursor = mock_conn
        material_exemplo.id = 1
        material_exemplo.preco_venda = 99.99
        # Simula preço diferente no banco
        cursor.fetchone.return_value = (material_exemplo.preco_custo, 22.50)
        repo = MaterialRepo(conn)
        repo.atualizar(material_exemplo)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        inserts_historico = [s for s in sqls if "INSERT INTO HistoricoPrecos" in s]
        assert len(inserts_historico) == 1

    # ── desativar / reativar ──────────────────────────

    def test_desativar_usa_ativo_false(self, mock_conn):
        conn, cursor = mock_conn
        repo = MaterialRepo(conn)
        repo.desativar(7)

        sql = cursor.execute.call_args[0][0]
        assert "Ativo = FALSE" in sql
        conn.commit.assert_called_once()

    def test_reativar_usa_ativo_true(self, mock_conn):
        conn, cursor = mock_conn
        repo = MaterialRepo(conn)
        repo.reativar(7)

        sql = cursor.execute.call_args[0][0]
        assert "Ativo = TRUE" in sql
        conn.commit.assert_called_once()

    # ── ajustar_estoque ───────────────────────────────

    def test_ajustar_estoque_insere_movimentacao(self, mock_conn):
        conn, cursor = mock_conn
        repo = MaterialRepo(conn)
        repo.ajustar_estoque(id_produto=1, quantidade=25.0,
                             observacao="Compra NF-123", id_usuario=1)

        sql = cursor.execute.call_args[0][0]
        assert "MovimentacaoEstoque" in sql
        assert "AJUSTE" in sql
        conn.commit.assert_called_once()

    def test_ajustar_estoque_usa_abs_para_negativos(self, mock_conn):
        """Quantidade negativa deve ser armazenada como ABS()."""
        conn, cursor = mock_conn
        repo = MaterialRepo(conn)
        repo.ajustar_estoque(id_produto=1, quantidade=-10.0)

        params = cursor.execute.call_args[0][1]
        # params: (id_produto, abs(quantidade), id_usuario, observacao)
        assert params[1] == 10.0  # abs(-10.0)


# ══════════════════════════════════════════════════════
#  TESTES COM BANCO REAL  (ferroflux_test)
# ══════════════════════════════════════════════════════

class TestMaterialRepoBanco:

    def test_tabela_produtobase_existe(self, db_cursor):
        db_cursor.execute("SHOW TABLES LIKE 'ProdutoBase'")
        assert db_cursor.fetchone() is not None, "Tabela 'ProdutoBase' não encontrada"

    def test_tabela_estoque_existe(self, db_cursor):
        db_cursor.execute("SHOW TABLES LIKE 'Estoque'")
        assert db_cursor.fetchone() is not None, "Tabela 'Estoque' não encontrada"

    def test_tabela_historico_precos_existe(self, db_cursor):
        db_cursor.execute("SHOW TABLES LIKE 'HistoricoPrecos'")
        assert db_cursor.fetchone() is not None, "Tabela 'HistoricoPrecos' não encontrada"

    def test_inserir_e_buscar_material(self, db_connection, material_exemplo):
        repo = MaterialRepo(db_connection)
        id_criado = repo.inserir(material_exemplo)

        encontrado = repo.buscar_por_id(id_criado)
        assert encontrado is not None
        assert encontrado.nome == material_exemplo.nome
        assert encontrado.preco_venda == material_exemplo.preco_venda
        db_connection.rollback()

    def test_listar_retorna_material_inserido(self, db_connection, material_exemplo):
        repo = MaterialRepo(db_connection)
        repo.inserir(material_exemplo)

        todos = repo.listar_todos()
        nomes = [m.nome for m in todos]
        assert material_exemplo.nome in nomes
        db_connection.rollback()

    def test_buscar_por_nome_encontra_inserido(self, db_connection, material_exemplo):
        repo = MaterialRepo(db_connection)
        repo.inserir(material_exemplo)

        resultados = repo.buscar_por_nome("Chapa")
        assert any(m.nome == material_exemplo.nome for m in resultados)
        db_connection.rollback()

    def test_desativar_remove_de_lista_ativos(self, db_connection, material_exemplo):
        repo = MaterialRepo(db_connection)
        id_criado = repo.inserir(material_exemplo)
        repo.desativar(id_criado)

        ativos = repo.listar_todos(apenas_ativos=True)
        ids_ativos = [m.id for m in ativos]
        assert id_criado not in ids_ativos
        db_connection.rollback()

    def test_reativar_aparece_na_lista_ativos(self, db_connection, material_exemplo):
        repo = MaterialRepo(db_connection)
        id_criado = repo.inserir(material_exemplo)
        repo.desativar(id_criado)
        repo.reativar(id_criado)

        ativos = repo.listar_todos(apenas_ativos=True)
        ids_ativos = [m.id for m in ativos]
        assert id_criado in ids_ativos
        db_connection.rollback()


# ══════════════════════════════════════════════════════
#  HELPER — cria uma Row fake compatível com _row_para_material
# ══════════════════════════════════════════════════════

def _row_fake(
    id=1, nome="Ferro", descricao="", codigo_barras=None,
    unidade="KG", ativo=True, data_criacao=None,
    estoque=0.0, estoque_minimo=0.0, localizacao="",
    preco_custo=0.0, preco_venda=0.0,
):
    """Cria uma tupla que imita pyodbc.Row na ordem esperada por _row_para_material."""
    return (
        id, nome, descricao, codigo_barras, unidade, ativo, data_criacao,
        estoque, estoque_minimo, localizacao, preco_custo, preco_venda,
    )
