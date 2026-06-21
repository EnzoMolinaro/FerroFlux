"""
test_relatorio_repo.py — Testes de repositories/relatorio_repo.py

Execute:
    pytest tests/test_relatorio_repo.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from repositories.relatorio_repo import (
    RelatorioRepo, ResumoFinanceiro, FaturamentoMensal,
    TopCliente, TopProduto, LinhaDetalhePedido, _MESES_PT
)


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def _repo(cursor_retornos: list):
    """Cria VendaRepo com conn mockado. cursor_retornos: lista de fetchone/fetchall."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.fetchone.side_effect = cursor_retornos
    return RelatorioRepo(conn), cursor


# ══════════════════════════════════════════════════════
#  TESTES DE MODELOS E CONSTANTES
# ══════════════════════════════════════════════════════

class TestMesesPortugues:

    def test_janeiro(self):
        assert _MESES_PT[1] == "Jan"

    def test_dezembro(self):
        assert _MESES_PT[12] == "Dez"

    def test_todos_os_meses_presentes(self):
        assert len(_MESES_PT) == 12
        assert set(_MESES_PT.keys()) == set(range(1, 13))


class TestResumoFinanceiro:

    def test_lucro_calculado_corretamente(self):
        r = ResumoFinanceiro(
            faturamento_bruto=1000.0, custo_mercadorias=600.0,
            lucro_bruto=400.0, margem_percentual=40.0,
            total_pedidos=5, valor_estoque=2000.0, ticket_medio=200.0
        )
        assert r.lucro_bruto == 400.0
        assert r.margem_percentual == 40.0

    def test_ticket_medio_zero_sem_pedidos(self):
        """Divisão por zero deve ser tratada — ticket = 0 quando sem pedidos."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        # faturamento=0, pedidos=0, estoque=0
        cursor.fetchone.side_effect = [(0, 0), (0,), (0,)]
        repo = RelatorioRepo(conn)

        resumo = repo.resumo()
        assert resumo.ticket_medio == 0.0

    def test_margem_zero_sem_faturamento(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.side_effect = [(0, 0), (0,), (0,)]
        repo = RelatorioRepo(conn)

        resumo = repo.resumo()
        assert resumo.margem_percentual == 0.0


class TestHelpersFR:
    """Testa os helpers estáticos _f e _i."""

    def test_f_retorna_float(self):
        row = (None, 42.5, "x")
        assert RelatorioRepo._f(row, 1) == 42.5

    def test_f_retorna_default_quando_none(self):
        row = (None,)
        assert RelatorioRepo._f(row, 0) == 0.0

    def test_f_default_customizado(self):
        row = (None,)
        assert RelatorioRepo._f(row, 0, default=99.9) == 99.9

    def test_i_retorna_int(self):
        row = (7,)
        assert RelatorioRepo._i(row, 0) == 7

    def test_i_retorna_default_quando_none(self):
        row = (None,)
        assert RelatorioRepo._i(row, 0) == 0


class TestFiltroPeriodo:
    """Testa o helper estático _filtro_periodo."""

    def test_sem_datas_retorna_string_vazia(self):
        filtro, params = RelatorioRepo._filtro_periodo("p.DataPedido", None, None)
        assert filtro == ""
        assert params == []

    def test_com_data_inicio_gera_clausula(self):
        dt = datetime(2025, 1, 1)
        filtro, params = RelatorioRepo._filtro_periodo("p.DataPedido", dt, None)
        assert ">=" in filtro
        assert dt in params

    def test_com_data_fim_gera_clausula(self):
        dt = datetime(2025, 12, 31)
        filtro, params = RelatorioRepo._filtro_periodo("p.DataPedido", None, dt)
        assert "<=" in filtro
        assert dt in params

    def test_com_ambas_as_datas_gera_dois_filtros(self):
        inicio = datetime(2025, 1, 1)
        fim = datetime(2025, 12, 31)
        filtro, params = RelatorioRepo._filtro_periodo("p.DataPedido", inicio, fim)
        assert ">=" in filtro
        assert "<=" in filtro
        assert len(params) == 2

    def test_campo_correto_na_clausula(self):
        dt = datetime(2025, 6, 1)
        filtro, _ = RelatorioRepo._filtro_periodo("p.DataPedido", dt, None)
        assert "p.DataPedido" in filtro


# ══════════════════════════════════════════════════════
#  RESUMO FINANCEIRO
# ══════════════════════════════════════════════════════

class TestResumo:

    def test_resumo_com_dados(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        # fetchone: faturamento+pedidos, custo, estoque
        cursor.fetchone.side_effect = [
            (1000.0, 5),   # faturamento bruto e total pedidos
            (600.0,),      # custo mercadorias
            (5000.0,),     # valor estoque
        ]
        repo = RelatorioRepo(conn)
        resumo = repo.resumo()

        assert resumo.faturamento_bruto == 1000.0
        assert resumo.custo_mercadorias == 600.0
        assert resumo.lucro_bruto == 400.0
        assert resumo.total_pedidos == 5
        assert resumo.valor_estoque == 5000.0
        assert resumo.ticket_medio == 200.0
        assert resumo.margem_percentual == 40.0

    def test_resumo_com_periodo(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.side_effect = [(500.0, 2), (300.0,), (0.0,)]
        repo = RelatorioRepo(conn)

        inicio = datetime(2025, 1, 1)
        fim = datetime(2025, 6, 30)
        resumo = repo.resumo(data_inicio=inicio, data_fim=fim)

        # Verifica que os parâmetros de período foram passados ao cursor
        calls_params = [c[0][1] for c in cursor.execute.call_args_list if c[0][1]]
        params_flat = [p for params in calls_params for p in params]
        assert inicio in params_flat
        assert fim in params_flat


# ══════════════════════════════════════════════════════
#  FATURAMENTO MENSAL
# ══════════════════════════════════════════════════════

class TestFaturamentoMensal:

    def test_label_formato_mes_ano(self):
        fm = FaturamentoMensal(ano=2025, mes=1, label="Jan/25",
                               faturamento=1000.0, custo=600.0, lucro=400.0)
        assert fm.label == "Jan/25"

    def test_retorna_lista_de_faturamento_mensal(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            (2025, 1, 1000.0, 600.0),
            (2025, 2, 1500.0, 900.0),
        ]
        repo = RelatorioRepo(conn)
        resultado = repo.faturamento_mensal()

        assert len(resultado) == 2
        assert resultado[0].label == "Jan/25"
        assert resultado[0].faturamento == 1000.0
        assert resultado[0].lucro == 400.0
        assert resultado[1].label == "Fev/25"

    def test_lucro_calculado_por_mes(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [(2025, 3, 2000.0, 1200.0)]
        repo = RelatorioRepo(conn)
        resultado = repo.faturamento_mensal()

        assert resultado[0].lucro == 800.0

    def test_lista_vazia_sem_dados(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = RelatorioRepo(conn)

        assert repo.faturamento_mensal() == []

    def test_ultimos_n_meses_passa_parametro(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = RelatorioRepo(conn)
        repo.faturamento_mensal(ultimos_n_meses=6)

        params = cursor.execute.call_args[0][1]
        assert 6 in params


# ══════════════════════════════════════════════════════
#  TOP CLIENTES
# ══════════════════════════════════════════════════════

class TestTopClientes:

    def test_retorna_lista_de_top_cliente(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            ("João Silva", 5000.0, 10),
            ("Maria Souza", 3000.0, 6),
        ]
        repo = RelatorioRepo(conn)
        resultado = repo.top_clientes()

        assert len(resultado) == 2
        assert resultado[0].nome == "João Silva"
        assert resultado[0].total_comprado == 5000.0
        assert resultado[0].quantidade_pedidos == 10

    def test_limite_passado_como_parametro(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = RelatorioRepo(conn)
        repo.top_clientes(limite=5)

        params = cursor.execute.call_args[0][1]
        assert 5 in params

    def test_lista_vazia_sem_vendas(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = RelatorioRepo(conn)
        assert repo.top_clientes() == []


# ══════════════════════════════════════════════════════
#  TOP PRODUTOS
# ══════════════════════════════════════════════════════

class TestTopProdutos:

    def test_retorna_lista_de_top_produto(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            ("Ferro Fundido", "KG", 500.0, 1250.0, 750.0),
            ("Alumínio",      "KG", 200.0, 9000.0, 4000.0),
        ]
        repo = RelatorioRepo(conn)
        resultado = repo.top_produtos()

        assert len(resultado) == 2
        assert resultado[0].nome == "Ferro Fundido"
        assert resultado[0].quantidade_vendida == 500.0
        assert resultado[0].receita == 1250.0
        assert resultado[0].lucro == 500.0   # 1250 - 750

    def test_lucro_calculado_receita_menos_custo(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [("Cobre", "KG", 100.0, 4500.0, 2000.0)]
        repo = RelatorioRepo(conn)
        resultado = repo.top_produtos()

        assert resultado[0].lucro == 2500.0

    def test_limite_passado_como_parametro(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = RelatorioRepo(conn)
        repo.top_produtos(limite=3)

        params = cursor.execute.call_args[0][1]
        assert 3 in params


# ══════════════════════════════════════════════════════
#  DETALHE DE PEDIDOS
# ══════════════════════════════════════════════════════

class TestDetalhePedidos:

    def test_retorna_lista_de_linhas(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        data = datetime(2025, 3, 15)
        cursor.fetchall.return_value = [
            (1, data, "João Silva", "ENTREGUE", 250.0, 150.0),
            (2, data, "Maria Souza", "CONFIRMADO", 100.0, 60.0),
        ]
        repo = RelatorioRepo(conn)
        resultado = repo.detalhe_pedidos()

        assert len(resultado) == 2
        assert resultado[0].id_pedido == 1
        assert resultado[0].nome_cliente == "João Silva"
        assert resultado[0].status == "ENTREGUE"
        assert resultado[0].faturamento == 250.0
        assert resultado[0].custo == 150.0
        assert resultado[0].lucro == 100.0

    def test_lucro_calculado_por_linha(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            (3, datetime(2025, 1, 1), "X", "ENTREGUE", 1000.0, 700.0)
        ]
        repo = RelatorioRepo(conn)
        resultado = repo.detalhe_pedidos()

        assert resultado[0].lucro == 300.0

    def test_lista_vazia_sem_pedidos(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = RelatorioRepo(conn)

        assert repo.detalhe_pedidos() == []
