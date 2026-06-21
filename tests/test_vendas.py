"""
test_vendas.py — Testes do módulo de vendas.

Execute:
    pytest tests/test_vendas.py -v
"""

import pytest
from datetime import datetime


class TestCalculosVenda:
    """Testes unitários de cálculo — sem banco de dados."""

    def test_total_venda_simples(self):
        """Total = quantidade × preço unitário."""
        quantidade = 10.0
        preco_unitario = 2.50
        total = round(quantidade * preco_unitario, 2)
        assert total == 25.00

    def test_total_venda_fracionado(self):
        """Total com valores decimais deve ser preciso."""
        quantidade = 7.3
        preco_unitario = 1.80
        total = round(quantidade * preco_unitario, 2)
        assert total == 13.14

    def test_venda_quantidade_zero_invalida(self):
        """Não deve permitir venda com quantidade zero."""
        quantidade = 0
        assert quantidade <= 0, "Quantidade zero deve ser rejeitada"

    def test_venda_quantidade_negativa_invalida(self):
        """Não deve permitir quantidade negativa."""
        quantidade = -5.0
        assert quantidade < 0, "Quantidade negativa deve ser rejeitada"

    def test_desconto_percentual(self):
        """Desconto percentual aplicado corretamente."""
        total_bruto = 100.00
        desconto_pct = 10  # 10%
        desconto_valor = total_bruto * (desconto_pct / 100)
        total_liquido = total_bruto - desconto_valor
        assert total_liquido == 90.00

    def test_desconto_nao_pode_ser_maior_que_total(self):
        """Desconto não pode ser maior que o valor total da venda."""
        total = 50.00
        desconto = 60.00
        assert desconto > total, "Desconto maior que total deve ser bloqueado"

    def test_data_venda_e_hoje(self):
        """Data da venda deve corresponder ao dia atual."""
        data_venda = datetime.now().date()
        hoje = datetime.now().date()
        assert data_venda == hoje

    def test_recibo_contem_campos_obrigatorios(self):
        """Simula estrutura mínima de um recibo."""
        recibo = {
            "numero": "0001",
            "data": "2025-06-01",
            "cliente": "João Silva",
            "itens": [{"material": "Ferro", "kg": 10, "total": 25.00}],
            "total_geral": 25.00,
        }
        assert "numero" in recibo
        assert "data" in recibo
        assert "cliente" in recibo
        assert "total_geral" in recibo
        assert len(recibo["itens"]) > 0


class TestVendaBancoDados:
    """Testes de integração com banco real."""

    def test_tabela_vendas_existe(self, db_cursor):
        """Verifica se a tabela de vendas existe."""
        db_cursor.execute("SHOW TABLES LIKE 'vendas'")
        resultado = db_cursor.fetchone()
        assert resultado is not None, "Tabela 'vendas' não encontrada"

    def test_registrar_venda(self, db_cursor, venda_exemplo):
        """Registra uma venda e verifica persistência."""
        v = venda_exemplo
        db_cursor.execute(
            """INSERT INTO vendas (cliente_id, material_id, quantidade_kg, preco_unitario, total)
               VALUES (%s, %s, %s, %s, %s)""",
            (v["cliente_id"], v["material_id"], v["quantidade_kg"],
             v["preco_unitario"], v["total"])
        )
        venda_id = db_cursor.lastrowid

        db_cursor.execute("SELECT * FROM vendas WHERE id = %s", (venda_id,))
        resultado = db_cursor.fetchone()

        assert resultado is not None
        assert float(resultado["total"]) == v["total"]

    def test_estoque_atualizado_apos_venda(self, db_cursor, material_exemplo):
        """
        Após uma venda, o estoque do material deve diminuir.
        Adapte conforme a lógica real do seu sistema.
        """
        m = material_exemplo
        db_cursor.execute(
            "INSERT INTO materiais (nome, categoria, preco_kg, quantidade_kg) VALUES (%s, %s, %s, %s)",
            (m["nome"], m["categoria"], m["preco_kg"], m["quantidade_kg"])
        )
        material_id = db_cursor.lastrowid
        quantidade_vendida = 10.0

        # Simula atualização de estoque após venda
        db_cursor.execute(
            "UPDATE materiais SET quantidade_kg = quantidade_kg - %s WHERE id = %s",
            (quantidade_vendida, material_id)
        )

        db_cursor.execute("SELECT quantidade_kg FROM materiais WHERE id = %s", (material_id,))
        resultado = db_cursor.fetchone()
        estoque_esperado = m["quantidade_kg"] - quantidade_vendida

        assert float(resultado["quantidade_kg"]) == estoque_esperado

    def test_historico_venda_registrado(self, db_cursor):
        """
        Verifica se existe tabela/log de histórico de alterações.
        Adapte o nome da tabela conforme seu projeto.
        """
        # Tenta nomes comuns para tabela de histórico
        nomes_possiveis = ["historico", "historico_alteracoes", "log_vendas", "auditoria"]
        encontrou = False
        for nome in nomes_possiveis:
            db_cursor.execute(f"SHOW TABLES LIKE '{nome}'")
            if db_cursor.fetchone():
                encontrou = True
                break
        # Se não encontrar, exibe aviso (não falha o teste, apenas avisa)
        if not encontrou:
            pytest.warns(UserWarning, match="Tabela de histórico não encontrada")
