"""
repositories/usuario_repo.py
-----------------------------
Repositório de usuários — todo SQL relacionado às tabelas
Usuario, Perfil e UsuarioPerfil fica aqui.
As telas nunca escrevem SQL diretamente.

Schema:
    Usuario       (IDUsuario, Login, SenhaHash)
    Perfil        (IDPerfil, Nome)               -- ex: 'ADM', 'FUNCIONARIO'
    UsuarioPerfil (IDUsuario, IDPerfil)          -- N:N, mas na prática 1 perfil por user
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from database.conexao import ConexaoError, obter_conexao

# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


@dataclass
class Usuario:
    """Representa um usuário do sistema com seus dados de identificação e perfil."""

    id: int
    login: str
    nome_completo: str  # buscado junto via JOIN com Perfil/UsuarioPerfil se disponível
    perfil: str  # nome do perfil: 'ADM' | 'FUNCIONARIO'
    ativo: bool = (
        True  # controlado pela presença/ausência em UsuarioPerfil ou campo Ativo
    )

    # Nota: se a tabela Usuario não tiver NomeCompleto, adicione a coluna ou
    # use uma tabela auxiliar. O repo assume que NomeCompleto existe em Usuario.


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _row_para_usuario(row: Any) -> Usuario:
    """Converte uma linha (IDUsuario, Login, NomeCompleto, Perfil, Ativo) → Usuario."""
    return Usuario(
        id=int(row[0]),
        login=str(row[1]),
        nome_completo=str(row[2]),
        perfil=str(row[3]),
        ativo=bool(row[4]) if len(row) > 4 else True,
    )


def _perfil_id(conn, nome_perfil: str) -> int:
    """Retorna o IDPerfil pelo nome. Lança ValueError se não encontrar."""
    cursor = conn.cursor()
    cursor.execute("SELECT IDPerfil FROM Perfil WHERE Nome = ?", (nome_perfil,))
    row = cursor.fetchone()
    cursor.close()
    if row is None:
        raise ValueError(f"Perfil '{nome_perfil}' não encontrado na tabela Perfil.")
    return int(row[0])


# ---------------------------------------------------------------------------
# SELECT
# ---------------------------------------------------------------------------

# SQL base — supõe que Usuario tem: IDUsuario, Login, SenhaHash, NomeCompleto, Ativo
# e que Perfil tem: IDPerfil, Nome
_SELECT_BASE = """
    SELECT u.IDUsuario,
           u.Login,
           u.NomeCompleto,
           p.Nome   AS Perfil,
           u.Ativo
    FROM   Usuario u
    JOIN   UsuarioPerfil up ON up.IDUsuario = u.IDUsuario
    JOIN   Perfil        p  ON p.IDPerfil  = up.IDPerfil
"""


def listar(apenas_ativos: bool = True) -> list[Usuario]:
    """Retorna todos os usuários, com filtro opcional de ativos."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        sql = _SELECT_BASE
        if apenas_ativos:
            sql += " WHERE u.Ativo = 1"
        sql += " ORDER BY u.NomeCompleto"
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
    return [_row_para_usuario(r) for r in rows]


def buscar_por_id(id_usuario: int) -> Usuario | None:
    """Busca um usuário pelo ID. Retorna None se não encontrado."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _SELECT_BASE + " WHERE u.IDUsuario = ?",
            (id_usuario,),
        )
        row = cursor.fetchone()
        cursor.close()
    return _row_para_usuario(row) if row else None


def buscar_por_login_e_senha(login: str, senha_hash: str) -> Usuario | None:
    """
    Busca um usuário pelo login e hash de senha.
    Retorna None se não encontrado, inativo ou senha incorreta.
    """
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute(
            _SELECT_BASE + " WHERE u.Login = ? AND u.SenhaHash = ? AND u.Ativo = 1",
            (login, senha_hash),
        )
        row = cursor.fetchone()
        cursor.close()
    return _row_para_usuario(row) if row else None


def login_existe(login: str, exceto_id: int | None = None) -> bool:
    """
    Verifica se um login já está cadastrado.
    exceto_id: ignora o próprio usuário (útil ao editar).
    """
    with obter_conexao() as conn:
        cursor = conn.cursor()
        if exceto_id is not None:
            cursor.execute(
                "SELECT 1 FROM Usuario WHERE Login = ? AND IDUsuario <> ?",
                (login, exceto_id),
            )
        else:
            cursor.execute("SELECT 1 FROM Usuario WHERE Login = ?", (login,))
        existe = cursor.fetchone() is not None
        cursor.close()
    return existe


def existe_adm() -> bool:
    """Retorna True se já existe pelo menos um usuário com perfil ADM ativo."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM   Usuario u
            JOIN   UsuarioPerfil up ON up.IDUsuario = u.IDUsuario
            JOIN   Perfil        p  ON p.IDPerfil  = up.IDPerfil
            WHERE  p.Nome = 'ADM' AND u.Ativo = 1
            """
        )
        row = cursor.fetchone()
        cursor.close()
    return bool(row and row[0] > 0)


# ---------------------------------------------------------------------------
# INSERT
# ---------------------------------------------------------------------------


def cadastrar(
    login: str,
    senha_hash: str,
    nome_completo: str,
    perfil: str,
) -> None:
    """
    Insere um novo usuário e associa ao perfil informado.

    Raises:
        pyodbc.IntegrityError: se o login já existir.
        ValueError: se o perfil não existir na tabela Perfil.
    """
    with obter_conexao() as conn:
        id_perfil = _perfil_id(conn, perfil)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Usuario (Login, SenhaHash, NomeCompleto, Ativo)
            VALUES (?, ?, ?, 1)
            """,
            (login, senha_hash, nome_completo),
        )
        # Recupera o ID gerado
        cursor.execute("SELECT LAST_INSERT_ID()")
        row = cursor.fetchone()
        if row is None:
            raise ConexaoError("Não foi possível obter o ID do usuário inserido.")
        id_usuario = row[0]

        cursor.execute(
            "INSERT INTO UsuarioPerfil (IDUsuario, IDPerfil) VALUES (?, ?)",
            (id_usuario, id_perfil),
        )
        conn.commit()
        cursor.close()


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


def atualizar(
    id_usuario: int,
    login: str,
    nome_completo: str,
    perfil: str,
    senha_hash: str | None = None,
) -> None:
    """
    Atualiza login, nome e perfil de um usuário.
    Se senha_hash for None, a senha não é alterada.

    Raises:
        ValueError: se o perfil não existir.
    """
    with obter_conexao() as conn:
        id_perfil = _perfil_id(conn, perfil)
        cursor = conn.cursor()

        if senha_hash is not None:
            cursor.execute(
                """
                UPDATE Usuario
                SET Login = ?, NomeCompleto = ?, SenhaHash = ?
                WHERE IDUsuario = ?
                """,
                (login, nome_completo, senha_hash, id_usuario),
            )
        else:
            cursor.execute(
                """
                UPDATE Usuario
                SET Login = ?, NomeCompleto = ?
                WHERE IDUsuario = ?
                """,
                (login, nome_completo, id_usuario),
            )

        # Atualiza perfil (remove antigo, insere novo)
        cursor.execute(
            "DELETE FROM UsuarioPerfil WHERE IDUsuario = ?",
            (id_usuario,),
        )
        cursor.execute(
            "INSERT INTO UsuarioPerfil (IDUsuario, IDPerfil) VALUES (?, ?)",
            (id_usuario, id_perfil),
        )
        conn.commit()
        cursor.close()


def desativar(id_usuario: int) -> None:
    """Marca o usuário como inativo (soft delete)."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Usuario SET Ativo = 0 WHERE IDUsuario = ?",
            (id_usuario,),
        )
        conn.commit()
        cursor.close()


def reativar(id_usuario: int) -> None:
    """Reativa um usuário previamente desativado."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Usuario SET Ativo = 1 WHERE IDUsuario = ?",
            (id_usuario,),
        )
        conn.commit()
        cursor.close()


def redefinir_senha(id_usuario: int, senha_hash: str) -> None:
    """Redefine apenas a senha de um usuário."""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Usuario SET SenhaHash = ? WHERE IDUsuario = ?",
            (senha_hash, id_usuario),
        )
        conn.commit()
        cursor.close()
