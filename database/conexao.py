"""
database/conexao.py
-------------------
Módulo central de conexão com o banco de dados MySQL via pyodbc.

Responsabilidades:
    - Detectar o driver ODBC disponível (uma vez só, na inicialização)
    - Prover uma única função para obter conexão
    - Lançar exceções claras em vez de retornar None silenciosamente

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

import pyodbc  # type: ignore[import-untyped]


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
# Estado interno encapsulado — evita variáveis globais mutáveis
# ---------------------------------------------------------------------------


class _Estado:
    """
    Mantém o estado mutável do módulo em um único lugar.
    Evita o uso de `global`, que confunde o Pylance com variáveis tipadas.
    """

    config: ConfigConexao = ConfigConexao(
        servidor="localhost",
        porta=3306,
        usuario="root",
        senha="",
        banco="ferroflux",
    )
    driver_cache: str | None = None


# Drivers MySQL suportados, em ordem de preferência
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
    """
    Detecta o primeiro driver MySQL ODBC disponível no sistema.
    O resultado fica em _Estado.driver_cache para não repetir a busca.

    Raises:
        DriverNaoEncontradoError: se nenhum driver compatível for encontrado.
    """
    if _Estado.driver_cache is not None:
        return _Estado.driver_cache

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
    """
    Define a configuração de conexão que será usada pelo módulo.
    Deve ser chamada uma vez na inicialização, antes de obter_conexao().

    Exemplo:
        configurar(ConfigConexao(
            servidor="localhost",
            porta=3306,
            usuario="root",
            senha="minhasenha",
            banco="ferroflux",
        ))
    """
    _Estado.config = config


def obter_conexao() -> pyodbc.Connection:
    """
    Retorna uma conexão aberta com o banco de dados.
    Use preferencialmente como gerenciador de contexto:

        with obter_conexao() as conn:
            cursor = conn.cursor()
            ...
        # conexão fechada automaticamente ao sair do bloco

    Raises:
        DriverNaoEncontradoError: driver ODBC não instalado.
        ConexaoError: falha ao conectar (banco offline, credenciais erradas, etc).
    """
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
    """
    Testa se a conexão com o banco é possível.

    Parâmetros:
        config: ConfigConexao a testar. Se None, usa a config ativa.

    Retorna:
        (True, mensagem_de_sucesso) ou (False, mensagem_de_erro)

    Exemplo:
        ok, msg = testar_conexao(config)
        barra.sucesso(msg) if ok else barra.erro(msg)
    """
    cfg = config or _Estado.config

    try:
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
    except pyodbc.Error as e:
        return False, f"Falha na conexão: {e}"


def salvar_config_no_banco(config: ConfigConexao) -> None:
    """
    Persiste a configuração de conexão na tabela ConexoesBancoDeDados.

    Raises:
        ConexaoError: se não for possível conectar.
    """
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
    Lê a configuração mais recente salva na tabela ConexoesBancoDeDados.

    Retorna:
        ConfigConexao preenchido, ou None se a tabela não existir ou estiver vazia.

    Raises:
        ConexaoError: se não for possível conectar nem com a config padrão.
    """
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
            return None  # tabela ainda não existe
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
