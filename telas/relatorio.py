"""
telas/relatorio.py
-------------------
Tela de Relatório Financeiro do FerroFlux.
Embarcada no menu como CTkFrame (single-window navigation).
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from datetime import datetime, timedelta
from typing import Any, Literal

import customtkinter as ctk
import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError, obter_conexao
from repositories.relatorio_repo import (
    FaturamentoMensal,
    LinhaDetalhePedido,
    RelatorioRepo,
    ResumoFinanceiro,
    TopCliente,
    TopProduto,
)
from repositories.usuario_repo import Usuario
from telas.componentes import (
    BarraStatus,
    Botao,
    CampoTexto,
    CartaoFrame,
    Rotulo,
    Separador,
    Tema,
    Titulo,
)

AnchorTabela = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]


def _brl(valor: float) -> str:
    s = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}" if valor >= 0 else f"- R$ {s}"


def _pct(valor: float) -> str:
    return f"{valor:.1f}%"


class _CardKPI(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkFrame,
        icone: str,
        rotulo: str,
        valor: str,
        cor_valor: str = Tema.TEXTO_TITULO,
        destaque: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("corner_radius", 14)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        super().__init__(master, **kwargs)

        ctk.CTkLabel(
            self,
            text=icone,
            font=("Segoe UI Emoji", 26),
            fg_color="transparent",
            text_color=Tema.PRIMARIO,
        ).pack(anchor="w", padx=18, pady=(18, 0))

        ctk.CTkLabel(
            self,
            text=rotulo,
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            fg_color="transparent",
            text_color=Tema.TEXTO_SECUNDARIO,
            anchor="w",
        ).pack(anchor="w", padx=18, pady=(2, 0))

        ctk.CTkLabel(
            self,
            text=valor,
            font=Tema.fonte_titulo(Tema.TAMANHO_H2 if destaque else Tema.TAMANHO_H3),
            fg_color="transparent",
            text_color=cor_valor,
            anchor="w",
            wraplength=200,
        ).pack(anchor="w", padx=18, pady=(2, 18))

    def atualizar_valor(self, novo_valor: str, cor: str | None = None) -> None:
        labels = [w for w in self.winfo_children() if isinstance(w, ctk.CTkLabel)]
        if labels:
            kw: dict[str, Any] = {"text": novo_valor}
            if cor:
                kw["text_color"] = cor
            labels[-1].configure(**kw)


class _GraficoBarras(ctk.CTkFrame):
    _COR_FAT = "#4f7cff"
    _COR_LUCRO = "#10b981"
    _COR_CUSTO = "#f43f5e"
    _COR_GRADE = "#dde3f5"
    _COR_TEXTO = "#6b7a9e"

    def __init__(self, master: ctk.CTkFrame, **kwargs: Any) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("corner_radius", 14)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        super().__init__(master, **kwargs)
        self._dados: list[FaturamentoMensal] = []
        self._canvas = tk.Canvas(
            self,
            bg=Tema.FUNDO_CARD,
            highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self._canvas.bind("<Configure>", lambda _: self._desenhar())

    def popular(self, dados: list[FaturamentoMensal]) -> None:
        self._dados = dados
        self._desenhar()

    def _desenhar(self) -> None:
        c = self._canvas
        c.delete("all")
        if not self._dados:
            c.create_text(
                c.winfo_width() // 2,
                c.winfo_height() // 2,
                text="Sem dados para o período selecionado.",
                fill=self._COR_TEXTO,
                font=(Tema.FAMILIA_FB, Tema.TAMANHO_LABEL),
            )
            return

        largura = c.winfo_width()
        altura = c.winfo_height()
        if largura < 10 or altura < 10:
            return

        margem_esq = 72
        margem_dir = 20
        margem_top = 20
        margem_bot = 48

        area_w = largura - margem_esq - margem_dir
        area_h = altura - margem_top - margem_bot

        max_val = max(
            max(d.faturamento for d in self._dados),
            max(d.lucro for d in self._dados),
            1.0,
        )

        divisoes = 5
        for i in range(divisoes + 1):
            y = margem_top + area_h - (i / divisoes) * area_h
            val = (i / divisoes) * max_val
            c.create_line(
                margem_esq,
                y,
                largura - margem_dir,
                y,
                fill=self._COR_GRADE,
                dash=(3, 4),
            )
            label = _brl(val) if val >= 1000 else f"R$ {val:.0f}"
            c.create_text(
                margem_esq - 6,
                y,
                text=label,
                anchor="e",
                fill=self._COR_TEXTO,
                font=(Tema.FAMILIA_FB, 8),
            )

        n = len(self._dados)
        grupo_w = area_w / n
        barra_w = max(grupo_w * 0.3, 4)
        gap = barra_w * 0.2

        for i, d in enumerate(self._dados):
            cx = margem_esq + (i + 0.5) * grupo_w

            h_fat = (d.faturamento / max_val) * area_h
            x0 = cx - barra_w - gap / 2
            c.create_rectangle(
                x0,
                margem_top + area_h - h_fat,
                x0 + barra_w,
                margem_top + area_h,
                fill=self._COR_FAT,
                outline="",
            )

            h_luc = (max(d.lucro, 0) / max_val) * area_h
            x1 = cx + gap / 2
            c.create_rectangle(
                x1,
                margem_top + area_h - h_luc,
                x1 + barra_w,
                margem_top + area_h,
                fill=self._COR_LUCRO if d.lucro >= 0 else self._COR_CUSTO,
                outline="",
            )

            c.create_text(
                cx,
                margem_top + area_h + 10,
                text=d.label,
                fill=self._COR_TEXTO,
                font=(Tema.FAMILIA_FB, 8),
                anchor="n",
            )

        lx = margem_esq
        ly = altura - 12
        for cor, texto in [(self._COR_FAT, "Faturamento"), (self._COR_LUCRO, "Lucro")]:
            c.create_rectangle(lx, ly - 8, lx + 14, ly, fill=cor, outline="")
            c.create_text(
                lx + 18,
                ly - 4,
                text=texto,
                anchor="w",
                fill=self._COR_TEXTO,
                font=(Tema.FAMILIA_FB, 9),
            )
            lx += 100


def _estilo_tabela_rel() -> None:
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Rel.Treeview",
        background=Tema.FUNDO_INPUT,
        foreground=Tema.TEXTO_PRINCIPAL,
        fieldbackground=Tema.FUNDO_INPUT,
        rowheight=32,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_CORPO),
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Rel.Treeview.Heading",
        background=Tema.FUNDO_JANELA,
        foreground=Tema.TEXTO_SECUNDARIO,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_LABEL, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Rel.Treeview",
        background=[("selected", Tema.PRIMARIO)],
        foreground=[("selected", "#ffffff")],
    )
    style.map("Rel.Treeview.Heading", background=[("active", Tema.NEUTRO)])
    style.layout("Rel.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


def _tabela(
    master: ctk.CTkFrame,
    colunas: list[tuple[str, str, int, AnchorTabela]],
    altura: int = 8,
) -> ttk.Treeview:
    _estilo_tabela_rel()
    ids = [c[0] for c in colunas]
    sb = tk.Scrollbar(
        master,
        orient="vertical",
        bg=Tema.SCROLL_FUNDO,
        troughcolor=Tema.FUNDO_INPUT,
        activebackground=Tema.PRIMARIO,
        highlightthickness=0,
        bd=0,
    )
    tree = ttk.Treeview(
        master,
        columns=ids,
        show="headings",
        style="Rel.Treeview",
        selectmode="browse",
        height=altura,
        yscrollcommand=sb.set,
    )
    for col_id, cab, larg, anchor in colunas:
        tree.heading(col_id, text=cab)
        tree.column(col_id, width=larg, minwidth=larg, anchor=anchor)  # type: ignore[arg-type]
    sb.config(command=tree.yview)
    tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
    sb.pack(side="right", fill="y", pady=8, padx=(0, 4))
    tree.tag_configure("par", background=Tema.FUNDO_INPUT)
    tree.tag_configure("impar", background=Tema.FUNDO_CARD)
    return tree


# ---------------------------------------------------------------------------
# Tela principal — CTkFrame (embedded)
# ---------------------------------------------------------------------------


class TelaRelatorio(ctk.CTkFrame):
    """Tela de relatório financeiro. Embarcada no menu principal."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        usuario: Usuario | None = None,
    ) -> None:
        super().__init__(master, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._usuario = usuario

        hoje = datetime.now()
        self._data_inicio = hoje.replace(day=1, month=1)
        self._data_fim = hoje

        # Widgets declarados antes de construir
        self._f_inicio: CampoTexto
        self._f_fim: CampoTexto
        self._scroll: ctk.CTkScrollableFrame
        self._cards: dict[str, _CardKPI] = {}
        self._grafico: _GraficoBarras
        self._tree_clientes: ttk.Treeview
        self._tree_produtos: ttk.Treeview
        self._tree_detalhe: ttk.Treeview
        self._barra: BarraStatus

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._construir_ui()
        self._carregar()

    def _construir_ui(self) -> None:
        # ── Cabeçalho ──────────────────────────────────────────────────
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        topo.columnconfigure(1, weight=1)

        Titulo(topo, "📊  Relatório Financeiro").grid(row=0, column=0, sticky="w")

        filtros = ctk.CTkFrame(topo, fg_color="transparent")
        filtros.grid(row=0, column=1, sticky="e")

        Rotulo(filtros, "De:").pack(side="left", padx=(0, 4))
        self._f_inicio = CampoTexto(filtros, placeholder="dd/mm/aaaa", width=110)
        self._f_inicio.pack(side="left")
        self._f_inicio.insert(0, self._data_inicio.strftime("%d/%m/%Y"))

        Rotulo(filtros, "Até:").pack(side="left", padx=(12, 4))
        self._f_fim = CampoTexto(filtros, placeholder="dd/mm/aaaa", width=110)
        self._f_fim.pack(side="left")
        self._f_fim.insert(0, self._data_fim.strftime("%d/%m/%Y"))

        Botao(
            filtros,
            "🔄  Atualizar",
            variante="primario",
            ao_clicar=self._ao_atualizar,
            height=38,
        ).pack(side="left", padx=(12, 0))

        atalhos = ctk.CTkFrame(topo, fg_color="transparent")
        atalhos.grid(row=1, column=1, sticky="e", pady=(4, 0))
        for label, dias in [
            ("7 dias", 7),
            ("30 dias", 30),
            ("90 dias", 90),
            ("Este ano", 0),
        ]:
            Botao(
                atalhos,
                label,
                variante="neutro",
                height=28,
                ao_clicar=lambda d=dias: self._atalho_periodo(d),
            ).pack(side="left", padx=(4, 0))

        # Divisor
        ctk.CTkFrame(self, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=24, pady=(12, 0)
        )

        # Corpo scrollável
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew")

        # KPI Cards
        frame_kpi = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame_kpi.pack(fill="x", padx=24, pady=(16, 0))
        for col in range(7):
            frame_kpi.columnconfigure(col, weight=1)

        kpis = [
            ("fat", "💰", "Faturamento Bruto", "R$ 0,00", Tema.PRIMARIO, True),
            ("custo", "📦", "Custo Mercadorias", "R$ 0,00", Tema.PERIGO, False),
            ("lucro", "📈", "Lucro Bruto", "R$ 0,00", Tema.SUCESSO, True),
            ("margem", "🎯", "Margem", "0,0%", Tema.TEXTO_TITULO, False),
            ("pedidos", "🧾", "Pedidos", "0", Tema.TEXTO_TITULO, False),
            ("ticket", "🎫", "Ticket Médio", "R$ 0,00", Tema.TEXTO_TITULO, False),
            ("estoque", "🏭", "Valor em Estoque", "R$ 0,00", Tema.AVISO, False),
        ]
        for col, (chave, icone, rotulo, valor, cor, dest) in enumerate(kpis):
            card = _CardKPI(
                frame_kpi, icone, rotulo, valor, cor_valor=cor, destaque=dest
            )
            card.grid(
                row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0), pady=0
            )
            self._cards[chave] = card

        # Gráfico
        self._grafico = _GraficoBarras(self._scroll, height=220)  # type: ignore[arg-type]
        self._grafico.pack(fill="x", padx=24, pady=(16, 0))

        # Top Clientes + Top Produtos
        frame_tops = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame_tops.pack(fill="x", padx=24, pady=(16, 0))
        frame_tops.columnconfigure((0, 1), weight=1)

        f_cli = CartaoFrame(frame_tops)
        f_cli.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        Rotulo(f_cli, "🏆  Top Clientes").pack(anchor="w", padx=14, pady=(12, 4))
        Separador(f_cli).pack(fill="x", padx=14, pady=(0, 4))
        frame_tree_cli = ctk.CTkFrame(f_cli, fg_color="transparent")
        frame_tree_cli.pack(fill="both", expand=True)
        cols_cli: list[tuple[str, str, int, AnchorTabela]] = [
            ("nome", "Cliente", 200, "w"),
            ("total", "Total", 110, "e"),
            ("pedidos", "Pedidos", 70, "center"),
        ]
        self._tree_clientes = _tabela(frame_tree_cli, cols_cli, altura=6)

        f_prod = CartaoFrame(frame_tops)
        f_prod.grid(row=0, column=1, sticky="nsew")
        Rotulo(f_prod, "🏅  Top Produtos").pack(anchor="w", padx=14, pady=(12, 4))
        Separador(f_prod).pack(fill="x", padx=14, pady=(0, 4))
        frame_tree_prod = ctk.CTkFrame(f_prod, fg_color="transparent")
        frame_tree_prod.pack(fill="both", expand=True)
        cols_prod: list[tuple[str, str, int, AnchorTabela]] = [
            ("nome", "Produto", 190, "w"),
            ("qtd", "Qtd", 70, "e"),
            ("receita", "Receita", 110, "e"),
            ("lucro", "Lucro", 100, "e"),
        ]
        self._tree_produtos = _tabela(frame_tree_prod, cols_prod, altura=6)

        # Detalhe de pedidos
        f_det = CartaoFrame(self._scroll)  # type: ignore[arg-type]
        f_det.pack(fill="x", padx=24, pady=(16, 24))
        Rotulo(f_det, "📋  Detalhe dos Pedidos").pack(anchor="w", padx=14, pady=(12, 4))
        Separador(f_det).pack(fill="x", padx=14, pady=(0, 4))
        frame_tree_det = ctk.CTkFrame(f_det, fg_color="transparent")
        frame_tree_det.pack(fill="both", expand=True)
        cols_det: list[tuple[str, str, int, AnchorTabela]] = [
            ("id", "Nº", 55, "center"),
            ("data", "Data", 120, "center"),
            ("cliente", "Cliente", 220, "w"),
            ("status", "Status", 110, "center"),
            ("fat", "Faturamento", 120, "e"),
            ("custo", "Custo", 110, "e"),
            ("lucro", "Lucro", 110, "e"),
        ]
        self._tree_detalhe = _tabela(frame_tree_det, cols_det, altura=10)

        # Barra de status (fora do scroll, fixo no fundo)
        self._barra = BarraStatus(self)
        self._barra.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))

    def _ao_atualizar(self) -> None:
        try:
            self._data_inicio = datetime.strptime(
                self._f_inicio.get().strip(), "%d/%m/%Y"
            )
            self._data_fim = datetime.strptime(self._f_fim.get().strip(), "%d/%m/%Y")
        except ValueError:
            self._barra.erro("Datas inválidas. Use o formato dd/mm/aaaa.")
            return
        self._carregar()

    def _atalho_periodo(self, dias: int) -> None:
        hoje = datetime.now()
        if dias == 0:
            self._data_inicio = hoje.replace(month=1, day=1)
        else:
            self._data_inicio = hoje - timedelta(days=dias)
        self._data_fim = hoje
        self._f_inicio.delete(0, "end")
        self._f_inicio.insert(0, self._data_inicio.strftime("%d/%m/%Y"))
        self._f_fim.delete(0, "end")
        self._f_fim.insert(0, self._data_fim.strftime("%d/%m/%Y"))
        self._carregar()

    def _carregar(self) -> None:
        self._barra.info("Carregando dados...")
        self.update_idletasks()
        try:
            with obter_conexao() as conn:
                repo = RelatorioRepo(conn)
                resumo = repo.resumo(self._data_inicio, self._data_fim)
                mensal = repo.faturamento_mensal(
                    self._data_inicio, self._data_fim, ultimos_n_meses=None
                )
                clientes = repo.top_clientes(self._data_inicio, self._data_fim)
                produtos = repo.top_produtos(self._data_inicio, self._data_fim)
                detalhe = repo.detalhe_pedidos(self._data_inicio, self._data_fim)
        except ConexaoError as e:
            self._barra.erro(f"Erro de conexão: {e}")
            return
        except pyodbc.Error as e:
            self._barra.erro(f"Erro no banco de dados: {e}")
            return

        self._atualizar_cards(resumo)
        self._grafico.popular(mensal)
        self._popular_clientes(clientes)
        self._popular_produtos(produtos)
        self._popular_detalhe(detalhe)

        per_ini = self._data_inicio.strftime("%d/%m/%Y")
        per_fim = self._data_fim.strftime("%d/%m/%Y")
        self._barra.sucesso(
            f"Dados atualizados — período: {per_ini} a {per_fim}  |  "
            f"{resumo.total_pedidos} pedido(s)  |  Faturamento: {_brl(resumo.faturamento_bruto)}"
        )

    def _atualizar_cards(self, r: ResumoFinanceiro) -> None:
        cor_lucro = Tema.SUCESSO if r.lucro_bruto >= 0 else Tema.PERIGO
        cor_margem = Tema.SUCESSO if r.margem_percentual >= 0 else Tema.PERIGO
        self._cards["fat"].atualizar_valor(_brl(r.faturamento_bruto))
        self._cards["custo"].atualizar_valor(_brl(r.custo_mercadorias))
        self._cards["lucro"].atualizar_valor(_brl(r.lucro_bruto), cor=cor_lucro)
        self._cards["margem"].atualizar_valor(_pct(r.margem_percentual), cor=cor_margem)
        self._cards["pedidos"].atualizar_valor(str(r.total_pedidos))
        self._cards["ticket"].atualizar_valor(_brl(r.ticket_medio))
        self._cards["estoque"].atualizar_valor(_brl(r.valor_estoque))

    def _popular_clientes(self, dados: list[TopCliente]) -> None:
        self._tree_clientes.delete(*self._tree_clientes.get_children())
        for i, d in enumerate(dados):
            tag = "par" if i % 2 == 0 else "impar"
            self._tree_clientes.insert(
                "",
                "end",
                tags=(tag,),
                values=(d.nome, _brl(d.total_comprado), d.quantidade_pedidos),
            )

    def _popular_produtos(self, dados: list[TopProduto]) -> None:
        self._tree_produtos.delete(*self._tree_produtos.get_children())
        for i, d in enumerate(dados):
            tag = "par" if i % 2 == 0 else "impar"
            self._tree_produtos.insert(
                "",
                "end",
                tags=(tag,),
                values=(
                    d.nome,
                    f"{d.quantidade_vendida:.2f} {d.unidade}",
                    _brl(d.receita),
                    _brl(d.lucro),
                ),
            )

    def _popular_detalhe(self, dados: list[LinhaDetalhePedido]) -> None:
        self._tree_detalhe.delete(*self._tree_detalhe.get_children())
        for i, d in enumerate(dados):
            tag = "par" if i % 2 == 0 else "impar"
            data_str = d.data_pedido.strftime("%d/%m/%Y") if d.data_pedido else "—"
            self._tree_detalhe.insert(
                "",
                "end",
                tags=(tag,),
                values=(
                    f"#{d.id_pedido}",
                    data_str,
                    d.nome_cliente,
                    d.status.capitalize(),
                    _brl(d.faturamento),
                    _brl(d.custo),
                    _brl(d.lucro),
                ),
            )
