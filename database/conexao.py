"""
database/conexao.py
-------------------
Módulo central de conexão com o banco de dados MySQL via pyodbc.

Uso:
    from database.conexao import obter_conexao, ConexaoError

    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    except ConexaoError as e:
        # tratar erro de conexão
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------


class ConexaoError(Exception):
    """Lançada quando não é possível estabelecer conexão com o banco."""


class DriverNaoEncontradoError(ConexaoError):
    """Lançada quando nenhum driver MySQL ODBC está instalado no sistema."""


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


@dataclass
class ConfigConexao:
    servidor: str
    porta: int
    usuario: str
    senha: str
    banco: str

    def __str__(self) -> str:
        return f"{self.usuario}@{self.servidor}:{self.porta}/{self.banco}"


# ---------------------------------------------------------------------------
# Estado interno
# ---------------------------------------------------------------------------


class _Estado:
    config: ConfigConexao = ConfigConexao(
        servidor="localhost",
        porta=3307,
        usuario="root",
        senha="",
        banco="ferroflux",
    )
    driver_cache: str | None = None


_DRIVERS_MYSQL: list[str] = [
    "MySQL ODBC 9.4 Unicode Driver",
    "MySQL ODBC 9.4 ANSI Driver",
    "MySQL ODBC 8.0 Unicode Driver",
    "MySQL ODBC 8.0 ANSI Driver",
]


# ---------------------------------------------------------------------------
# Funções internas
# ---------------------------------------------------------------------------


def _detectar_driver() -> str:
    if _Estado.driver_cache is not None:
        return _Estado.driver_cache

    try:
        import pyodbc  # type: ignore[import-untyped]
    except ImportError as exc:
        raise DriverNaoEncontradoError(
            "pyodbc não está instalado.\n" "Execute: pip install pyodbc"
        ) from exc

    for driver in _DRIVERS_MYSQL:
        if driver in pyodbc.drivers():
            _Estado.driver_cache = driver
            return driver

    raise DriverNaoEncontradoError(
        "Nenhum driver MySQL ODBC encontrado no sistema.\n"
        "Instale o MySQL Connector/ODBC em:\n"
        "https://dev.mysql.com/downloads/connector/odbc/"
    )


def _montar_string_conexao(config: ConfigConexao, driver: str) -> str:
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={config.servidor};"
        f"PORT={config.porta};"
        f"DATABASE={config.banco};"
        f"UID={config.usuario};"
        f"PWD={config.senha};"
        f"CHARSET=utf8mb4;"
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def configurar(config: ConfigConexao) -> None:
    """Define a configuração de conexão ativa."""
    _Estado.config = config


def obter_conexao():  # type: ignore[return]
    """
    Retorna uma conexão aberta com o banco de dados.

    Raises:
        DriverNaoEncontradoError: driver ODBC não instalado.
        ConexaoError: falha ao conectar.
    """
    import pyodbc  # type: ignore[import-untyped]

    driver = _detectar_driver()
    connection_string = _montar_string_conexao(_Estado.config, driver)

    try:
        conexao = pyodbc.connect(connection_string, timeout=5)
        conexao.autocommit = False
        return conexao
    except pyodbc.Error as e:
        raise ConexaoError(
            f"Falha ao conectar em {_Estado.config}.\n"
            f"Verifique se o MySQL está rodando e as credenciais estão corretas.\n"
            f"Detalhe: {e}"
        ) from e


def testar_conexao(config: ConfigConexao | None = None) -> tuple[bool, str]:
    """Testa se a conexão com o banco é possível."""
    cfg = config or _Estado.config

    try:
        import pyodbc  # type: ignore[import-untyped]

        driver = _detectar_driver()
        conn = pyodbc.connect(_montar_string_conexao(cfg, driver), timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        row = cursor.fetchone()
        versao: str = row[0] if row is not None else "desconhecida"
        cursor.close()
        conn.close()
        return True, f"MySQL {versao}  |  Driver: {driver}"
    except DriverNaoEncontradoError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Falha na conexão: {e}"


def salvar_config_no_banco(config: ConfigConexao) -> None:
    """Persiste a configuração na tabela ConexoesBancoDeDados."""
    with obter_conexao() as conn:

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ConexoesBancoDeDados (Servidor, Porta, Usuario, Senha, BancoDeDados)
            VALUES (?, ?, ?, ?, ?)
            """,
            (config.servidor, config.porta, config.usuario, config.senha, config.banco),
        )
        conn.commit()
        cursor.close()


def carregar_config_do_banco() -> ConfigConexao | None:
    """
    Lê a configuração mais recente salva no banco.
    Retorna None se não conseguir conectar ou se não houver config salva.
    """
    try:
        import pyodbc  # type: ignore[import-untyped]

        with obter_conexao() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT Servidor, Porta, Usuario, Senha, BancoDeDados
                    FROM ConexoesBancoDeDados
                    ORDER BY IDConexoesBancoDeDados DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
            except pyodbc.Error:
                return None
            finally:
                cursor.close()

        if row is None:
            return None

        return ConfigConexao(
            servidor=row[0],
            porta=int(row[1]),
            usuario=row[2],
            senha=row[3],
            banco=row[4],
        )
    except Exception:
        return None
