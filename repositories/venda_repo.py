"""
repositories/venda_repo.py
---------------------------
Repositório de vendas — Pedido, ItemPedido, MovimentacaoEstoque, NotaFiscal.

Fluxo principal:
    1. criar_pedido()          → insere Pedido com status PENDENTE
    2. adicionar_item()        → insere ItemPedido e valida estoque
    3. confirmar_pedido()      → muda status para CONFIRMADO, baixa estoque,
                                 atualiza ValorTotal
    4. cancelar_pedido()       → muda status para CANCELADO, estorna estoque
    5. avancar_status()        → CONFIRMADO → PREPARANDO → ENVIADO → ENTREGUE
    6. emitir_nota_fiscal()    → insere NotaFiscal vinculada ao pedido
    7. Consultas de listagem, busca, detalhes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

STATUS_PEDIDO = [
    "PENDENTE",
    "CONFIRMADO",
    "PREPARANDO",
    "ENVIADO",
    "ENTREGUE",
    "CANCELADO",
]
STATUS_AVANCAR = {
    "CONFIRMADO": "PREPARANDO",
    "PREPARANDO": "ENVIADO",
    "ENVIADO": "ENTREGUE",
}


@dataclass
class ItemPedido:
    id_produto: int
    nome_produto: str
    unidade: str
    quantidade: float
    preco_unitario: float
    subtotal: float = field(init=False)
    id_item: int | None = None

    def __post_init__(self) -> None:
        self.subtotal = round(self.quantidade * self.preco_unitario, 2)


@dataclass
class Pedido:
    id_cliente: int
    nome_cliente: str
    data_pedido: datetime
    status: str
    valor_total: float
    observacoes: str
    id_pedido: int | None = None
    id_endereco_entrega: int | None = None
    endereco_entrega: str = ""
    itens: list[ItemPedido] = field(default_factory=list)


@dataclass
class NotaFiscal:
    id_pedido: int
    data_emissao: datetime
    valor_total: float
    status: str
    tipo_nota: str
    id_emitente: int
    nome_emitente: str
    id_destinatario: int
    nome_destinatario: str
    observacoes: str
    xml_nota: str = ""
    id_nota: int | None = None


# ---------------------------------------------------------------------------
# Repositório
# ---------------------------------------------------------------------------


class VendaRepo:
    """
    Operações de banco para o módulo de vendas.
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
    def _row_pedido(row: Any) -> Pedido:
        return Pedido(
            id_pedido=int(row[0]),
            id_cliente=int(row[1]),
            nome_cliente=str(row[2]),
            data_pedido=row[3],
            status=str(row[4]),
            valor_total=float(row[5]) if row[5] is not None else 0.0,
            observacoes=str(row[6]) if row[6] is not None else "",
            id_endereco_entrega=int(row[7]) if row[7] is not None else None,
            endereco_entrega=str(row[8]) if row[8] is not None else "",
        )

    @staticmethod
    def _row_item(row: Any) -> ItemPedido:
        item = ItemPedido(
            id_item=int(row[0]),
            id_produto=int(row[1]),
            nome_produto=str(row[2]),
            unidade=str(row[3]) if row[3] is not None else "",
            quantidade=float(row[4]),
            preco_unitario=float(row[5]),
        )
        item.subtotal = float(row[6]) if row[6] is not None else item.subtotal
        return item

    # ------------------------------------------------------------------
    # Consultas de pedidos
    # ------------------------------------------------------------------

    _SQL_PEDIDOS = """
        SELECT
            p.IDPedido,
            p.IDCliente,
            e.Nome          AS NomeCliente,
            p.DataPedido,
            p.Status,
            p.ValorTotal,
            p.Observacoes,
            p.IDEnderecoEntrega,
            CONCAT(eb.Logradouro, ', ', eb.Numero, ' - ', eb.Cidade) AS EnderecoEntrega
        FROM Pedido p
        JOIN Entidade e  ON e.IDEntidade = p.IDCliente
        LEFT JOIN EnderecoBase eb ON eb.IDEndereco = p.IDEnderecoEntrega
    """

    def listar_pedidos(
        self,
        status: str | None = None,
        id_cliente: int | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> list[Pedido]:
        """Lista pedidos com filtros opcionais."""
        filtros: list[str] = []
        params: list[Any] = []

        if status and status != "TODOS":
            filtros.append("p.Status = ?")
            params.append(status)
        if id_cliente:
            filtros.append("p.IDCliente = ?")
            params.append(id_cliente)
        if data_inicio:
            filtros.append("p.DataPedido >= ?")
            params.append(data_inicio)
        if data_fim:
            filtros.append("p.DataPedido <= ?")
            params.append(data_fim)

        sql = self._SQL_PEDIDOS
        if filtros:
            sql += " WHERE " + " AND ".join(filtros)
        sql += " ORDER BY p.DataPedido DESC"

        cur = self._cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [self._row_pedido(r) for r in rows]

    def buscar_pedido(self, id_pedido: int) -> Pedido | None:
        """Busca pedido por ID com seus itens."""
        cur = self._cursor()
        cur.execute(self._SQL_PEDIDOS + " WHERE p.IDPedido = ?", (id_pedido,))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return None
        pedido = self._row_pedido(row)
        pedido.itens = self.listar_itens(id_pedido)
        return pedido

    def listar_itens(self, id_pedido: int) -> list[ItemPedido]:
        """Retorna os itens de um pedido."""
        cur = self._cursor()
        cur.execute(
            """
            SELECT
                ip.IDItemPedido,
                ip.IDProduto,
                pb.Nome,
                pb.UnidadeMedida,
                ip.Quantidade,
                ip.PrecoUnitario,
                ip.Subtotal
            FROM ItemPedido ip
            JOIN ProdutoBase pb ON pb.IDProduto = ip.IDProduto
            WHERE ip.IDPedido = ?
            ORDER BY pb.Nome
            """,
            (id_pedido,),
        )
        rows = cur.fetchall()
        cur.close()
        return [self._row_item(r) for r in rows]

    # ------------------------------------------------------------------
    # Estoque
    # ------------------------------------------------------------------

    def estoque_disponivel(self, id_produto: int) -> float:
        """Retorna a quantidade atual em estoque de um produto."""
        cur = self._cursor()
        cur.execute(
            "SELECT COALESCE(Quantidade, 0) FROM Estoque WHERE IDProduto = ?",
            (id_produto,),
        )
        row = cur.fetchone()
        cur.close()
        return float(row[0]) if row else 0.0

    def validar_estoque_pedido(self, itens: list[ItemPedido]) -> list[str]:
        """
        Valida se todos os itens têm estoque suficiente.
        Retorna lista de mensagens de erro (vazia se tudo OK).
        """
        erros: list[str] = []
        for item in itens:
            disponivel = self.estoque_disponivel(item.id_produto)
            if disponivel < item.quantidade:
                erros.append(
                    f"{item.nome_produto}: estoque insuficiente "
                    f"(disponível: {disponivel:.2f} {item.unidade}, "
                    f"solicitado: {item.quantidade:.2f} {item.unidade})"
                )
        return erros

    # ------------------------------------------------------------------
    # Criação e edição de pedido
    # ------------------------------------------------------------------

    def criar_pedido(
        self,
        id_cliente: int,
        observacoes: str = "",
        id_endereco_entrega: int | None = None,
    ) -> int:
        """
        Cria um pedido com status PENDENTE.
        Retorna o ID do pedido criado.
        """
        cur = self._cursor()
        cur.execute(
            """
            INSERT INTO Pedido (IDCliente, IDEnderecoEntrega, Status, ValorTotal, Observacoes)
            VALUES (?, ?, 'PENDENTE', 0, ?)
            """,
            (id_cliente, id_endereco_entrega, observacoes or None),
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        row = cur.fetchone()
        if row is None:
            self._conn.rollback()
            raise ConexaoError("Banco não retornou o ID do pedido criado.")
        id_pedido = int(row[0])
        self._conn.commit()
        cur.close()
        return id_pedido

    def salvar_itens(self, id_pedido: int, itens: list[ItemPedido]) -> None:
        """
        Substitui todos os itens de um pedido PENDENTE.
        Limpa os itens atuais e reinsere.
        """
        cur = self._cursor()
        cur.execute("DELETE FROM ItemPedido WHERE IDPedido = ?", (id_pedido,))
        for item in itens:
            cur.execute(
                """
                INSERT INTO ItemPedido (IDPedido, IDProduto, Quantidade, PrecoUnitario)
                VALUES (?, ?, ?, ?)
                """,
                (id_pedido, item.id_produto, item.quantidade, item.preco_unitario),
            )
        # Atualiza ValorTotal
        cur.execute(
            """
            UPDATE Pedido
            SET ValorTotal = (
                SELECT COALESCE(SUM(Subtotal), 0) FROM ItemPedido WHERE IDPedido = ?
            )
            WHERE IDPedido = ?
            """,
            (id_pedido, id_pedido),
        )
        self._conn.commit()
        cur.close()

    def atualizar_observacoes(
        self,
        id_pedido: int,
        observacoes: str,
        id_endereco_entrega: int | None,
    ) -> None:
        cur = self._cursor()
        cur.execute(
            "UPDATE Pedido SET Observacoes = ?, IDEnderecoEntrega = ? WHERE IDPedido = ?",
            (observacoes or None, id_endereco_entrega, id_pedido),
        )
        self._conn.commit()
        cur.close()

    # ------------------------------------------------------------------
    # Mudanças de status
    # ------------------------------------------------------------------

    def confirmar_pedido(self, id_pedido: int, id_usuario: int) -> None:
        """
        Confirma o pedido: valida estoque, baixa estoque de cada item,
        insere movimentações e muda status para CONFIRMADO.

        Raises:
            ValueError: se estoque insuficiente ou pedido sem itens.
        """
        itens = self.listar_itens(id_pedido)
        if not itens:
            raise ValueError("O pedido não possui itens.")

        erros = self.validar_estoque_pedido(itens)
        if erros:
            raise ValueError("Estoque insuficiente:\n" + "\n".join(erros))

        cur = self._cursor()
        for item in itens:
            # Baixa estoque
            cur.execute(
                "UPDATE Estoque SET Quantidade = Quantidade - ? WHERE IDProduto = ?",
                (item.quantidade, item.id_produto),
            )
            # Movimentação de saída
            cur.execute(
                """
                INSERT INTO MovimentacaoEstoque
                    (IDProduto, TipoMovimentacao, Quantidade, IDPedido, IDNotaFiscal, IDUsuario, Observacao)
                VALUES (?, 'SAIDA', ?, ?, 0, ?, ?)
                """,
                (
                    item.id_produto,
                    item.quantidade,
                    id_pedido,
                    id_usuario,
                    f"Saída por pedido #{id_pedido}",
                ),
            )

        cur.execute(
            "UPDATE Pedido SET Status = 'CONFIRMADO' WHERE IDPedido = ?",
            (id_pedido,),
        )
        self._conn.commit()
        cur.close()

    def cancelar_pedido(self, id_pedido: int, id_usuario: int) -> None:
        """
        Cancela o pedido. Se já estava CONFIRMADO, estorna o estoque.

        Raises:
            ValueError: se status não permite cancelamento (ENTREGUE).
        """
        cur = self._cursor()
        cur.execute("SELECT Status FROM Pedido WHERE IDPedido = ?", (id_pedido,))
        row = cur.fetchone()
        if row is None:
            raise ValueError("Pedido não encontrado.")
        status_atual = str(row[0])

        if status_atual == "ENTREGUE":
            raise ValueError("Pedidos entregues não podem ser cancelados.")

        # Estorna estoque se já havia baixado
        if status_atual in ("CONFIRMADO", "PREPARANDO", "ENVIADO"):
            itens = self.listar_itens(id_pedido)
            for item in itens:
                cur.execute(
                    "UPDATE Estoque SET Quantidade = Quantidade + ? WHERE IDProduto = ?",
                    (item.quantidade, item.id_produto),
                )
                cur.execute(
                    """
                    INSERT INTO MovimentacaoEstoque
                        (IDProduto, TipoMovimentacao, Quantidade, IDPedido, IDNotaFiscal, IDUsuario, Observacao)
                    VALUES (?, 'ENTRADA', ?, ?, 0, ?, ?)
                    """,
                    (
                        item.id_produto,
                        item.quantidade,
                        id_pedido,
                        id_usuario,
                        f"Estorno por cancelamento do pedido #{id_pedido}",
                    ),
                )

        cur.execute(
            "UPDATE Pedido SET Status = 'CANCELADO' WHERE IDPedido = ?",
            (id_pedido,),
        )
        self._conn.commit()
        cur.close()

    def avancar_status(self, id_pedido: int) -> str:
        """
        Avança o status: CONFIRMADO→PREPARANDO→ENVIADO→ENTREGUE.
        Retorna o novo status.

        Raises:
            ValueError: se o status atual não pode avançar.
        """
        cur = self._cursor()
        cur.execute("SELECT Status FROM Pedido WHERE IDPedido = ?", (id_pedido,))
        row = cur.fetchone()
        if row is None:
            raise ValueError("Pedido não encontrado.")
        status_atual = str(row[0])

        novo_status = STATUS_AVANCAR.get(status_atual)
        if novo_status is None:
            raise ValueError(f"Status '{status_atual}' não pode ser avançado.")

        cur.execute(
            "UPDATE Pedido SET Status = ? WHERE IDPedido = ?",
            (novo_status, id_pedido),
        )
        self._conn.commit()
        cur.close()
        return novo_status

    # ------------------------------------------------------------------
    # Nota Fiscal
    # ------------------------------------------------------------------

    def emitir_nota_fiscal(
        self,
        id_pedido: int,
        id_emitente: int,
        id_destinatario: int,
        observacoes: str = "",
    ) -> int:
        """
        Emite uma NF de saída para o pedido.
        Retorna o ID da NotaFiscal criada.

        Raises:
            ValueError: se o pedido não estiver CONFIRMADO ou superior.
        """
        cur = self._cursor()
        cur.execute(
            "SELECT Status, ValorTotal FROM Pedido WHERE IDPedido = ?",
            (id_pedido,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Pedido não encontrado.")
        status, valor = str(row[0]), float(row[1]) if row[1] else 0.0

        if status in ("PENDENTE", "CANCELADO"):
            raise ValueError(
                f"Não é possível emitir NF para pedido com status '{status}'."
            )

        cur.execute(
            """
            INSERT INTO NotaFiscal
                (IDPedido, DataEmissao, ValorTotal, Status, TipoNota,
                 IDEmitente, IDDestinatario, Observacoes)
            VALUES (?, NOW(), ?, 'EMITIDA', 'SAIDA', ?, ?, ?)
            """,
            (id_pedido, valor, id_emitente, id_destinatario, observacoes or None),
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        row_id = cur.fetchone()
        if row_id is None:
            self._conn.rollback()
            raise ConexaoError("Banco não retornou o ID da NF criada.")
        id_nota = int(row_id[0])
        self._conn.commit()
        cur.close()
        return id_nota

    def buscar_nota_fiscal(self, id_pedido: int) -> NotaFiscal | None:
        """Retorna a NF mais recente de um pedido, ou None."""
        cur = self._cursor()
        cur.execute(
            """
            SELECT
                nf.IDNotaFiscal,
                nf.IDPedido,
                nf.DataEmissao,
                nf.ValorTotal,
                nf.Status,
                nf.TipoNota,
                nf.IDEmitente,
                emit.Nome  AS NomeEmitente,
                nf.IDDestinatario,
                dest.Nome  AS NomeDestinatario,
                nf.Observacoes,
                nf.XMLNotaFiscal
            FROM NotaFiscal nf
            JOIN Entidade emit ON emit.IDEntidade = nf.IDEmitente
            JOIN Entidade dest ON dest.IDEntidade = nf.IDDestinatario
            WHERE nf.IDPedido = ?
            ORDER BY nf.IDNotaFiscal DESC
            LIMIT 1
            """,
            (id_pedido,),
        )
        row = cur.fetchone()
        cur.close()
        if row is None:
            return None
        return NotaFiscal(
            id_nota=int(row[0]),
            id_pedido=int(row[1]),
            data_emissao=row[2],
            valor_total=float(row[3]) if row[3] else 0.0,
            status=str(row[4]),
            tipo_nota=str(row[5]),
            id_emitente=int(row[6]),
            nome_emitente=str(row[7]),
            id_destinatario=int(row[8]),
            nome_destinatario=str(row[9]),
            observacoes=str(row[10]) if row[10] else "",
            xml_nota=str(row[11]) if row[11] else "",
        )

    # ------------------------------------------------------------------
    # Clientes (para seleção no formulário)
    # ------------------------------------------------------------------

    def listar_clientes(self) -> list[tuple[int, str]]:
        """Retorna [(id, nome)] de entidades marcadas como cliente e ativas."""
        cur = self._cursor()
        cur.execute(
            """
            SELECT IDEntidade, Nome
            FROM Entidade
            WHERE EhCliente = TRUE AND Ativo = TRUE
            ORDER BY Nome
            """
        )
        rows = cur.fetchall()
        cur.close()
        return [(int(r[0]), str(r[1])) for r in rows]

    def listar_enderecos_cliente(self, id_cliente: int) -> list[tuple[int, str]]:
        """Retorna [(id_endereco, descricao)] dos endereços de um cliente."""
        cur = self._cursor()
        cur.execute(
            """
            SELECT eb.IDEndereco,
                   CONCAT(eb.Logradouro, ', ', eb.Numero,
                          IF(eb.Complemento IS NOT NULL, CONCAT(' ', eb.Complemento), ''),
                          ' - ', eb.Cidade, '/', eb.Estado) AS Descricao
            FROM EnderecoBase eb
            JOIN EntidadeEndereco ee ON ee.IDEndereco = eb.IDEndereco
            WHERE ee.IDEntidade = ? AND eb.Ativo = TRUE
            ORDER BY eb.Principal DESC, eb.Logradouro
            """,
            (id_cliente,),
        )
        rows = cur.fetchall()
        cur.close()
        return [(int(r[0]), str(r[1])) for r in rows]
