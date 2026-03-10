"""
telas/tela_conexao.py
---------------------
Tela de configuração inicial da conexão com o banco de dados.
Exibida apenas quando nenhuma configuração válida é encontrada.

Fluxo:
    1. Usuário preenche os dados de conexão
    2. "Testar Conexão" verifica sem salvar
    3. "Conectar e Salvar" conecta, persiste na tabela e avança para CadastroADM
"""

from __future__ import annotations

import customtkinter as ctk

from database.conexao import (
    ConexaoError,
    ConfigConexao,
    configurar,
    salvar_config_no_banco,
    testar_conexao,
)
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


class TelaConexao(JanelaPadrao):
    """
    Tela de configuração inicial da conexão com o banco de dados.

    Uso:
        app = TelaConexao()
        app.mainloop()
    """

    def __init__(self) -> None:
        super().__init__("FerroFlux — Conexão com Banco de Dados", 500, 640)
        self._barra: BarraStatus
        self._campo_servidor: CampoTexto
        self._campo_porta: CampoTexto
        self._campo_usuario: CampoTexto
        self._campo_senha: CampoSenha
        self._campo_banco: CampoTexto
        self._construir()

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------

    def _construir(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = CartaoFrame(self)
        card.grid(row=0, column=0, padx=24, pady=24, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        Titulo(card, "Configurar Conexão").grid(
            row=0, column=0, pady=(28, 4), padx=24, sticky="w"
        )
        Subtitulo(card, "Informe os dados de acesso ao banco MySQL.").grid(
            row=1, column=0, pady=(0, 4), padx=24, sticky="w"
        )
        Separador(card).grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 20))

        # Servidor e porta na mesma linha
        frame_sv = ctk.CTkFrame(card, fg_color="transparent")
        frame_sv.grid(row=3, column=0, sticky="ew", padx=24)
        frame_sv.grid_columnconfigure(0, weight=3)
        frame_sv.grid_columnconfigure(1, weight=1)

        Rotulo(frame_sv, "Servidor:").grid(row=0, column=0, sticky="w", pady=(0, 3))
        Rotulo(frame_sv, "Porta:").grid(
            row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 3)
        )
        self._campo_servidor = CampoTexto(frame_sv, placeholder="localhost")
        self._campo_servidor.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self._campo_porta = CampoTexto(frame_sv, placeholder="3306")
        self._campo_porta.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 14))

        # Usuário
        Rotulo(card, "Usuário:").grid(row=4, column=0, sticky="w", padx=24, pady=(0, 3))
        self._campo_usuario = CampoTexto(card, placeholder="root")
        self._campo_usuario.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 14))

        # Senha
        Rotulo(card, "Senha:").grid(row=6, column=0, sticky="w", padx=24, pady=(0, 3))
        self._campo_senha = CampoSenha(
            card, placeholder="Deixe em branco se não houver"
        )
        self._campo_senha.grid(row=7, column=0, sticky="ew", padx=24, pady=(0, 14))

        # Banco de dados
        Rotulo(card, "Banco de dados:").grid(
            row=8, column=0, sticky="w", padx=24, pady=(0, 3)
        )
        self._campo_banco = CampoTexto(card, placeholder="ferroflux")
        self._campo_banco.grid(row=9, column=0, sticky="ew", padx=24, pady=(0, 24))

        # Botões
        Botao(
            card,
            "Conectar e Salvar",
            variante="sucesso",
            ao_clicar=self._conectar_e_salvar,
        ).grid(row=10, column=0, sticky="ew", padx=24, pady=(0, 8))

        Botao(
            card,
            "Testar Conexão",
            variante="primario",
            ao_clicar=self._testar,
        ).grid(row=11, column=0, sticky="ew", padx=24, pady=(0, 8))

        Botao(
            card,
            "Cancelar",
            variante="neutro",
            ao_clicar=self._cancelar,
        ).grid(row=12, column=0, sticky="ew", padx=24, pady=(0, 20))

        # Barra de status
        self._barra = BarraStatus(card)
        self._barra.grid(row=13, column=0, sticky="ew", padx=24, pady=(0, 24))
        self._barra.info("Preencha os dados e clique em Testar ou Conectar.")

    # ------------------------------------------------------------------
    # Leitura e validação dos campos
    # ------------------------------------------------------------------

    def _ler_campos(self) -> ConfigConexao | None:
        """Lê os campos, valida e retorna um ConfigConexao. Retorna None se inválido."""
        servidor = self._campo_servidor.get().strip() or "localhost"
        porta_str = self._campo_porta.get().strip() or "3306"
        usuario = self._campo_usuario.get().strip() or "root"
        senha = self._campo_senha.get()
        banco = self._campo_banco.get().strip() or "ferroflux"

        try:
            porta = int(porta_str)
            if not (1 <= porta <= 65535):
                raise ValueError
        except ValueError:
            self._barra.erro("Porta inválida — deve ser um número entre 1 e 65535.")
            return None

        return ConfigConexao(
            servidor=servidor,
            porta=porta,
            usuario=usuario,
            senha=senha,
            banco=banco,
        )

    # ------------------------------------------------------------------
    # Ações dos botões
    # ------------------------------------------------------------------

    def _testar(self) -> None:
        config = self._ler_campos()
        if config is None:
            return

        self._barra.info("Testando conexão...")
        self.update()

        try:
            ok, msg = testar_conexao(config)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._barra.erro(f"Erro inesperado: {e}")
            return

        if ok:
            self._barra.sucesso(msg)
        else:
            self._barra.erro(msg)

    def _conectar_e_salvar(self) -> None:
        config = self._ler_campos()
        if config is None:
            return

        self._barra.info("Conectando...")
        self.update()

        # 1. Testar antes de salvar
        try:
            ok, msg = testar_conexao(config)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._barra.erro(f"Erro inesperado: {e}")
            return

        if not ok:
            self._barra.erro(msg)
            return

        # 2. Aplicar como config ativa do sistema
        configurar(config)

        # 3. Persistir na tabela ConexoesBancoDeDados
        try:
            salvar_config_no_banco(config)
        except ConexaoError as e:
            self._barra.erro(f"Conexão ok, mas falha ao salvar: {e}")
            return

        self._barra.sucesso("Conexão salva! Abrindo cadastro do administrador...")
        self.update()
        self.after(800, self._avancar)

    def _cancelar(self) -> None:
        self.destroy()

    def _avancar(self) -> None:
        """Fecha esta tela e abre o cadastro do administrador."""
        self.destroy()
        try:
            from telas.cadastro_adm import (
                CadastroAdm,
            )  # pylint: disable=import-outside-toplevel

            CadastroAdm().mainloop()
        except (ImportError, AttributeError):
            # Tela ainda não implementada — silencioso em desenvolvimento
            pass


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TelaConexao().mainloop()
