"""
telas/login.py
--------------
Tela de login do sistema FerroFlux.
Ponto de entrada após a configuração inicial.
"""

from __future__ import annotations

import customtkinter as ctk

from repositories.usuario_repo import Usuario, buscar_por_login_e_senha
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
    Tema,
    Titulo,
)
from utils.seguranca import hash_senha


class TelaLogin(JanelaPadrao):
    """
    Tela de login.

    Uso:
        app = TelaLogin()
        app.mainloop()
    """

    def __init__(self) -> None:
        super().__init__("FerroFlux — Login", 440, 500)
        self._barra: BarraStatus
        self._campo_login: CampoTexto
        self._campo_senha: CampoSenha
        self._construir()

    # ------------------------------------------------------------------
    # Interface
    # ------------------------------------------------------------------

    def _construir(self) -> None:
        """Monta os widgets da tela de login."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = CartaoFrame(self)
        card.grid(row=0, column=0, padx=24, pady=24, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        Titulo(card, "FerroFlux", grande=True).grid(row=0, column=0, pady=(32, 4))
        Subtitulo(card, "Sistema de Gestão para Ferro Velhos").grid(
            row=1, column=0, pady=(0, 8)
        )
        Separador(card).grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 24))

        Rotulo(card, "Login:").grid(row=3, column=0, sticky="w", padx=24, pady=(0, 3))
        self._campo_login = CampoTexto(card, placeholder="Digite seu login")
        self._campo_login.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 14))

        Rotulo(card, "Senha:").grid(row=5, column=0, sticky="w", padx=24, pady=(0, 3))
        self._campo_senha = CampoSenha(card, placeholder="Digite sua senha")
        self._campo_senha.grid(row=6, column=0, sticky="ew", padx=24, pady=(0, 24))

        Botao(
            card,
            "Entrar",
            variante="primario",
            ao_clicar=self._entrar,
        ).grid(row=7, column=0, sticky="ew", padx=24, pady=(0, 8))

        Botao(
            card,
            "Reconfigurar Conexão",
            variante="neutro",
            ao_clicar=self._reconfigurar,
        ).grid(row=8, column=0, sticky="ew", padx=24, pady=(0, 20))

        self._barra = BarraStatus(card)
        self._barra.grid(row=9, column=0, sticky="ew", padx=24, pady=(0, 24))
        self._barra.info("Digite suas credenciais para acessar o sistema.")

        # Enter nos campos também faz login
        self._campo_login.bind("<Return>", lambda _: self._campo_senha.focus())
        self._campo_senha.bind("<Return>", lambda _: self._entrar())

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _entrar(self) -> None:
        """Valida as credenciais e avança para o menu principal."""
        login = self._campo_login.get().strip()
        senha = self._campo_senha.get()

        if not login or not senha:
            self._barra.erro("Preencha o login e a senha.")
            return

        self._barra.info("Verificando credenciais...")
        self.update()

        usuario = buscar_por_login_e_senha(login, hash_senha(senha))

        if usuario is None:
            self._barra.erro("Login ou senha incorretos.")
            # Limpa o campo de senha para nova tentativa
            self._campo_senha.delete(0, "end")
            self._campo_senha.focus()
            return

        self._barra.sucesso(f"Bem-vindo, {usuario.nome_completo}!")
        self.update()
        self.after(700, lambda: self._avancar(usuario))

    def _reconfigurar(self) -> None:
        """Destrói esta janela e abre a tela de configuração de conexão."""
        self.destroy()
        from telas.conexao import TelaConexao  # pylint: disable=import-outside-toplevel

        TelaConexao().mainloop()

    def _avancar(self, usuario: Usuario) -> None:
        """Destrói esta janela, cria a janela raiz e exibe o menu principal."""
        self.destroy()
        try:
            from telas.menu import TelaMenu  # pylint: disable=import-outside-toplevel

            janela = ctk.CTk()
            janela.title("FerroFlux")
            janela.geometry("1100x700")
            janela.minsize(900, 600)
            janela.configure(fg_color=Tema.FUNDO_JANELA)

            menu = TelaMenu(janela, usuario=usuario)
            menu.pack(fill="both", expand=True)

            janela.mainloop()
        except (ImportError, AttributeError):
            pass


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TelaLogin().mainloop()
