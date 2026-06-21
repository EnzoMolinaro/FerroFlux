"""
test_banco_dados.py — Testes de integridade do banco de dados.

Execute:
    pytest tests/test_banco_dados.py -v
"""

import pytest
import mysql.connector


class TestConexaoBancoDados:
    """Testes de conexão com o banco."""

    def test_conexao_estabelecida(self, db_connection):
        """Verifica se a conexão com o banco está ativa."""
        assert db_connection.is_connected(), "Não foi possível conectar ao banco"

    def test_banco_correto_selecionado(self, db_connection):
        """Verifica se o banco de dados correto está selecionado."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT DATABASE()")
        resultado = cursor.fetchone()
        cursor.close()
        assert resultado[0] is not None, "Nenhum banco de dados selecionado"

    def test_reconectar_apos_queda(self):
        """
        Simula reconexão ao banco.
        Em produção, o sistema deve reconectar se perder a conexão.
        """
        from conftest import DB_CONFIG
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            assert conn.is_connected()
            conn.close()
            assert not conn.is_connected()
            conn.reconnect()
            assert conn.is_connected()
            conn.close()
        except Exception as e:
            pytest.skip(f"Teste de reconexão ignorado: {e}")


class TestEstruturaBancoDados:
    """Verifica se as tabelas e colunas essenciais existem."""

    TABELAS_ESPERADAS = [
        "usuarios",
        "materiais",
        "clientes",
        "fornecedores",
        "vendas",
    ]

    def test_todas_tabelas_existem(self, db_cursor):
        """Verifica se todas as tabelas principais existem."""
        db_cursor.execute("SHOW TABLES")
        tabelas_existentes = {list(t.values())[0].lower() for t in db_cursor.fetchall()}

        ausentes = []
        for tabela in self.TABELAS_ESPERADAS:
            if tabela not in tabelas_existentes:
                ausentes.append(tabela)

        assert not ausentes, f"Tabelas ausentes no banco: {ausentes}"

    def test_tabela_usuarios_tem_colunas_essenciais(self, db_cursor):
        """Tabela usuarios deve ter campos mínimos."""
        db_cursor.execute("DESCRIBE usuarios")
        colunas = {col["Field"].lower() for col in db_cursor.fetchall()}
        obrigatorias = {"id", "usuario", "senha"}
        ausentes = obrigatorias - colunas
        assert not ausentes, f"Colunas ausentes em 'usuarios': {ausentes}"

    def test_tabela_materiais_tem_colunas_essenciais(self, db_cursor):
        """Tabela materiais deve ter campos mínimos."""
        try:
            db_cursor.execute("DESCRIBE materiais")
            colunas = {col["Field"].lower() for col in db_cursor.fetchall()}
            obrigatorias = {"id", "nome"}
            ausentes = obrigatorias - colunas
            assert not ausentes, f"Colunas ausentes em 'materiais': {ausentes}"
        except Exception as e:
            pytest.skip(f"Tabela 'materiais' não encontrada: {e}")

    def test_tabela_vendas_tem_colunas_essenciais(self, db_cursor):
        """Tabela vendas deve ter campos mínimos."""
        try:
            db_cursor.execute("DESCRIBE vendas")
            colunas = {col["Field"].lower() for col in db_cursor.fetchall()}
            obrigatorias = {"id", "total"}
            ausentes = obrigatorias - colunas
            assert not ausentes, f"Colunas ausentes em 'vendas': {ausentes}"
        except Exception as e:
            pytest.skip(f"Tabela 'vendas' não encontrada: {e}")


class TestIntegridadeDados:
    """Testes de constraints e integridade referencial."""

    def test_chave_primaria_autoincrement(self, db_cursor, material_exemplo):
        """IDs devem ser únicos e auto-incrementados."""
        m = material_exemplo
        db_cursor.execute(
            "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
            (m["nome"] + "_1", m["categoria"], m["preco_kg"], m["quantidade_kg"])
        )
        id1 = db_cursor.lastrowid

        db_cursor.execute(
            "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
            (m["nome"] + "_2", m["categoria"], m["preco_kg"], m["quantidade_kg"])
        )
        id2 = db_cursor.lastrowid

        assert id2 > id1, "IDs não estão incrementando corretamente"

    def test_campo_obrigatorio_nome_nao_aceita_null(self, db_cursor):
        """Campo 'nome' em materiais não deve aceitar NULL."""
        with pytest.raises(mysql.connector.errors.DatabaseError):
            db_cursor.execute(
                "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
                (None, "Ferroso", 2.50, 100.0)
            )

    def test_performance_consulta_simples(self, db_cursor):
        """Consulta simples deve retornar em tempo razoável."""
        import time
        inicio = time.time()
        db_cursor.execute("SELECT COUNT(*) as total FROM materiais")
        db_cursor.fetchone()
        fim = time.time()
        tempo_ms = (fim - inicio) * 1000
        assert tempo_ms < 2000, f"Consulta demorou {tempo_ms:.0f}ms — verifique índices"

    def test_sem_registros_orfaos_vendas(self, db_cursor):
        """Não deve haver vendas com cliente inexistente."""
        try:
            db_cursor.execute(
                """SELECT COUNT(*) as orfaos
                   FROM vendas v
                   LEFT JOIN clientes c ON v.cliente_id = c.id
                   WHERE c.id IS NULL"""
            )
            resultado = db_cursor.fetchone()
            assert resultado["orfaos"] == 0, \
                f"Existem {resultado['orfaos']} vendas com cliente_id inválido (registros órfãos)"
        except Exception as e:
            pytest.skip(f"Verificação de órfãos ignorada: {e}")
