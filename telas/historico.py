"""
telas/historico.py
------------------
Tela de histórico de ações (LogAcoes) do FerroFlux.
Embarcada no menu como CTkFrame (single-window navigation).
"""

from __future__ import annotations

import json
import tkinter as tk
import tkinter.ttk as ttk
from datetime import datetime
from typing import Any

import customtkinter as ctk
import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError, obter_conexao
from repositories.usuario_repo import Usuario
from telas.componentes import BarraStatus, Botao, CampoTexto, ComboSelecao, Tema, Titulo

# ---------------------------------------------------------------------------
# Estilo da tabela
# ---------------------------------------------------------------------------


def _aplicar_estilo() -> None:
    """Aplica o estilo visual customizado à Treeview do histórico."""
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Hist.Treeview",
        background=Tema.FUNDO_INPUT,
        foreground=Tema.TEXTO_PRINCIPAL,
        fieldbackground=Tema.FUNDO_INPUT,
        rowheight=34,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_CORPO),
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Hist.Treeview.Heading",
        background=Tema.FUNDO_JANELA,
        foreground=Tema.TEXTO_SECUNDARIO,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_LABEL, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Hist.Treeview",
        background=[("selected", Tema.PRIMARIO)],
        foreground=[("selected", "#ffffff")],
    )
    style.map("Hist.Treeview.Heading", background=[("active", Tema.NEUTRO)])
    style.layout("Hist.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


_COLUNAS = [
    ("id", "#", 50, "center"),
    ("data", "Data/Hora", 150, "center"),
    ("usuario", "Usuário", 130, "w"),
    ("acao", "Ação", 100, "center"),
    ("tabela", "Tabela", 120, "w"),
    ("registro", "Registro", 80, "center"),
]


# ---------------------------------------------------------------------------
# Tela principal — CTkFrame (embedded)
# ---------------------------------------------------------------------------


class TelaHistorico(ctk.CTkFrame):
    """Tela de histórico de ações do sistema. Embarcada no menu."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        usuario: Usuario | None = None,
    ) -> None:
        super().__init__(master, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._usuario = usuario
        self._registros: list[dict[str, Any]] = []
        self._filtrados: list[dict[str, Any]] = []

        # Widgets declarados antes de construir
        self._combo_tabela: ComboSelecao
        self._campo_usuario: CampoTexto
        self._tree: ttk.Treeview
        self._barra: BarraStatus
        self._txt_antes: ctk.CTkTextbox
        self._txt_depois: ctk.CTkTextbox
        self._ord_flags: dict[str, bool] = {}

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._construir_ui()
        self._carregar()

    def _construir_ui(self) -> None:
        """Monta a interface da tela de histórico."""
        # ── Cabeçalho ──────────────────────────────────────────────────
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        topo.columnconfigure(2, weight=1)

        Titulo(topo, "📋  Histórico de Ações").grid(row=0, column=0, sticky="w")

        filtros = ctk.CTkFrame(topo, fg_color="transparent")
        filtros.grid(row=0, column=1, padx=24)

        ctk.CTkLabel(
            filtros,
            text="Tabela:",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
        ).pack(side="left", padx=(0, 6))

        self._combo_tabela = ComboSelecao(
            filtros,
            valores=[
                "TODAS",
                "Entidade",
                "Usuario",
                "Material",
                "Pedido",
                "ItemPedido",
                "NotaFiscal",
            ],
            width=160,
        )
        self._combo_tabela.set("TODAS")
        self._combo_tabela.pack(side="left", padx=(0, 16))
        self._combo_tabela.bind("<<ComboboxSelected>>", lambda _: self._filtrar())

        ctk.CTkLabel(
            filtros,
            text="Usuário:",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
        ).pack(side="left", padx=(0, 6))

        self._campo_usuario = CampoTexto(filtros, placeholder="Login...", width=140)
        self._campo_usuario.pack(side="left")
        self._campo_usuario.bind("<KeyRelease>", lambda _: self._filtrar())

        Botao(
            topo,
            "🔄  Atualizar",
            variante="primario",
            ao_clicar=self._carregar,
            height=36,
        ).grid(row=0, column=3, sticky="e")

        # ── Divisor ────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=24, pady=(12, 0)
        )

        # ── Corpo ──────────────────────────────────────────────────────
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="nsew", padx=24, pady=12)
        corpo.grid_rowconfigure(0, weight=3)
        corpo.grid_rowconfigure(1, weight=1)
        corpo.grid_columnconfigure(0, weight=1)

        # Tabela
        frame_tab = ctk.CTkFrame(
            corpo,
            fg_color=Tema.FUNDO_CARD,
            corner_radius=16,
            border_width=1,
            border_color=Tema.BORDA_CARD,
        )
        frame_tab.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        frame_tab.grid_rowconfigure(0, weight=1)
        frame_tab.grid_columnconfigure(0, weight=1)

        _aplicar_estilo()
        colunas = [c[0] for c in _COLUNAS]

        sb_y = tk.Scrollbar(
            frame_tab,
            orient="vertical",
            bg=Tema.SCROLL_FUNDO,
            troughcolor=Tema.FUNDO_INPUT,
            activebackground=Tema.PRIMARIO,
            highlightthickness=0,
            bd=0,
        )
        sb_x = tk.Scrollbar(
            frame_tab,
            orient="horizontal",
            bg=Tema.SCROLL_FUNDO,
            troughcolor=Tema.FUNDO_INPUT,
            activebackground=Tema.PRIMARIO,
            highlightthickness=0,
            bd=0,
        )

        self._tree = ttk.Treeview(
            frame_tab,
            columns=colunas,
            show="headings",
            style="Hist.Treeview",
            selectmode="browse",
            yscrollcommand=sb_y.set,
            xscrollcommand=sb_x.set,
        )

        for col_id, cab, larg, anchor in _COLUNAS:
            self._tree.heading(
                col_id, text=cab, command=lambda c=col_id: self._ordenar(c)
            )
            self._tree.column(col_id, width=larg, minwidth=larg, anchor=anchor)  # type: ignore[arg-type]

        sb_y.config(command=self._tree.yview)
        sb_x.config(command=self._tree.xview)

        self._tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        sb_y.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=8)
        sb_x.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 4))

        self._tree.tag_configure("par", background=Tema.FUNDO_INPUT)
        self._tree.tag_configure("impar", background=Tema.FUNDO_CARD)
        self._tree.bind("<<TreeviewSelect>>", self._ao_selecionar)

        # Painel de detalhe (dados antes/depois)
        frame_det = ctk.CTkFrame(
            corpo,
            fg_color=Tema.FUNDO_CARD,
            corner_radius=16,
            border_width=1,
            border_color=Tema.BORDA_CARD,
        )
        frame_det.grid(row=1, column=0, sticky="nsew")
        frame_det.grid_rowconfigure(1, weight=1)
        frame_det.columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            frame_det,
            text="Dados Anteriores",
            font=Tema.fonte(Tema.TAMANHO_LABEL, "bold"),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(10, 2))

        ctk.CTkLabel(
            frame_det,
            text="Dados Novos",
            font=Tema.fonte(Tema.TAMANHO_LABEL, "bold"),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=16, pady=(10, 2))

        self._txt_antes = ctk.CTkTextbox(
            frame_det,
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            fg_color=Tema.FUNDO_INPUT,
            text_color=Tema.TEXTO_PRINCIPAL,
            corner_radius=8,
            state="disabled",
        )
        self._txt_antes.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))

        self._txt_depois = ctk.CTkTextbox(
            frame_det,
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            fg_color=Tema.FUNDO_INPUT,
            text_color=Tema.TEXTO_PRINCIPAL,
            corner_radius=8,
            state="disabled",
        )
        self._txt_depois.grid(
            row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12)
        )

        # Barra de status
        self._barra = BarraStatus(self)
        self._barra.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar(self) -> None:
        """Carrega todos os registros de log do banco de dados."""
        self._registros = []
        try:
            with obter_conexao() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        l.IDLog,
                        l.DataHora,
                        u.Login,
                        l.Acao,
                        l.Tabela,
                        l.IDRegistro,
                        l.DadosAntigos,
                        l.DadosNovos
                    FROM LogAcoes l
                    LEFT JOIN Usuario u ON u.IDUsuario = l.IDUsuario
                    ORDER BY l.DataHora DESC
                    """
                )
                for row in cursor.fetchall():
                    self._registros.append(
                        {
                            "id": row[0],
                            "data": row[1],
                            "usuario": row[2] or "—",
                            "acao": row[3] or "—",
                            "tabela": row[4] or "—",
                            "registro": row[5],
                            "antes": row[6],
                            "depois": row[7],
                        }
                    )
        except ConexaoError as e:
            self._barra.erro(str(e))
            return
        except pyodbc.Error as e:
            self._barra.erro(f"Erro ao carregar histórico: {e}")
            return

        self._filtrar()

    def _filtrar(self) -> None:
        """Filtra os registros carregados por tabela e nome de usuário."""
        tabela_sel = self._combo_tabela.get()
        usuario_termo = self._campo_usuario.get().strip().lower()

        self._filtrados = [
            r
            for r in self._registros
            if (tabela_sel == "TODAS" or r["tabela"] == tabela_sel)
            and (not usuario_termo or usuario_termo in r["usuario"].lower())
        ]

        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(self._filtrados):
            data_str = (
                r["data"].strftime("%d/%m/%Y %H:%M:%S")
                if isinstance(r["data"], datetime)
                else str(r["data"])
            )
            tag = "par" if i % 2 == 0 else "impar"
            self._tree.insert(
                "",
                "end",
                iid=str(i),
                tags=(tag,),
                values=(
                    r["id"],
                    data_str,
                    r["usuario"],
                    r["acao"],
                    r["tabela"],
                    r["registro"] or "—",
                ),
            )

        self._barra.info(f"{len(self._filtrados)} registro(s) encontrado(s).")
        self._limpar_detalhe()

    def _ao_selecionar(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        """Exibe os dados antes/depois do registro selecionado na tabela."""
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(self._filtrados):
            return
        r = self._filtrados[idx]
        self._mostrar_detalhe(r["antes"], r["depois"])

    def _mostrar_detalhe(self, antes: Any, depois: Any) -> None:
        """Preenche os painéis de texto com os dados antes e depois da ação."""

        def formatar(dado: Any) -> str:
            if dado is None:
                return "—"
            if isinstance(dado, str):
                try:
                    return json.dumps(json.loads(dado), indent=2, ensure_ascii=False)
                except (json.JSONDecodeError, ValueError):
                    return dado
            return str(dado)

        for txt, dado in [(self._txt_antes, antes), (self._txt_depois, depois)]:
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", formatar(dado))
            txt.configure(state="disabled")

    def _limpar_detalhe(self) -> None:
        """Limpa os painéis de texto de detalhe."""
        for txt in (self._txt_antes, self._txt_depois):
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.configure(state="disabled")

    def _ordenar(self, coluna: str) -> None:
        """Ordena a tabela pela coluna clicada, alternando asc/desc."""
        crescente = not self._ord_flags.get(coluna, False)
        self._ord_flags[coluna] = crescente
        mapa = {
            "id": "id",
            "data": "data",
            "usuario": "usuario",
            "acao": "acao",
            "tabela": "tabela",
            "registro": "registro",
        }
        attr = mapa.get(coluna, "id")
        self._registros.sort(key=lambda r: str(r.get(attr, "")), reverse=not crescente)
        self._filtrar()
        for c, cab, *_ in _COLUNAS:
            seta = (" ↑" if crescente else " ↓") if c == coluna else ""
            self._tree.heading(c, text=cab + seta)
