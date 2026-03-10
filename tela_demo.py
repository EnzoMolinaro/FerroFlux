"""
tela_demo.py
------------
Demonstração visual de todos os componentes do FerroFlux.

    python tela_demo.py

Requer: pip install customtkinter
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk

from telas.componentes import (
    BarraStatus,
    Botao,
    BotaoIcone,
    CampoSenha,
    CampoTexto,
    CartaoFrame,
    ComboSelecao,
    JanelaPadrao,
    ListaSelecao,
    Rotulo,
    Separador,
    Subtitulo,
    Tema,
    Titulo,
)

MATERIAIS = [
    "Ferro fundido — Fornecedor A  | 12,5 kg | Qtd: 200 | R$ 8,50",
    "Cobre refinado — Fornecedor B |  3,2 kg | Qtd:  50 | R$ 42,00",
    "Alumínio — Fornecedor C       |  6,0 kg | Qtd: 130 | R$ 15,75",
    "Aço inox — Fornecedor A       | 20,0 kg | Qtd:  80 | R$ 31,00",
    "Latão — Fornecedor D          |  1,8 kg | Qtd: 300 | R$ 27,90",
    "Zinco — Fornecedor B          |  5,5 kg | Qtd:  60 | R$ 19,40",
]


class TelaDemo(JanelaPadrao):
    def __init__(self) -> None:
        super().__init__(
            "FerroFlux — Demo de Componentes",
            largura=1100,
            altura=740,
            redimensionavel=True,
        )
        # Declarados aqui para o Pylance reconhecer em toda a classe
        self._barra_lista: BarraStatus
        self._barra_menu: BarraStatus
        self._construir()

    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._coluna_esquerda()
        self._coluna_direita()

    # ------------------------------------------------------------------
    # Coluna esquerda
    # ------------------------------------------------------------------

    def _coluna_esquerda(self) -> None:
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=Tema.FUNDO_JANELA,
            scrollbar_button_color=Tema.SCROLL_BOTAO,
            scrollbar_button_hover_color=Tema.PRIMARIO,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        # ① Identidade
        self._tag(scroll, "① Identidade visual")
        card = CartaoFrame(scroll)
        card.pack(fill="x", pady=(0, 14))

        Titulo(card, "FerroFlux", grande=True).pack(pady=(28, 4))
        Subtitulo(card, "Sistema de Gestão para Ferro Velhos").pack(pady=(0, 10))
        Separador(card).pack(fill="x", padx=24, pady=8)
        Titulo(card, "Título de tela (H2)").pack(pady=(4, 4))
        Rotulo(card, "Rótulo de campo  (bold, corpo)").pack(pady=(0, 4))
        Rotulo(card, "Rótulo secundário — hints e observações", secundario=True).pack(
            pady=(0, 20)
        )

        # ② Formulário
        self._tag(scroll, "② Campos de formulário")
        card2 = CartaoFrame(scroll)
        card2.pack(fill="x", pady=(0, 14))
        card2.grid_columnconfigure((0, 1), weight=1)

        Rotulo(card2, "Nome completo: *").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 3)
        )
        CampoTexto(card2, placeholder="Ex: João da Silva").grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12)
        )
        Rotulo(card2, "CPF:").grid(row=2, column=0, sticky="w", padx=24, pady=(0, 3))
        Rotulo(card2, "Telefone:").grid(
            row=2, column=1, sticky="w", padx=(8, 24), pady=(0, 3)
        )
        CampoTexto(card2, placeholder="000.000.000-00").grid(
            row=3, column=0, sticky="ew", padx=24, pady=(0, 12)
        )
        CampoTexto(card2, placeholder="(11) 99999-9999").grid(
            row=3, column=1, sticky="ew", padx=(8, 24), pady=(0, 12)
        )
        Rotulo(card2, "Perfil:").grid(row=4, column=0, sticky="w", padx=24, pady=(0, 3))
        Rotulo(card2, "Senha:").grid(
            row=4, column=1, sticky="w", padx=(8, 24), pady=(0, 3)
        )
        ComboSelecao(card2, valores=["ADM", "Funcionário"]).grid(
            row=5, column=0, sticky="ew", padx=24, pady=(0, 20)
        )
        CampoSenha(card2).grid(row=5, column=1, sticky="ew", padx=(8, 24), pady=(0, 20))

        # ③ Botões
        self._tag(scroll, "③ Botões — variantes semânticas")
        card3 = CartaoFrame(scroll)
        card3.pack(fill="x", pady=(0, 14))

        for texto, variante in [
            ("Cadastrar / Confirmar", "sucesso"),
            ("Salvar Alterações", "primario"),
            ("Excluir", "perigo"),
            ("Editar", "aviso"),
            ("Cancelar / Voltar", "neutro"),
        ]:
            Botao(card3, texto, variante=variante).pack(fill="x", padx=24, pady=4)
        ctk.CTkLabel(card3, text="", height=12, fg_color="transparent").pack()

        # ④ Barra de status
        self._tag(scroll, "④ Barra de status — interativa")
        card4 = CartaoFrame(scroll)
        card4.pack(fill="x", pady=(0, 14))

        barra = BarraStatus(card4)
        barra.pack(fill="x", padx=24, pady=(20, 8))
        barra.info("Aguardando ação do usuário...")

        fr = ctk.CTkFrame(card4, fg_color="transparent")
        fr.pack(fill="x", padx=24, pady=(0, 20))
        Botao(
            fr,
            "Info",
            variante="neutro",
            ao_clicar=lambda: barra.info("Processando dados..."),
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        Botao(
            fr,
            "Sucesso",
            variante="sucesso",
            ao_clicar=lambda: barra.sucesso("Registro salvo com sucesso!"),
        ).pack(side="left", expand=True, fill="x", padx=4)
        Botao(
            fr,
            "Erro",
            variante="perigo",
            ao_clicar=lambda: barra.erro("Login ou senha inválidos."),
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    # ------------------------------------------------------------------
    # Coluna direita
    # ------------------------------------------------------------------

    def _coluna_direita(self) -> None:
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=Tema.FUNDO_JANELA,
            scrollbar_button_color=Tema.SCROLL_BOTAO,
            scrollbar_button_hover_color=Tema.PRIMARIO,
        )
        scroll.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        # ⑤ Lista
        self._tag(scroll, "⑤ Lista de seleção — interativa")
        card5 = CartaoFrame(scroll)
        card5.pack(fill="x", pady=(0, 14))

        Rotulo(card5, "Materiais cadastrados:").pack(anchor="w", padx=24, pady=(20, 6))

        lista = ListaSelecao(card5, altura=6)
        lista.pack(fill="x", padx=24)
        for item in MATERIAIS:
            lista.inserir(item)

        self._barra_lista = BarraStatus(card5)
        self._barra_lista.pack(fill="x", padx=24, pady=(8, 8))
        self._barra_lista.info("Clique em um item para selecionar.")

        lista.ao_selecionar(
            lambda idx: self._barra_lista.sucesso(f"Item {idx + 1} selecionado.")
        )

        fr5 = ctk.CTkFrame(card5, fg_color="transparent")
        fr5.pack(fill="x", padx=24, pady=(0, 20))
        Botao(fr5, "Editar", variante="aviso").pack(
            side="left", expand=True, fill="x", padx=(0, 4)
        )
        Botao(fr5, "Excluir", variante="perigo").pack(
            side="left", expand=True, fill="x", padx=(4, 0)
        )

        # ⑥ Menu
        self._tag(scroll, "⑥ Botões de menu — com hover")
        card6 = CartaoFrame(scroll)
        card6.pack(fill="x", pady=(0, 14))

        grade = ctk.CTkFrame(card6, fg_color="transparent")
        grade.pack(pady=20, padx=20)

        itens: list[tuple[str, str, int, int, str]] = [
            ("👤", "Funcionários", 0, 0, "padrao"),
            ("👥", "Clientes", 0, 1, "padrao"),
            ("🏭", "Fornecedores", 0, 2, "padrao"),
            ("📦", "Materiais", 1, 0, "padrao"),
            ("💰", "Vendas", 1, 1, "padrao"),
            ("←", "Sair", 1, 2, "sair"),
        ]
        for icone, texto, linha, col, var in itens:
            BotaoIcone(
                grade,
                icone,
                texto,
                variante=var,
                ao_clicar=lambda t=texto: self._barra_menu.sucesso(f'"{t}" clicado.'),
            ).grid(row=linha, column=col, padx=6, pady=6)

        self._barra_menu = BarraStatus(card6)
        self._barra_menu.pack(fill="x", padx=24, pady=(8, 20))
        self._barra_menu.info("Passe o mouse ou clique nos botões.")

        # ⑦ Paleta
        self._tag(scroll, "⑦ Paleta de cores")
        card7 = CartaoFrame(scroll)
        card7.pack(fill="x", pady=(0, 14))

        grade7 = ctk.CTkFrame(card7, fg_color="transparent")
        grade7.pack(padx=24, pady=20, fill="x")
        grade7.grid_columnconfigure((0, 1), weight=1)

        cores: list[tuple[str, str]] = [
            ("Fundo janela", Tema.FUNDO_JANELA),
            ("Fundo card", Tema.FUNDO_CARD),
            ("Primário", Tema.PRIMARIO),
            ("Sucesso", Tema.SUCESSO),
            ("Perigo", Tema.PERIGO),
            ("Aviso", Tema.AVISO),
            ("Neutro", Tema.NEUTRO),
            ("Texto principal", Tema.TEXTO_PRINCIPAL),
            ("Texto secundário", Tema.TEXTO_SECUNDARIO),
            ("Borda card", Tema.BORDA_CARD),
        ]
        for i, (nome, hex_cor) in enumerate(cores):
            r, c = (i // 2) * 2, i % 2
            pad_x = (0, 6) if c == 0 else (6, 0)
            ctk.CTkFrame(grade7, fg_color=hex_cor, corner_radius=6, height=32).grid(
                row=r, column=c, sticky="ew", padx=pad_x, pady=(4, 0)
            )
            ctk.CTkLabel(
                grade7,
                text=f"{nome}   {hex_cor}",
                font=Tema.fonte_mono(Tema.TAMANHO_PEQUENO),
                text_color=Tema.TEXTO_SECUNDARIO,
                fg_color="transparent",
                anchor="w",
            ).grid(row=r + 1, column=c, sticky="w", padx=4, pady=(2, 4))

    # ------------------------------------------------------------------

    def _tag(self, master: ctk.CTkScrollableFrame, texto: str) -> None:
        ctk.CTkLabel(
            master,
            text=texto,
            font=Tema.fonte_mono(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        ).pack(anchor="w", pady=(14, 4))


if __name__ == "__main__":
    TelaDemo().mainloop()
