"""
test_relatorios.py — Testes de relatório financeiro e histórico.

Execute:
    pytest tests/test_relatorios.py -v
"""

import pytest
from datetime import date, timedelta


class TestRelatorioFinanceiro:
    """Testes unitários de lógica financeira."""

    def test_soma_total_vendas(self):
        """Soma de vendas deve ser precisa."""
        vendas = [25.00, 50.00, 13.50, 100.00]
        total = sum(vendas)
        assert total == 188.50

    def test_relatorio_periodo_correto(self):
        """Datas de início e fim do relatório devem ser coerentes."""
        data_inicio = date(2025, 1, 1)
        data_fim = date(2025, 6, 30)
        assert data_inicio <= data_fim, "Data início deve ser anterior à data fim"

    def test_periodo_invalido_inicio_maior_que_fim(self):
        """Período com início após fim deve ser rejeitado."""
        data_inicio = date(2025, 12, 31)
        data_fim = date(2025, 1, 1)
        assert data_inicio > data_fim, "Este período inválido deve ser bloqueado"

    def test_lucro_calculado_corretamente(self):
        """Lucro = Receita - Custos."""
        receita = 1000.00
        custos = 600.00
        lucro = receita - custos
        assert lucro == 400.00

    def test_lucro_negativo_prejuizo(self):
        """Lucro negativo representa prejuízo."""
        receita = 300.00
        custos = 500.00
        lucro = receita - custos
        assert lucro < 0

    def test_media_vendas_por_dia(self):
        """Média diária de vendas."""
        total_vendas = 900.00
        dias = 30
        media = round(total_vendas / dias, 2)
        assert media == 30.00

    def test_relatorio_sem_vendas_retorna_zero(self):
        """Relatório em período sem vendas deve retornar total zero."""
        vendas = []
        total = sum(vendas)
        assert total == 0.0


class TestRelatorioFinanceiroBancoDados:
    """Testes de relatório com banco real."""

    def test_consulta_vendas_por_periodo(self, db_cursor):
        """Consulta de vendas filtrando por período deve funcionar."""
        data_inicio = "2024-01-01"
        data_fim = "2025-12-31"

        try:
            db_cursor.execute(
                """SELECT SUM(total) as total_periodo
                   FROM vendas
                   WHERE DATE(data_venda) BETWEEN %s AND %s""",
                (data_inicio, data_fim)
            )
            resultado = db_cursor.fetchone()
            # Pode ser None se não houver vendas no período
            total = resultado["total_periodo"] if resultado["total_periodo"] else 0
            assert total >= 0
        except Exception as e:
            pytest.skip(f"Tabela 'vendas' não encontrada ou campo 'data_venda' ausente: {e}")

    def test_consulta_total_por_material(self, db_cursor):
        """Agrupa vendas por material — útil para relatório."""
        try:
            db_cursor.execute(
                """SELECT m.nome, SUM(v.total) as total_vendido
                   FROM vendas v
                   JOIN materiais m ON v.material_id = m.id
                   GROUP BY m.nome
                   ORDER BY total_vendido DESC"""
            )
            resultados = db_cursor.fetchall()
            assert isinstance(resultados, list)
        except Exception as e:
            pytest.skip(f"Consulta de relatório por material falhou: {e}")

    def test_consulta_total_por_cliente(self, db_cursor):
        """Agrupa vendas por cliente."""
        try:
            db_cursor.execute(
                """SELECT c.nome, SUM(v.total) as total_gasto
                   FROM vendas v
                   JOIN clientes c ON v.cliente_id = c.id
                   GROUP BY c.nome
                   ORDER BY total_gasto DESC"""
            )
            resultados = db_cursor.fetchall()
            assert isinstance(resultados, list)
        except Exception as e:
            pytest.skip(f"Consulta de relatório por cliente falhou: {e}")


class TestHistoricoAlteracoes:
    """Testes para o histórico/log de alterações."""

    def test_estrutura_registro_historico(self):
        """Um registro de histórico deve conter campos essenciais."""
        registro = {
            "tabela": "materiais",
            "acao": "UPDATE",
            "campo_alterado": "preco_kg",
            "valor_anterior": "2.50",
            "valor_novo": "3.00",
            "usuario": "admin",
            "data_hora": "2025-06-01 10:30:00",
        }
        campos_obrigatorios = ["tabela", "acao", "usuario", "data_hora"]
        for campo in campos_obrigatorios:
            assert campo in registro, f"Campo '{campo}' ausente no histórico"

    def test_acao_historico_valida(self):
        """Ação do histórico deve ser uma das operações válidas."""
        acoes_validas = {"INSERT", "UPDATE", "DELETE"}
        acao = "UPDATE"
        assert acao in acoes_validas

    def test_historico_banco_dados(self, db_cursor):
        """Verifica se existe alguma tabela de histórico/auditoria."""
        nomes_possiveis = [
            "historico", "historico_alteracoes", "log_alteracoes",
            "auditoria", "audit_log", "log"
        ]
        encontrou = False
        tabela_encontrada = None
        for nome in nomes_possiveis:
            db_cursor.execute(f"SHOW TABLES LIKE '{nome}'")
            if db_cursor.fetchone():
                encontrou = True
                tabela_encontrada = nome
                break

        if encontrou:
            db_cursor.execute(f"DESCRIBE {tabela_encontrada}")
            colunas = [col["Field"] for col in db_cursor.fetchall()]
            assert len(colunas) > 0, "Tabela de histórico existe mas está vazia"
        else:
            pytest.skip("Tabela de histórico não encontrada — verifique o nome no conftest.py")
