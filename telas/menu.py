"""
telas/menu.py
-------------
Menu principal do FerroFlux — navegação single-window.

Cada módulo é um CTkFrame embutido na área central.
O menu lateral troca o frame ativo sem abrir novas janelas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from repositories.usuario_repo import Usuario
from telas.componentes import Tema

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Definição dos módulos
# ---------------------------------------------------------------------------

_MODULOS: list[dict] = [
    {
        "chave": "funcionarios",
        "label": "Funcionários",
        "icone": "👤",
        "perfis": ["ADM"],
        "modulo": "telas.funcionarios",
        "classe": "TelaFuncionarios",
    },
    {
        "chave": "clientes",
        "label": "Clientes",
        "icone": "👥",
        "perfis": ["ADM", "FUNCIONARIO"],
        "modulo": "telas.clientes",
        "classe": "TelaClientes",
    },
    {
        "chave": "fornecedores",
        "label": "Fornecedores",
        "icone": "🏭",
        "perfis": ["ADM", "FUNCIONARIO"],
        "modulo": "telas.clientes",
        "classe": "TelaFornecedores",
    },
    {
        "chave": "materiais",
        "label": "Materiais",
        "icone": "🔩",
        "perfis": ["ADM", "FUNCIONARIO"],
        "modulo": "telas.materiais",
        "classe": "TelaMateriais",
    },
    {
        "chave": "vendas",
        "label": "Vendas",
        "icone": "💰",
        "perfis": ["ADM", "FUNCIONARIO"],
        "modulo": "telas.vendas",
        "classe": "TelaVendas",
    },
    {
        "chave": "relatorio",
        "label": "Relatórios",
        "icone": "📊",
        "perfis": ["ADM"],
        "modulo": "telas.relatorio",
        "classe": "TelaRelatorio",
    },
    {
        "chave": "historico",
        "label": "Histórico",
        "icone": "📋",
        "perfis": ["ADM"],
        "modulo": "telas.historico",
        "classe": "TelaHistorico",
    },
]


# ---------------------------------------------------------------------------
# Tela de boas-vindas (frame padrão ao abrir o menu)
# ---------------------------------------------------------------------------


class _TelaBoasVindas(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkFrame, usuario: Usuario) -> None:
        super().__init__(master, fg_color=Tema.FUNDO_JANELA, corner_radius=0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.grid(row=0, column=0)

        ctk.CTkLabel(
            centro,
            text="⚙️",
            font=("Segoe UI Emoji", 64),
            fg_color="transparent",
            text_color=Tema.PRIMARIO,
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            centro,
            text=f"Bem-vindo, {usuario.nome_completo.split()[0]}!",
            font=Tema.fonte_titulo(Tema.TAMANHO_H1),
            fg_color="transparent",
            text_color=Tema.TEXTO_TITULO,
        ).pack()

        ctk.CTkLabel(
            centro,
            text="Selecione um módulo no menu lateral para começar.",
            font=Tema.fonte(Tema.TAMANHO_H3),
            fg_color="transparent",
            text_color=Tema.TEXTO_SECUNDARIO,
        ).pack(pady=(8, 0))


# ---------------------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------------------


class TelaMenu(ctk.CTkFrame):
    """
    Frame raiz do sistema após o login.
    Deve ser empacotado na janela CTk pelo chamador.

    Uso:
        menu = TelaMenu(janela_raiz, usuario=usuario_logado)
        menu.pack(fill="both", expand=True)
    """

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        usuario: Usuario,
    ) -> None:
        super().__init__(master, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._usuario = usuario
        self._chave_ativa: str | None = None
        self._frame_atual: ctk.CTkFrame | None = None
        self._botoes_nav: dict[str, ctk.CTkButton] = {}

        self._modulos_visiveis = [
            m for m in _MODULOS if usuario.perfil.upper() in m["perfis"]
        ]

        self._construir_layout()
        self._mostrar_boas_vindas()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _construir_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── Sidebar ────────────────────────────────────────────────────
        self._sidebar = ctk.CTkFrame(
            self,
            fg_color=Tema.FUNDO_CARD,
            corner_radius=0,
            border_width=0,
            width=220,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._sidebar.grid_rowconfigure(99, weight=1)  # empurra o rodapé pra baixo

        # Logo / nome do sistema
        logo_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 0))

        ctk.CTkLabel(
            logo_frame,
            text="⚙️  FerroFlux",
            font=Tema.fonte_titulo(Tema.TAMANHO_H2),
            fg_color="transparent",
            text_color=Tema.PRIMARIO,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame,
            text="Sistema de Gestão",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            fg_color="transparent",
            text_color=Tema.TEXTO_SECUNDARIO,
            anchor="w",
        ).pack(anchor="w")

        # Divisor
        ctk.CTkFrame(
            self._sidebar, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(16, 8))

        # Botões de navegação
        for linha, modulo in enumerate(self._modulos_visiveis, start=2):
            btn = ctk.CTkButton(
                self._sidebar,
                text=f"  {modulo['icone']}  {modulo['label']}",
                font=Tema.fonte(Tema.TAMANHO_LABEL),
                fg_color="transparent",
                text_color=Tema.TEXTO_PRINCIPAL,
                hover_color=Tema.FUNDO_INPUT,
                anchor="w",
                height=44,
                corner_radius=10,
                command=lambda m=modulo: self._navegar(m),
            )
            btn.grid(row=linha, column=0, sticky="ew", padx=10, pady=2)
            self._botoes_nav[modulo["chave"]] = btn

        # Divisor antes do rodapé
        ctk.CTkFrame(
            self._sidebar, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0
        ).grid(row=99, column=0, sticky="ew", padx=16, pady=(8, 8))

        # Info do usuário + botão sair
        rodape = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        rodape.grid(row=100, column=0, sticky="ew", padx=16, pady=(0, 16))

        ctk.CTkLabel(
            rodape,
            text=self._usuario.nome_completo,
            font=Tema.fonte(Tema.TAMANHO_LABEL, "bold"),
            fg_color="transparent",
            text_color=Tema.TEXTO_PRINCIPAL,
            anchor="w",
            wraplength=180,
            justify="left",
        ).pack(anchor="w")

        ctk.CTkLabel(
            rodape,
            text=self._usuario.perfil.capitalize(),
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            fg_color="transparent",
            text_color=Tema.TEXTO_SECUNDARIO,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkButton(
            rodape,
            text="Sair",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            fg_color="transparent",
            text_color=Tema.PERIGO,
            hover_color=Tema.FUNDO_INPUT,
            anchor="w",
            height=32,
            corner_radius=8,
            command=self._sair,
        ).pack(anchor="w", pady=(8, 0))

        # ── Área de conteúdo ───────────────────────────────────────────
        self._area = ctk.CTkFrame(self, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._area.grid(row=0, column=1, sticky="nsew")
        self._area.grid_rowconfigure(0, weight=1)
        self._area.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _navegar(self, modulo: dict) -> None:
        chave = modulo["chave"]

        # Verifica permissão
        if self._usuario.perfil.upper() not in modulo["perfis"]:
            return

        # Evita recarregar se já está na mesma tela
        if chave == self._chave_ativa:
            return

        # Destaca botão ativo
        for k, btn in self._botoes_nav.items():
            if k == chave:
                btn.configure(
                    fg_color=Tema.PRIMARIO,
                    text_color="#ffffff",
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=Tema.TEXTO_PRINCIPAL,
                )

        # Importa e instancia o frame do módulo
        try:
            import importlib

            mod = importlib.import_module(modulo["modulo"])
            Classe = getattr(mod, modulo["classe"])
        except (ImportError, AttributeError) as e:
            self._mostrar_erro(f"Módulo '{modulo['label']}' não disponível.\n{e}")
            return

        self._trocar_frame(Classe(self._area, usuario=self._usuario))
        self._chave_ativa = chave

    def _trocar_frame(self, novo_frame: ctk.CTkFrame) -> None:
        """Remove o frame atual e exibe o novo."""
        if self._frame_atual is not None:
            self._frame_atual.destroy()
        self._frame_atual = novo_frame
        novo_frame.grid(row=0, column=0, sticky="nsew")

    def _mostrar_boas_vindas(self) -> None:
        self._trocar_frame(_TelaBoasVindas(self._area, self._usuario))
        self._chave_ativa = None
        for btn in self._botoes_nav.values():
            btn.configure(fg_color="transparent", text_color=Tema.TEXTO_PRINCIPAL)

    def _mostrar_erro(self, mensagem: str) -> None:
        frame_erro = ctk.CTkFrame(
            self._area, fg_color=Tema.FUNDO_JANELA, corner_radius=0
        )
        frame_erro.grid_rowconfigure(0, weight=1)
        frame_erro.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame_erro,
            text=f"⚠️  {mensagem}",
            font=Tema.fonte(Tema.TAMANHO_H3),
            fg_color="transparent",
            text_color=Tema.PERIGO,
            wraplength=500,
            justify="center",
        ).grid(row=0, column=0)
        self._trocar_frame(frame_erro)

    def _sair(self) -> None:
        """Fecha a aplicação ou volta para o login."""
        self.winfo_toplevel().destroy()
