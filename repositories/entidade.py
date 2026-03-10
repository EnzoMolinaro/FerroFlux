"""
repositories/entidade_repo.py
------------------------------
Repositório de entidades (clientes e/ou fornecedores).

Uma Entidade é qualquer pessoa física (CPF) ou jurídica (CNPJ) cadastrada
no sistema. A mesma entidade pode ser cliente E fornecedor ao mesmo tempo.

Tabelas envolvidas:
    Entidade, Contato, EnderecoBase, Bairro, Cidade, EntidadeEndereco

Uso:
    from repositories.entidade_repo import EntidadeRepo, Entidade, Contato, Endereco

    with obter_conexao() as conn:
        repo = EntidadeRepo(conn)

        # Listar clientes ativos
        clientes = repo.listar(apenas_clientes=True)

        # Listar fornecedores ativos
        fornecedores = repo.listar(apenas_fornecedores=True)

        # Inserir novo cliente PF
        repo.inserir(Entidade(
            nome="João Silva",
            cpf="123.456.789-00",
            eh_cliente=True,
            contatos=[Contato(tipo="CELULAR", valor="(11) 91234-5678", principal=True)],
        ))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


@dataclass
class Contato:
    """Um meio de contato de uma entidade."""

    tipo: str  # 'EMAIL' | 'TELEFONE' | 'CELULAR' | 'WHATSAPP'
    valor: str
    principal: bool = False
    id: int | None = field(default=None, repr=False)


@dataclass
class Endereco:
    """Endereço completo com cidade/bairro desnormalizados para exibição."""

    logradouro: str
    numero: str = ""
    complemento: str = ""
    cep: str = ""
    bairro: str = ""
    cidade: str = ""
    estado: str = ""
    tipo: str = "COMERCIAL"  # 'RESIDENCIAL'|'COMERCIAL'|'ENTREGA'|'COBRANCA'
    principal: bool = False

    # IDs internos — necessários para gravar no banco
    id_endereco: int | None = field(default=None, repr=False)
    id_bairro: int | None = field(default=None, repr=False)
    id_cidade: int | None = field(default=None, repr=False)


@dataclass
class Entidade:
    """Representa um cliente e/ou fornecedor."""

    nome: str
    cpf: str | None = None
    cnpj: str | None = None
    eh_cliente: bool = False
    eh_fornecedor: bool = False
    ativo: bool = True
    observacoes: str = ""

    # Relacionamentos carregados sob demanda
    contatos: list[Contato] = field(default_factory=list)
    enderecos: list[Endereco] = field(default_factory=list)

    # Preenchido após busca / inserção
    id: int | None = field(default=None, repr=False)
    data_criacao: datetime | None = field(default=None, repr=False)

    # ----------------------------------------------------------------
    # Helpers de leitura
    # ----------------------------------------------------------------

    @property
    def documento(self) -> str:
        """Retorna CPF ou CNPJ formatado para exibição."""
        return self.cpf or self.cnpj or "—"

    @property
    def tipo_pessoa(self) -> str:
        return "PF" if self.cpf else "PJ"

    @property
    def contato_principal(self) -> str:
        """Retorna valor do contato marcado como principal, ou o primeiro."""
        for c in self.contatos:
            if c.principal:
                return f"{c.tipo}: {c.valor}"
        return self.contatos[0].valor if self.contatos else "—"

    @property
    def endereco_principal(self) -> Endereco | None:
        for e in self.enderecos:
            if e.principal:
                return e
        return self.enderecos[0] if self.enderecos else None


# ---------------------------------------------------------------------------
# SQL base
# ---------------------------------------------------------------------------

_SQL_SELECT_ENTIDADE = """
    SELECT
        e.IDEntidade,
        e.Nome,
        e.CPF,
        e.CNPJ,
        e.EhCliente,
        e.EhFornecedor,
        e.Ativo,
        e.DataCriacao,
        e.Observacoes
    FROM Entidade e
"""


# ---------------------------------------------------------------------------
# Repositório
# ---------------------------------------------------------------------------


class EntidadeRepo:
    """
    CRUD completo de entidades (clientes / fornecedores).
    Requer uma conexão pyodbc aberta — NÃO gerencia seu ciclo de vida.
    """

    def __init__(self, conn: pyodbc.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _cursor(self) -> pyodbc.Cursor:
        return self._conn.cursor()

    @staticmethod
    def _row_para_entidade(row: pyodbc.Row) -> Entidade:
        return Entidade(
            id=int(row[0]),
            nome=str(row[1]),
            cpf=str(row[2]) if row[2] is not None else None,
            cnpj=str(row[3]) if row[3] is not None else None,
            eh_cliente=bool(row[4]),
            eh_fornecedor=bool(row[5]),
            ativo=bool(row[6]),
            data_criacao=row[7],
            observacoes=str(row[8]) if row[8] is not None else "",
        )

    # ------------------------------------------------------------------
    # Consultas — listagem
    # ------------------------------------------------------------------

    def listar(
        self,
        apenas_clientes: bool = False,
        apenas_fornecedores: bool = False,
        apenas_ativos: bool = True,
    ) -> list[Entidade]:
        """
        Lista entidades com filtros opcionais.

        Parâmetros:
            apenas_clientes:     retorna só quem tem EhCliente = TRUE
            apenas_fornecedores: retorna só quem tem EhFornecedor = TRUE
            apenas_ativos:       filtra por Ativo = TRUE
        """
        condicoes: list[str] = []
        if apenas_ativos:
            condicoes.append("e.Ativo = TRUE")
        if apenas_clientes:
            condicoes.append("e.EhCliente = TRUE")
        if apenas_fornecedores:
            condicoes.append("e.EhFornecedor = TRUE")

        where = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
        cur = self._cursor()
        cur.execute(f"{_SQL_SELECT_ENTIDADE} {where} ORDER BY e.Nome")
        rows: list[pyodbc.Row] = cur.fetchall()
        cur.close()
        return [self._row_para_entidade(r) for r in rows]

    def buscar_por_id(
        self, id_entidade: int, carregar_detalhes: bool = True
    ) -> Entidade | None:
        """
        Retorna uma entidade pelo ID.

        Parâmetros:
            carregar_detalhes: se True, carrega contatos e endereços também.
        """
        cur = self._cursor()
        cur.execute(
            f"{_SQL_SELECT_ENTIDADE} WHERE e.IDEntidade = ?",
            (id_entidade,),
        )
        row: pyodbc.Row | None = cur.fetchone()
        cur.close()
        if row is None:
            return None
        entidade = self._row_para_entidade(row)
        if carregar_detalhes:
            entidade.contatos = self.listar_contatos(id_entidade)
            entidade.enderecos = self.listar_enderecos(id_entidade)
        return entidade

    def buscar_por_nome(self, termo: str) -> list[Entidade]:
        """Busca por nome (case-insensitive, contém)."""
        cur = self._cursor()
        cur.execute(
            f"{_SQL_SELECT_ENTIDADE} WHERE e.Nome LIKE ? ORDER BY e.Nome",
            (f"%{termo}%",),
        )
        rows: list[pyodbc.Row] = cur.fetchall()
        cur.close()
        return [self._row_para_entidade(r) for r in rows]

    def buscar_por_documento(self, documento: str) -> Entidade | None:
        """Busca por CPF ou CNPJ exatos."""
        cur = self._cursor()
        cur.execute(
            f"{_SQL_SELECT_ENTIDADE} WHERE e.CPF = ? OR e.CNPJ = ?",
            (documento, documento),
        )
        row: pyodbc.Row | None = cur.fetchone()
        cur.close()
        return self._row_para_entidade(row) if row is not None else None

    def documento_existe(
        self, cpf: str | None, cnpj: str | None, ignorar_id: int | None = None
    ) -> bool:
        """Verifica se CPF ou CNPJ já estão em uso por outra entidade."""
        cur = self._cursor()
        resultado = False
        if cpf:
            if ignorar_id is not None:
                cur.execute(
                    "SELECT 1 FROM Entidade WHERE CPF = ? AND IDEntidade <> ?",
                    (cpf, ignorar_id),
                )
            else:
                cur.execute("SELECT 1 FROM Entidade WHERE CPF = ?", (cpf,))
            if cur.fetchone() is not None:
                resultado = True
        if not resultado and cnpj:
            if ignorar_id is not None:
                cur.execute(
                    "SELECT 1 FROM Entidade WHERE CNPJ = ? AND IDEntidade <> ?",
                    (cnpj, ignorar_id),
                )
            else:
                cur.execute("SELECT 1 FROM Entidade WHERE CNPJ = ?", (cnpj,))
            if cur.fetchone() is not None:
                resultado = True
        cur.close()
        return resultado

    # ------------------------------------------------------------------
    # Contatos
    # ------------------------------------------------------------------

    def listar_contatos(self, id_entidade: int) -> list[Contato]:
        cur = self._cursor()
        cur.execute(
            """
            SELECT IDContato, TipoContato, Valor, Principal
            FROM Contato
            WHERE IDEntidade = ?
            ORDER BY Principal DESC, IDContato
            """,
            (id_entidade,),
        )
        rows: list[pyodbc.Row] = cur.fetchall()
        cur.close()
        return [
            Contato(
                id=int(r[0]),
                tipo=str(r[1]),
                valor=str(r[2]),
                principal=bool(r[3]),
            )
            for r in rows
        ]

    def salvar_contatos(self, id_entidade: int, contatos: list[Contato]) -> None:
        """
        Substitui todos os contatos da entidade pelos fornecidos.
        (delete + insert — simples e seguro para listas pequenas)
        """
        cur = self._cursor()
        cur.execute("DELETE FROM Contato WHERE IDEntidade = ?", (id_entidade,))
        for c in contatos:
            if not c.valor.strip():
                continue
            cur.execute(
                """
                INSERT INTO Contato (IDEntidade, TipoContato, Valor, Principal)
                VALUES (?, ?, ?, ?)
                """,
                (id_entidade, c.tipo, c.valor.strip(), c.principal),
            )
        cur.close()

    # ------------------------------------------------------------------
    # Endereços
    # ------------------------------------------------------------------

    def listar_enderecos(self, id_entidade: int) -> list[Endereco]:
        cur = self._cursor()
        cur.execute(
            """
            SELECT
                eb.IDEndereco,
                eb.Logradouro,
                eb.Numero,
                eb.Complemento,
                eb.CEP,
                ba.IDBairro,
                ba.Nome        AS Bairro,
                ci.IDCidade,
                ci.Nome        AS Cidade,
                ci.Estado,
                ee.TipoEndereco,
                ee.Principal
            FROM EntidadeEndereco ee
            JOIN EnderecoBase eb ON eb.IDEndereco = ee.IDEndereco
            JOIN Bairro ba       ON ba.IDBairro   = eb.IDBairro
            JOIN Cidade ci       ON ci.IDCidade   = ba.IDCidade
            WHERE ee.IDEntidade = ?
            ORDER BY ee.Principal DESC, eb.IDEndereco
            """,
            (id_entidade,),
        )
        rows: list[pyodbc.Row] = cur.fetchall()
        cur.close()
        return [
            Endereco(
                id_endereco=int(r[0]),
                logradouro=str(r[1]),
                numero=str(r[2]) if r[2] else "",
                complemento=str(r[3]) if r[3] else "",
                cep=str(r[4]) if r[4] else "",
                id_bairro=int(r[5]),
                bairro=str(r[6]),
                id_cidade=int(r[7]),
                cidade=str(r[8]),
                estado=str(r[9]),
                tipo=str(r[10]),
                principal=bool(r[11]),
            )
            for r in rows
        ]

    def _obter_ou_criar_cidade(self, cur: pyodbc.Cursor, nome: str, estado: str) -> int:
        cur.execute(
            "SELECT IDCidade FROM Cidade WHERE Nome = ? AND Estado = ?",
            (nome.strip(), estado.strip()),
        )
        row: pyodbc.Row | None = cur.fetchone()
        if row is not None:
            return int(row[0])
        cur.execute(
            "INSERT INTO Cidade (Nome, Estado) VALUES (?, ?)",
            (nome.strip(), estado.strip()),
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        row_id: pyodbc.Row | None = cur.fetchone()
        if row_id is None:
            raise ConexaoError("Falha ao obter ID da cidade inserida.")
        return int(row_id[0])

    def _obter_ou_criar_bairro(
        self, cur: pyodbc.Cursor, nome: str, id_cidade: int
    ) -> int:
        cur.execute(
            "SELECT IDBairro FROM Bairro WHERE Nome = ? AND IDCidade = ?",
            (nome.strip(), id_cidade),
        )
        row: pyodbc.Row | None = cur.fetchone()
        if row is not None:
            return int(row[0])
        cur.execute(
            "INSERT INTO Bairro (Nome, IDCidade) VALUES (?, ?)",
            (nome.strip(), id_cidade),
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        row_id: pyodbc.Row | None = cur.fetchone()
        if row_id is None:
            raise ConexaoError("Falha ao obter ID do bairro inserido.")
        return int(row_id[0])

    def salvar_enderecos(self, id_entidade: int, enderecos: list[Endereco]) -> None:
        """
        Substitui todos os endereços da entidade pelos fornecidos.
        Cria Cidade e Bairro automaticamente se não existirem.
        """
        cur = self._cursor()

        # Remove vínculos anteriores (EntidadeEndereco)
        cur.execute(
            "DELETE FROM EntidadeEndereco WHERE IDEntidade = ?",
            (id_entidade,),
        )

        for e in enderecos:
            if not e.logradouro.strip():
                continue

            # Resolve Cidade e Bairro
            if e.id_cidade is None:
                e.id_cidade = self._obter_ou_criar_cidade(cur, e.cidade, e.estado)
            if e.id_bairro is None:
                e.id_bairro = self._obter_ou_criar_bairro(cur, e.bairro, e.id_cidade)

            # Insere ou reusa EnderecoBase
            if e.id_endereco is None:
                cur.execute(
                    """
                    INSERT INTO EnderecoBase (Logradouro, Numero, Complemento, CEP, IDBairro)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        e.logradouro.strip(),
                        e.numero.strip() or None,
                        e.complemento.strip() or None,
                        e.cep.strip() or None,
                        e.id_bairro,
                    ),
                )
                cur.execute("SELECT LAST_INSERT_ID()")
                row_id: pyodbc.Row | None = cur.fetchone()
                if row_id is None:
                    raise ConexaoError("Falha ao obter ID do endereço inserido.")
                e.id_endereco = int(row_id[0])

            # Vincula EntidadeEndereco
            cur.execute(
                """
                INSERT INTO EntidadeEndereco (IDEntidade, IDEndereco, TipoEndereco, Principal)
                VALUES (?, ?, ?, ?)
                """,
                (id_entidade, e.id_endereco, e.tipo, e.principal),
            )

        cur.close()

    # ------------------------------------------------------------------
    # Escrita — Entidade
    # ------------------------------------------------------------------

    def inserir(self, entidade: Entidade) -> int:
        """
        Insere entidade + contatos + endereços em uma única transação.

        Retorna:
            ID da entidade criada.
        """
        if not entidade.cpf and not entidade.cnpj:
            raise ValueError("Entidade deve ter CPF ou CNPJ.")
        if not entidade.eh_cliente and not entidade.eh_fornecedor:
            raise ValueError("Entidade deve ser cliente e/ou fornecedor.")

        cur = self._cursor()
        cur.execute(
            """
            INSERT INTO Entidade (Nome, CPF, CNPJ, EhCliente, EhFornecedor, Ativo, Observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entidade.nome,
                entidade.cpf or None,
                entidade.cnpj or None,
                entidade.eh_cliente,
                entidade.eh_fornecedor,
                entidade.ativo,
                entidade.observacoes or None,
            ),
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        row_id: pyodbc.Row | None = cur.fetchone()
        if row_id is None:
            self._conn.rollback()
            raise ConexaoError("Banco não retornou o ID da entidade inserida.")
        id_entidade = int(row_id[0])
        cur.close()

        entidade.id = id_entidade

        if entidade.contatos:
            self.salvar_contatos(id_entidade, entidade.contatos)
        if entidade.enderecos:
            self.salvar_enderecos(id_entidade, entidade.enderecos)

        self._conn.commit()
        return id_entidade

    def atualizar(self, entidade: Entidade) -> None:
        """
        Atualiza dados da entidade + substitui contatos e endereços.

        Raises:
            ValueError: se entidade.id for None.
        """
        if entidade.id is None:
            raise ValueError("Entidade sem ID — use inserir() para novos registros.")

        id_entidade: int = entidade.id
        cur = self._cursor()
        cur.execute(
            """
            UPDATE Entidade
            SET Nome = ?, CPF = ?, CNPJ = ?, EhCliente = ?, EhFornecedor = ?,
                Ativo = ?, Observacoes = ?
            WHERE IDEntidade = ?
            """,
            (
                entidade.nome,
                entidade.cpf or None,
                entidade.cnpj or None,
                entidade.eh_cliente,
                entidade.eh_fornecedor,
                entidade.ativo,
                entidade.observacoes or None,
                id_entidade,
            ),
        )
        cur.close()

        self.salvar_contatos(id_entidade, entidade.contatos)
        self.salvar_enderecos(id_entidade, entidade.enderecos)

        self._conn.commit()

    def desativar(self, id_entidade: int) -> None:
        """Soft delete."""
        cur = self._cursor()
        cur.execute(
            "UPDATE Entidade SET Ativo = FALSE WHERE IDEntidade = ?",
            (id_entidade,),
        )
        self._conn.commit()
        cur.close()

    def reativar(self, id_entidade: int) -> None:
        cur = self._cursor()
        cur.execute(
            "UPDATE Entidade SET Ativo = TRUE WHERE IDEntidade = ?",
            (id_entidade,),
        )
        self._conn.commit()
        cur.close()
