"""
telas/cadastro_adm.py
---------------------
Tela de cadastro do primeiro administrador do sistema.
Exibida uma única vez, logo após a configuração da conexão,
quando ainda não existe nenhum ADM cadastrado.
"""

from __future__ import annotations

import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError
from repositories.usuario_repo import cadastrar, existe_adm
from telas.componentes import (
    BarraStatus,
    Botao,
    CampoSenha,
    CampoTexto,
    CartaoFrame,
    JanelaPadrao,
    Rotulo,
    Separador,
    Subtitulo,
    Titulo,
)
from utils.seguranca import hash_senha, login_valido, senha_valida


class CadastroAdm(JanelaPadrao):
    """
    Tela de cadastro do administrador inicial.

    Uso:
        app = CadastroAdm()
        app.mainloop()
    """

    def __init__(self) -> None:
        super().__init__("FerroFlux — Cadastro do Administrador", 480, 620)
        self._barra: BarraStatus
        self._campo_nome: CampoTexto
        self._campo_login: CampoTexto
        self._campo_senha: CampoSenha
        self._campo_confirmar: CampoSenha
        self._construir()

    # ------------------------------------------------------------------
    # Interface
    # ------------------------------------------------------------------

    def _construir(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = CartaoFrame(self)
        card.grid(row=0, column=0, padx=24, pady=24, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        Titulo(card, "Cadastro do Administrador").grid(
            row=0, column=0, sticky="w", padx=24, pady=(28, 4)
        )
        Subtitulo(card, "Crie a conta de acesso principal do sistema.").grid(
            row=1, column=0, sticky="w", padx=24, pady=(0, 4)
        )
        Separador(card).grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 20))

        # Nome completo
        Rotulo(card, "Nome completo: *").grid(
            row=3, column=0, sticky="w", padx=24, pady=(0, 3)
        )
        self._campo_nome = CampoTexto(card, placeholder="Ex: João da Silva")
        self._campo_nome.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 14))

        # Login
        Rotulo(card, "Login: *").grid(row=5, column=0, sticky="w", padx=24, pady=(0, 3))
        self._campo_login = CampoTexto(card, placeholder="Somente letras, números e _")
        self._campo_login.grid(row=6, column=0, sticky="ew", padx=24, pady=(0, 14))

        # Senha
        Rotulo(card, "Senha: *").grid(row=7, column=0, sticky="w", padx=24, pady=(0, 3))
        self._campo_senha = CampoSenha(card, placeholder="Mínimo 6 caracteres")
        self._campo_senha.grid(row=8, column=0, sticky="ew", padx=24, pady=(0, 14))

        # Confirmar senha
        Rotulo(card, "Confirmar senha: *").grid(
            row=9, column=0, sticky="w", padx=24, pady=(0, 3)
        )
        self._campo_confirmar = CampoSenha(card, placeholder="Repita a senha")
        self._campo_confirmar.grid(row=10, column=0, sticky="ew", padx=24, pady=(0, 24))

        # Botão cadastrar
        Botao(
            card,
            "Cadastrar Administrador",
            variante="sucesso",
            ao_clicar=self._cadastrar,
        ).grid(row=11, column=0, sticky="ew", padx=24, pady=(0, 8))

        # Rodapé com hint
        Rotulo(card, "* Campos obrigatórios", secundario=True).grid(
            row=12, column=0, sticky="w", padx=24, pady=(0, 12)
        )

        # Barra de status
        self._barra = BarraStatus(card)
        self._barra.grid(row=13, column=0, sticky="ew", padx=24, pady=(0, 24))
        self._barra.info("Preencha os dados para criar o administrador.")

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    def _validar(self) -> tuple[str, str, str] | None:
        """
        Lê e valida todos os campos.
        Retorna (nome, login, senha) se válido, ou None se inválido.
        """
        nome = self._campo_nome.get().strip()
        login = self._campo_login.get().strip()
        senha = self._campo_senha.get()
        confirmar = self._campo_confirmar.get()

        if not nome:
            self._barra.erro("Nome completo é obrigatório.")
            return None

        ok, msg = login_valido(login)
        if not ok:
            self._barra.erro(msg)
            return None

        ok, msg = senha_valida(senha)
        if not ok:
            self._barra.erro(msg)
            return None

        if senha != confirmar:
            self._barra.erro("As senhas não coincidem.")
            return None

        return nome, login, senha

    # ------------------------------------------------------------------
    # Ação
    # ------------------------------------------------------------------

    def _cadastrar(self) -> None:
        dados = self._validar()
        if dados is None:
            return

        nome, login, senha = dados

        # Segurança extra: não permite cadastrar se já existe um ADM
        if existe_adm():
            self._barra.erro("Já existe um administrador cadastrado.")
            return

        try:
            cadastrar(
                login=login,
                senha_hash=hash_senha(senha),
                nome_completo=nome,
                perfil="ADM",
            )
        except ConexaoError as e:
            self._barra.erro(f"Falha de conexão: {e}")
            return
        except pyodbc.Error as e:  # pylint: disable=c-extension-no-member
            msg = str(e).lower()
            if "duplicate" in msg or "unique" in msg:
                self._barra.erro("Este login já está em uso. Escolha outro.")
            else:
                self._barra.erro(f"Erro no banco de dados: {e}")
            return

        self._barra.sucesso(f"Administrador '{login}' cadastrado! Abrindo login...")
        self.update()
        self.after(900, self._avancar)

    def _avancar(self) -> None:
        self.destroy()
        try:
            from telas.login import TelaLogin  # pylint: disable=import-outside-toplevel

            TelaLogin().mainloop()
        except (ImportError, AttributeError):
            pass


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    CadastroAdm().mainloop()
