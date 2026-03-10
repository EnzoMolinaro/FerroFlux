"""
repositories/material_repo.py
------------------------------
Repositório de materiais (ProdutoBase + Estoque + HistoricoPrecos).

Responsabilidades:
    - CRUD completo de produtos/materiais
    - Gestão de estoque (consulta, ajuste)
    - Registro de preços via HistoricoPrecos

Uso:
    from repositories.material_repo import MaterialRepo, Material
    from database.conexao import obter_conexao

    with obter_conexao() as conn:
        repo  = MaterialRepo(conn)
        todos = repo.listar_todos()
        repo.inserir(Material(nome="Chapa de Aço", unidade="KG", preco_custo=15.00, preco_venda=22.50))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError

# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


@dataclass
class Material:
    """Representa um material/produto com estoque e preço atual."""

    nome: str
    unidade: str = "KG"
    descricao: str = ""
    codigo_barras: str | None = None
    preco_custo: float = 0.0
    preco_venda: float = 0.0
    estoque_atual: float = 0.0
    estoque_minimo: float = 0.0
    localizacao: str = ""
    ativo: bool = True

    # preenchido após busca / inserção
    id: int | None = field(default=None, repr=False)
    data_criacao: datetime | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# SQL base compartilhado pelas consultas de leitura
# ---------------------------------------------------------------------------

_SQL_SELECT = """
    SELECT
        p.IDProduto,
        p.Nome,
        p.Descricao,
        p.CodigoBarras,
        p.UnidadeMedida,
        p.Ativo,
        p.DataCriacao,
        COALESCE(e.Quantidade,    0)  AS Estoque,
        COALESCE(e.EstoqueMinimo, 0)  AS EstoqueMinimo,
        COALESCE(e.Localizacao,  '')  AS Localizacao,
        COALESCE(hp.PrecoCusto,   0)  AS PrecoCusto,
        COALESCE(hp.PrecoVenda,   0)  AS PrecoVenda
    FROM ProdutoBase p
    LEFT JOIN Estoque e
           ON e.IDProduto = p.IDProduto
    LEFT JOIN HistoricoPrecos hp
           ON hp.IDProduto = p.IDProduto
          AND hp.IDHistoricoPreco = (
              SELECT MAX(IDHistoricoPreco)
              FROM HistoricoPrecos
              WHERE IDProduto = p.IDProduto
          )
"""


# ---------------------------------------------------------------------------
# Repositório
# ---------------------------------------------------------------------------


class MaterialRepo:
    """
    Todas as operações de banco relacionadas a materiais.
    Requer uma conexão pyodbc aberta — NÃO gerencia seu ciclo de vida.

    Parâmetros:
        conn: conexão aberta obtida via obter_conexao()
    """

    def __init__(self, conn: pyodbc.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _cursor(self) -> pyodbc.Cursor:
        return self._conn.cursor()

    @staticmethod
    def _row_para_material(row: pyodbc.Row) -> Material:
        return Material(
            id=int(row[0]),
            nome=str(row[1]),
            descricao=str(row[2]) if row[2] is not None else "",
            codigo_barras=str(row[3]) if row[3] is not None else None,
            unidade=str(row[4]) if row[4] is not None else "KG",
            ativo=bool(row[5]),
            data_criacao=row[6],
            estoque_atual=float(row[7]) if row[7] is not None else 0.0,
            estoque_minimo=float(row[8]) if row[8] is not None else 0.0,
            localizacao=str(row[9]) if row[9] is not None else "",
            preco_custo=float(row[10]) if row[10] is not None else 0.0,
            preco_venda=float(row[11]) if row[11] is not None else 0.0,
        )

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def listar_todos(self, apenas_ativos: bool = True) -> list[Material]:
        """Retorna todos os materiais com estoque e preço atual."""
        filtro = "WHERE p.Ativo = TRUE" if apenas_ativos else ""
        cur = self._cursor()
        cur.execute(f"{_SQL_SELECT} {filtro} ORDER BY p.Nome")
        rows: list[pyodbc.Row] = cur.fetchall()
        cur.close()
        return [self._row_para_material(r) for r in rows]

    def buscar_por_id(self, id_produto: int) -> Material | None:
        """Retorna um material pelo ID ou None se não encontrado."""
        cur = self._cursor()
        cur.execute(f"{_SQL_SELECT} WHERE p.IDProduto = ?", (id_produto,))
        row: pyodbc.Row | None = cur.fetchone()
        cur.close()
        return self._row_para_material(row) if row is not None else None

    def buscar_por_nome(self, termo: str) -> list[Material]:
        """Busca materiais cujo nome contém o termo (case-insensitive)."""
        cur = self._cursor()
        cur.execute(
            f"{_SQL_SELECT} WHERE p.Nome LIKE ? ORDER BY p.Nome",
            (f"%{termo}%",),
        )
        rows: list[pyodbc.Row] = cur.fetchall()
        cur.close()
        return [self._row_para_material(r) for r in rows]

    def codigo_barras_existe(self, codigo: str, ignorar_id: int | None = None) -> bool:
        """Verifica se um código de barras já está em uso por outro produto."""
        cur = self._cursor()
        if ignorar_id is not None:
            cur.execute(
                "SELECT 1 FROM ProdutoBase WHERE CodigoBarras = ? AND IDProduto <> ?",
                (codigo, ignorar_id),
            )
        else:
            cur.execute(
                "SELECT 1 FROM ProdutoBase WHERE CodigoBarras = ?",
                (codigo,),
            )
        existe = cur.fetchone() is not None
        cur.close()
        return existe

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def inserir(self, material: Material) -> int:
        """
        Insere um novo material no banco.
        Cria também o registro de Estoque e HistoricoPrecos.

        Retorna:
            ID do produto criado.

        Raises:
            ConexaoError: se o banco não retornar o ID inserido.
        """
        cur = self._cursor()

        # 1. ProdutoBase
        cur.execute(
            """
            INSERT INTO ProdutoBase (Nome, Descricao, CodigoBarras, UnidadeMedida, Ativo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                material.nome,
                material.descricao or None,
                material.codigo_barras or None,
                material.unidade,
                material.ativo,
            ),
        )

        cur.execute("SELECT LAST_INSERT_ID()")
        row_id: pyodbc.Row | None = cur.fetchone()
        if row_id is None:
            self._conn.rollback()
            raise ConexaoError("Banco não retornou o ID do produto inserido.")
        id_produto = int(row_id[0])

        # 2. Estoque inicial
        cur.execute(
            """
            INSERT INTO Estoque (IDProduto, Quantidade, EstoqueMinimo, Localizacao, UltimaMovimentacao)
            VALUES (?, ?, ?, ?, NOW())
            """,
            (
                id_produto,
                material.estoque_atual,
                material.estoque_minimo,
                material.localizacao or None,
            ),
        )

        # 3. Preço inicial
        cur.execute(
            """
            INSERT INTO HistoricoPrecos (IDProduto, PrecoCusto, PrecoVenda, DataInicioVigencia)
            VALUES (?, ?, ?, NOW())
            """,
            (id_produto, material.preco_custo, material.preco_venda),
        )

        self._conn.commit()
        cur.close()

        material.id = id_produto
        return id_produto

    def atualizar(self, material: Material) -> None:
        """
        Atualiza os dados do material.
        Se o preço mudou, encerra o registro anterior e abre um novo.

        Raises:
            ValueError: se material.id for None.
        """
        if material.id is None:
            raise ValueError("Material sem ID — use inserir() para novos registros.")

        # Variável local tipada como int para o Pylance não reclamar de int | None
        id_produto: int = material.id
        cur = self._cursor()

        # 1. Atualiza ProdutoBase
        cur.execute(
            """
            UPDATE ProdutoBase
            SET Nome = ?, Descricao = ?, CodigoBarras = ?, UnidadeMedida = ?, Ativo = ?
            WHERE IDProduto = ?
            """,
            (
                material.nome,
                material.descricao or None,
                material.codigo_barras or None,
                material.unidade,
                material.ativo,
                id_produto,
            ),
        )

        # 2. Atualiza Estoque (quantidade não é editada aqui — use ajustar_estoque)
        cur.execute(
            """
            UPDATE Estoque
            SET EstoqueMinimo = ?, Localizacao = ?, UltimaMovimentacao = NOW()
            WHERE IDProduto = ?
            """,
            (material.estoque_minimo, material.localizacao or None, id_produto),
        )

        # 3. Verifica se o preço mudou
        cur.execute(
            """
            SELECT PrecoCusto, PrecoVenda FROM HistoricoPrecos
            WHERE IDProduto = ?
            ORDER BY IDHistoricoPreco DESC
            LIMIT 1
            """,
            (id_produto,),
        )
        row: pyodbc.Row | None = cur.fetchone()
        preco_mudou = row is None or (
            float(row[0]) != material.preco_custo
            or float(row[1]) != material.preco_venda
        )

        if preco_mudou:
            cur.execute(
                """
                UPDATE HistoricoPrecos
                SET DataFimVigencia = NOW()
                WHERE IDProduto = ? AND DataFimVigencia IS NULL
                """,
                (id_produto,),
            )
            cur.execute(
                """
                INSERT INTO HistoricoPrecos (IDProduto, PrecoCusto, PrecoVenda, DataInicioVigencia)
                VALUES (?, ?, ?, NOW())
                """,
                (id_produto, material.preco_custo, material.preco_venda),
            )

        self._conn.commit()
        cur.close()

    def desativar(self, id_produto: int) -> None:
        """Desativa (soft delete) um material."""
        cur = self._cursor()
        cur.execute(
            "UPDATE ProdutoBase SET Ativo = FALSE WHERE IDProduto = ?",
            (id_produto,),
        )
        self._conn.commit()
        cur.close()

    def reativar(self, id_produto: int) -> None:
        """Reativa um material desativado."""
        cur = self._cursor()
        cur.execute(
            "UPDATE ProdutoBase SET Ativo = TRUE WHERE IDProduto = ?",
            (id_produto,),
        )
        self._conn.commit()
        cur.close()

    def ajustar_estoque(
        self,
        id_produto: int,
        quantidade: float,
        observacao: str = "",
        id_usuario: int | None = None,
    ) -> None:
        """
        Registra um ajuste de estoque na tabela MovimentacaoEstoque.
        O trigger trg_movimento_atualizar_estoque cuida de atualizar Estoque.

        Parâmetros:
            id_produto:  ID do produto.
            quantidade:  Valor positivo = entrada, negativo = saída.
            observacao:  Motivo do ajuste.
            id_usuario:  ID do usuário responsável (opcional).
        """
        cur = self._cursor()
        cur.execute(
            """
            INSERT INTO MovimentacaoEstoque
                (IDProduto, TipoMovimentacao, Quantidade, IDPedido, IDNotaFiscal, IDUsuario, Observacao)
            VALUES (?, 'AJUSTE', ?, 0, 0, ?, ?)
            """,
            (id_produto, abs(quantidade), id_usuario, observacao or None),
        )
        self._conn.commit()
        cur.close()
