"""
repositories/relatorio_repo.py
--------------------------------
Repositório de relatórios financeiros.
Todas as queries de agregação para o módulo de controle financeiro.

Métricas geradas:
    - Faturamento bruto (ValorTotal dos pedidos CONFIRMADO/PREPARANDO/ENVIADO/ENTREGUE)
    - Custo dos produtos vendidos (PrecoCusto × Quantidade de cada ItemPedido)
    - Lucro bruto (faturamento - custo)
    - Valor do estoque atual (Quantidade × PrecoVenda de cada produto ativo)
    - Faturamento mensal (série histórica para gráfico)
    - Top clientes por valor comprado
    - Top produtos por receita gerada
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pyodbc  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Modelos de saída
# ---------------------------------------------------------------------------


@dataclass
class ResumoFinanceiro:
    """Cards de KPI do topo da tela."""

    faturamento_bruto: float
    custo_mercadorias: float
    lucro_bruto: float
    margem_percentual: float  # lucro / faturamento × 100
    total_pedidos: int
    valor_estoque: float
    ticket_medio: float  # faturamento / total_pedidos


@dataclass
class FaturamentoMensal:
    """Um ponto da série histórica para o gráfico de barras."""

    ano: int
    mes: int
    label: str  # "Jan/25", "Fev/25" …
    faturamento: float
    custo: float
    lucro: float


@dataclass
class TopCliente:
    nome: str
    total_comprado: float
    quantidade_pedidos: int


@dataclass
class TopProduto:
    nome: str
    unidade: str
    quantidade_vendida: float
    receita: float
    custo_total: float
    lucro: float


@dataclass
class LinhaDetalhePedido:
    id_pedido: int
    data_pedido: datetime
    nome_cliente: str
    status: str
    faturamento: float
    custo: float
    lucro: float


# ---------------------------------------------------------------------------
# Repositório
# ---------------------------------------------------------------------------

# Status que representam vendas efetivadas (excluindo PENDENTE e CANCELADO)
_STATUS_VENDA = "('CONFIRMADO','PREPARANDO','ENVIADO','ENTREGUE')"

_MESES_PT = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


class RelatorioRepo:
    """
    Queries de agregação financeira.
    Requer uma conexão pyodbc aberta — NÃO gerencia seu ciclo de vida.
    """

    def __init__(self, conn: pyodbc.Connection) -> None:
        self._conn = conn

    def _cursor(self) -> pyodbc.Cursor:
        return self._conn.cursor()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _f(row: Any, idx: int, default: float = 0.0) -> float:
        v = row[idx]
        return float(v) if v is not None else default

    @staticmethod
    def _i(row: Any, idx: int, default: int = 0) -> int:
        v = row[idx]
        return int(v) if v is not None else default

    # ------------------------------------------------------------------
    # Resumo financeiro (KPIs)
    # ------------------------------------------------------------------

    def resumo(
        self,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> ResumoFinanceiro:
        """
        Calcula os KPIs financeiros para o período informado.
        Se nenhum período for informado, considera todos os registros.
        """
        filtro, params = self._filtro_periodo("p.DataPedido", data_inicio, data_fim)

        cur = self._cursor()

        # Faturamento + contagem de pedidos
        cur.execute(
            f"""
            SELECT
                COALESCE(SUM(p.ValorTotal), 0)  AS Faturamento,
                COUNT(p.IDPedido)                AS TotalPedidos
            FROM Pedido p
            WHERE p.Status IN {_STATUS_VENDA}
            {filtro}
            """,
            params,
        )
        row = cur.fetchone()
        faturamento = self._f(row, 0)
        total_pedidos = self._i(row, 1)

        # Custo dos produtos vendidos (join com HistoricoPrecos vigente na data do pedido)
        cur.execute(
            f"""
            SELECT COALESCE(SUM(ip.Quantidade * hp.PrecoCusto), 0) AS CustoTotal
            FROM ItemPedido ip
            JOIN Pedido p ON p.IDPedido = ip.IDPedido
            JOIN (
                SELECT IDProduto, PrecoCusto,
                       DataInicioVigencia,
                       COALESCE(DataFimVigencia, '9999-12-31') AS DataFimVigencia
                FROM HistoricoPrecos
            ) hp ON hp.IDProduto = ip.IDProduto
                 AND p.DataPedido BETWEEN hp.DataInicioVigencia AND hp.DataFimVigencia
            WHERE p.Status IN {_STATUS_VENDA}
            {filtro}
            """,
            params,
        )
        row = cur.fetchone()
        custo = self._f(row, 0)

        # Valor do estoque atual
        cur.execute(
            """
            SELECT COALESCE(SUM(e.Quantidade * hp.PrecoVenda), 0)
            FROM Estoque e
            JOIN ProdutoBase pb ON pb.IDProduto = e.IDProduto AND pb.Ativo = TRUE
            JOIN HistoricoPrecos hp ON hp.IDProduto = e.IDProduto
            WHERE hp.DataFimVigencia IS NULL
            """
        )
        row_est = cur.fetchone()
        valor_estoque = self._f(row_est, 0)

        cur.close()

        lucro = faturamento - custo
        margem = (lucro / faturamento * 100) if faturamento > 0 else 0.0
        ticket = (faturamento / total_pedidos) if total_pedidos > 0 else 0.0

        return ResumoFinanceiro(
            faturamento_bruto=faturamento,
            custo_mercadorias=custo,
            lucro_bruto=lucro,
            margem_percentual=margem,
            total_pedidos=total_pedidos,
            valor_estoque=valor_estoque,
            ticket_medio=ticket,
        )

    # ------------------------------------------------------------------
    # Série mensal (gráfico)
    # ------------------------------------------------------------------

    def faturamento_mensal(
        self,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        ultimos_n_meses: int | None = 12,
    ) -> list[FaturamentoMensal]:
        """
        Retorna faturamento, custo e lucro agrupados por mês.
        Por padrão retorna os últimos 12 meses se nenhum período for dado.
        """
        filtro, params = self._filtro_periodo("p.DataPedido", data_inicio, data_fim)
        if not filtro and ultimos_n_meses:
            filtro = "AND p.DataPedido >= DATE_SUB(NOW(), INTERVAL ? MONTH)"
            params = [ultimos_n_meses]

        cur = self._cursor()
        cur.execute(
            f"""
            SELECT
                YEAR(p.DataPedido)   AS Ano,
                MONTH(p.DataPedido)  AS Mes,
                COALESCE(SUM(p.ValorTotal), 0) AS Faturamento,
                COALESCE(SUM(ip.Quantidade * hp.PrecoCusto), 0) AS Custo
            FROM Pedido p
            LEFT JOIN ItemPedido ip ON ip.IDPedido = p.IDPedido
            LEFT JOIN (
                SELECT IDProduto, PrecoCusto,
                       DataInicioVigencia,
                       COALESCE(DataFimVigencia, '9999-12-31') AS DataFimVigencia
                FROM HistoricoPrecos
            ) hp ON hp.IDProduto = ip.IDProduto
                 AND p.DataPedido BETWEEN hp.DataInicioVigencia AND hp.DataFimVigencia
            WHERE p.Status IN {_STATUS_VENDA}
            {filtro}
            GROUP BY YEAR(p.DataPedido), MONTH(p.DataPedido)
            ORDER BY Ano, Mes
            """,
            params,
        )
        rows = cur.fetchall()
        cur.close()

        resultado = []
        for r in rows:
            ano = self._i(r, 0)
            mes = self._i(r, 1)
            fat = self._f(r, 2)
            custo = self._f(r, 3)
            resultado.append(
                FaturamentoMensal(
                    ano=ano,
                    mes=mes,
                    label=f"{_MESES_PT.get(mes, str(mes))}/{str(ano)[2:]}",
                    faturamento=fat,
                    custo=custo,
                    lucro=fat - custo,
                )
            )
        return resultado

    # ------------------------------------------------------------------
    # Top clientes
    # ------------------------------------------------------------------

    def top_clientes(
        self,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limite: int = 10,
    ) -> list[TopCliente]:
        filtro, params = self._filtro_periodo("p.DataPedido", data_inicio, data_fim)
        cur = self._cursor()
        cur.execute(
            f"""
            SELECT
                e.Nome,
                COALESCE(SUM(p.ValorTotal), 0) AS TotalComprado,
                COUNT(p.IDPedido)               AS QtdPedidos
            FROM Pedido p
            JOIN Entidade e ON e.IDEntidade = p.IDCliente
            WHERE p.Status IN {_STATUS_VENDA}
            {filtro}
            GROUP BY p.IDCliente, e.Nome
            ORDER BY TotalComprado DESC
            LIMIT ?
            """,
            params + [limite],
        )
        rows = cur.fetchall()
        cur.close()
        return [
            TopCliente(
                nome=str(r[0]),
                total_comprado=self._f(r, 1),
                quantidade_pedidos=self._i(r, 2),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Top produtos
    # ------------------------------------------------------------------

    def top_produtos(
        self,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limite: int = 10,
    ) -> list[TopProduto]:
        filtro, params = self._filtro_periodo("p.DataPedido", data_inicio, data_fim)
        cur = self._cursor()
        cur.execute(
            f"""
            SELECT
                pb.Nome,
                pb.UnidadeMedida,
                COALESCE(SUM(ip.Quantidade), 0)                        AS QtdVendida,
                COALESCE(SUM(ip.Quantidade * ip.PrecoUnitario), 0)     AS Receita,
                COALESCE(SUM(ip.Quantidade * hp.PrecoCusto), 0)        AS CustoTotal
            FROM ItemPedido ip
            JOIN Pedido p      ON p.IDPedido   = ip.IDPedido
            JOIN ProdutoBase pb ON pb.IDProduto = ip.IDProduto
            LEFT JOIN (
                SELECT IDProduto, PrecoCusto,
                       DataInicioVigencia,
                       COALESCE(DataFimVigencia, '9999-12-31') AS DataFimVigencia
                FROM HistoricoPrecos
            ) hp ON hp.IDProduto = ip.IDProduto
                 AND p.DataPedido BETWEEN hp.DataInicioVigencia AND hp.DataFimVigencia
            WHERE p.Status IN {_STATUS_VENDA}
            {filtro}
            GROUP BY ip.IDProduto, pb.Nome, pb.UnidadeMedida
            ORDER BY Receita DESC
            LIMIT ?
            """,
            params + [limite],
        )
        rows = cur.fetchall()
        cur.close()
        return [
            TopProduto(
                nome=str(r[0]),
                unidade=str(r[1]) if r[1] else "",
                quantidade_vendida=self._f(r, 2),
                receita=self._f(r, 3),
                custo_total=self._f(r, 4),
                lucro=self._f(r, 3) - self._f(r, 4),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Detalhe de pedidos (tabela)
    # ------------------------------------------------------------------

    def detalhe_pedidos(
        self,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> list[LinhaDetalhePedido]:
        filtro, params = self._filtro_periodo("p.DataPedido", data_inicio, data_fim)
        cur = self._cursor()
        cur.execute(
            f"""
            SELECT
                p.IDPedido,
                p.DataPedido,
                e.Nome                                                       AS Cliente,
                p.Status,
                COALESCE(p.ValorTotal, 0)                                    AS Faturamento,
                COALESCE(SUM(ip.Quantidade * hp.PrecoCusto), 0)             AS Custo
            FROM Pedido p
            JOIN Entidade e ON e.IDEntidade = p.IDCliente
            LEFT JOIN ItemPedido ip ON ip.IDPedido = p.IDPedido
            LEFT JOIN (
                SELECT IDProduto, PrecoCusto,
                       DataInicioVigencia,
                       COALESCE(DataFimVigencia, '9999-12-31') AS DataFimVigencia
                FROM HistoricoPrecos
            ) hp ON hp.IDProduto = ip.IDProduto
                 AND p.DataPedido BETWEEN hp.DataInicioVigencia AND hp.DataFimVigencia
            WHERE p.Status IN {_STATUS_VENDA}
            {filtro}
            GROUP BY p.IDPedido, p.DataPedido, e.Nome, p.Status, p.ValorTotal
            ORDER BY p.DataPedido DESC
            """,
            params,
        )
        rows = cur.fetchall()
        cur.close()
        return [
            LinhaDetalhePedido(
                id_pedido=self._i(r, 0),
                data_pedido=r[1],
                nome_cliente=str(r[2]),
                status=str(r[3]),
                faturamento=self._f(r, 4),
                custo=self._f(r, 5),
                lucro=self._f(r, 4) - self._f(r, 5),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Helper de filtro
    # ------------------------------------------------------------------

    @staticmethod
    def _filtro_periodo(
        campo: str,
        data_inicio: datetime | None,
        data_fim: datetime | None,
    ) -> tuple[str, list[Any]]:
        parts: list[str] = []
        params: list[Any] = []
        if data_inicio:
            parts.append(f"AND {campo} >= ?")
            params.append(data_inicio)
        if data_fim:
            parts.append(f"AND {campo} <= ?")
            params.append(data_fim)
        return " ".join(parts), params
