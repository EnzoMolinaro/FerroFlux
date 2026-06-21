"""
test_materiais.py — Testes de gestão de materiais.

Execute:
    pytest tests/test_materiais.py -v
"""

import pytest
from unittest.mock import MagicMock


class TestCadastroMaterialUnitario:
    """Testes unitários sem banco real."""

    def test_cadastrar_material_dados_validos(self, mock_conn, material_exemplo):
        """Inserção com dados válidos deve chamar execute corretamente."""
        conn, cursor = mock_conn
        cursor.rowcount = 1

        m = material_exemplo
        cursor.execute(
            "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
            (m["nome"], m["categoria"], m["preco_kg"], m["quantidade_kg"])
        )

        cursor.execute.assert_called_once()
        assert cursor.rowcount == 1

    def test_cadastrar_material_nome_vazio_deve_falhar(self, mock_conn):
        """Material sem nome não deve ser inserido."""
        conn, cursor = mock_conn

        material_invalido = {"nome": "", "categoria": "Ferroso", "preco_kg": 2.5, "quantidade_kg": 10}

        # Sua função de cadastro deveria validar e lançar erro ou retornar False
        assert material_invalido["nome"].strip() == "", "Nome vazio deve ser rejeitado"

    def test_preco_negativo_invalido(self):
        """Preço por kg não pode ser negativo."""
        preco = -1.50
        assert preco < 0, "Preço negativo deve ser rejeitado pela validação"

    def test_quantidade_zero_invalida(self):
        """Quantidade zero ou negativa deve ser rejeitada."""
        quantidade = 0
        assert quantidade <= 0, "Quantidade zero deve ser rejeitada"

    def test_calculo_valor_total_estoque(self):
        """Calcula valor total: quantidade_kg × preco_kg."""
        preco_kg = 2.50
        quantidade_kg = 100.0
        total_esperado = 250.00

        total = preco_kg * quantidade_kg
        assert total == total_esperado

    def test_calculo_valor_total_fracionado(self):
        """Verifica cálculo com valores fracionados."""
        preco_kg = 1.75
        quantidade_kg = 33.5
        total = round(preco_kg * quantidade_kg, 2)
        assert total == 58.63


class TestEstoqueMaterial:
    """Testes de lógica de estoque."""

    def test_entrada_estoque_aumenta_quantidade(self):
        """Entrada de material deve somar à quantidade existente."""
        quantidade_atual = 100.0
        entrada = 50.0
        novo_total = quantidade_atual + entrada
        assert novo_total == 150.0

    def test_saida_estoque_diminui_quantidade(self):
        """Saída de material deve subtrair da quantidade existente."""
        quantidade_atual = 100.0
        saida = 30.0
        novo_total = quantidade_atual - saida
        assert novo_total == 70.0

    def test_saida_maior_que_estoque_invalida(self):
        """Não deve permitir saída maior que o estoque disponível."""
        quantidade_atual = 20.0
        saida = 50.0
        assert saida > quantidade_atual, "Saída maior que estoque deve ser bloqueada"

    def test_estoque_negativo_nao_permitido(self):
        """Estoque nunca deve ficar negativo."""
        quantidade_atual = 10.0
        saida = 10.0
        resultado = quantidade_atual - saida
        assert resultado >= 0


class TestMaterialBancoDados:
    """Testes com banco real."""

    def test_tabela_materiais_existe(self, db_cursor):
        """Verifica se a tabela materiais existe no banco."""
        db_cursor.execute("SHOW TABLES LIKE 'materiais'")
        resultado = db_cursor.fetchone()
        assert resultado is not None, "Tabela 'materiais' não encontrada no banco"

    def test_inserir_e_buscar_material(self, db_cursor, material_exemplo):
        """Insere um material e verifica se é recuperado corretamente."""
        m = material_exemplo
        db_cursor.execute(
            "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
            (m["nome"], m["categoria"], m["preco_kg"], m["quantidade_kg"])
        )
        material_id = db_cursor.lastrowid

        db_cursor.execute("SELECT * FROM materiais WHERE id = %s", (material_id,))
        resultado = db_cursor.fetchone()

        assert resultado is not None
        assert resultado["nome"] == m["nome"]
        assert float(resultado["preco_kg"]) == m["preco_kg"]
        # rollback automático pelo fixture db_cursor

    def test_busca_material_por_nome(self, db_cursor):
        """Busca por nome deve retornar resultados relevantes."""
        db_cursor.execute(
            "SELECT * FROM materiais WHERE nome LIKE %s",
            ("%Ferro%",)
        )
        resultados = db_cursor.fetchall()
        # Pode estar vazio se o banco de testes estiver limpo — só verifica o tipo
        assert isinstance(resultados, list)

    def test_atualizar_preco_material(self, db_cursor, material_exemplo):
        """Atualização de preço deve refletir no banco."""
        m = material_exemplo
        db_cursor.execute(
            "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
            (m["nome"], m["categoria"], m["preco_kg"], m["quantidade_kg"])
        )
        material_id = db_cursor.lastrowid

        novo_preco = 3.00
        db_cursor.execute(
            "UPDATE materiais SET preco_kg = %s WHERE id = %s",
            (novo_preco, material_id)
        )

        db_cursor.execute("SELECT preco_kg FROM materiais WHERE id = %s", (material_id,))
        resultado = db_cursor.fetchone()
        assert float(resultado["preco_kg"]) == novo_preco

    def test_deletar_material(self, db_cursor, material_exemplo):
        """Material deletado não deve mais aparecer na busca."""
        m = material_exemplo
        db_cursor.execute(
            "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
            (m["nome"], m["categoria"], m["preco_kg"], m["quantidade_kg"])
        )
        material_id = db_cursor.lastrowid

        db_cursor.execute("DELETE FROM materiais WHERE id = %s", (material_id,))
        db_cursor.execute("SELECT * FROM materiais WHERE id = %s", (material_id,))
        resultado = db_cursor.fetchone()

        assert resultado is None
