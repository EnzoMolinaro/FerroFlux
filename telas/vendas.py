"""
telas/vendas.py
---------------
Tela de gerenciamento de vendas do FerroFlux.
Embarcada no menu como CTkFrame (single-window navigation).

Fluxo:
    1. Lista de pedidos com filtro por status e busca por cliente
    2. Formulário para criar/editar pedido (cliente + endereço + itens)
    3. Painel lateral com detalhes e ações (confirmar, avançar, cancelar, NF)
    4. Visualizador de template de Nota Fiscal (janela modal separada)
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from typing import Any, Callable, Literal, cast

import customtkinter as ctk
import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError, obter_conexao
from repositories.material_repo import Material, MaterialRepo
from repositories.usuario_repo import Usuario
from repositories.venda_repo import (
    STATUS_AVANCAR,
    ItemPedido,
    NotaFiscal,
    Pedido,
    VendaRepo,
)
from telas.componentes import (
    BarraStatus,
    Botao,
    CampoTexto,
    CartaoFrame,
    ComboSelecao,
    Rotulo,
    Separador,
    Subtitulo,
    Tema,
    Titulo,
)

AnchorTabela = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]

_COR_STATUS: dict[str, str] = {
    "PENDENTE": "#f59e0b",
    "CONFIRMADO": "#3b82f6",
    "PREPARANDO": "#8b5cf6",
    "ENVIADO": "#06b6d4",
    "ENTREGUE": "#10b981",
    "CANCELADO": "#f43f5e",
}

_ICONE_STATUS: dict[str, str] = {
    "PENDENTE": "🕐",
    "CONFIRMADO": "✅",
    "PREPARANDO": "🔧",
    "ENVIADO": "🚚",
    "ENTREGUE": "📦",
    "CANCELADO": "❌",
}


def _aplicar_estilo_tabela() -> None:
    """Aplica o estilo visual customizado à Treeview de pedidos."""
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Venda.Treeview",
        background=Tema.FUNDO_INPUT,
        foreground=Tema.TEXTO_PRINCIPAL,
        fieldbackground=Tema.FUNDO_INPUT,
        rowheight=38,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_CORPO),
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Venda.Treeview.Heading",
        background=Tema.FUNDO_JANELA,
        foreground=Tema.TEXTO_SECUNDARIO,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_LABEL, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Venda.Treeview",
        background=[("selected", Tema.PRIMARIO)],
        foreground=[("selected", "#ffffff")],
    )
    style.map("Venda.Treeview.Heading", background=[("active", Tema.NEUTRO)])
    style.layout("Venda.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


_COLUNAS: list[tuple[str, str, int, AnchorTabela]] = [
    ("id", "Nº", 60, "center"),
    ("cliente", "Cliente", 240, "w"),
    ("data", "Data", 120, "center"),
    ("status", "Status", 110, "center"),
    ("total", "Total (R$)", 110, "e"),
]


class _TabelaPedidos(ctk.CTkFrame):
    """Frame com Treeview para listagem de pedidos."""

    def __init__(self, master: ctk.CTkFrame, **kwargs: Any) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        super().__init__(master, **kwargs)
        _aplicar_estilo_tabela()
        self._callback: Callable[[Pedido], None] | None = None
        self._pedidos: list[Pedido] = []
        self._construir()

    def _construir(self) -> None:
        """Monta a Treeview com scrollbars."""
        colunas = [c[0] for c in _COLUNAS]
        sb_y = tk.Scrollbar(
            self,
            orient="vertical",
            bg=Tema.SCROLL_FUNDO,
            troughcolor=Tema.FUNDO_INPUT,
            activebackground=Tema.PRIMARIO,
            highlightthickness=0,
            bd=0,
        )
        sb_x = tk.Scrollbar(
            self,
            orient="horizontal",
            bg=Tema.SCROLL_FUNDO,
            troughcolor=Tema.FUNDO_INPUT,
            activebackground=Tema.PRIMARIO,
            highlightthickness=0,
            bd=0,
        )
        self._tree = ttk.Treeview(
            self,
            columns=colunas,
            show="headings",
            style="Venda.Treeview",
            selectmode="browse",
            yscrollcommand=sb_y.set,
            xscrollcommand=sb_x.set,
        )

        for col_id, cab, larg, anchor in _COLUNAS:
            self._tree.heading(col_id, text=cab)
            self._tree.column(
                col_id, width=larg, minwidth=larg, anchor=anchor  # type: ignore[arg-type]
            )

        sb_y.config(command=self._tree.yview)
        sb_x.config(command=self._tree.xview)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        sb_y.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=8)
        sb_x.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 4))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tree.tag_configure("par", background=Tema.FUNDO_INPUT)
        self._tree.tag_configure("impar", background=Tema.FUNDO_CARD)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def popular(self, pedidos: list[Pedido]) -> None:
        """Preenche a tabela com a lista de pedidos fornecida."""
        self._pedidos = pedidos
        self._tree.delete(*self._tree.get_children())
        for i, p in enumerate(pedidos):
            tag = "par" if i % 2 == 0 else "impar"
            data_str = (
                p.data_pedido.strftime("%d/%m/%Y %H:%M") if p.data_pedido else "—"
            )
            icone = _ICONE_STATUS.get(p.status, "")
            status_str = f"{icone} {p.status.capitalize()}"
            total_str = (
                f"R$ {p.valor_total:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            self._tree.insert(
                "",
                "end",
                iid=str(i),
                tags=(tag,),
                values=(
                    f"#{p.id_pedido}",
                    p.nome_cliente,
                    data_str,
                    status_str,
                    total_str,
                ),
            )

    def ao_selecionar(self, callback: Callable[[Pedido], None]) -> None:
        """Registra o callback chamado ao selecionar uma linha."""
        self._callback = callback

    def _on_select(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        """Dispara o callback ao selecionar uma linha na Treeview."""
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self._pedidos) and self._callback:
            self._callback(self._pedidos[idx])


class _PainelDetalhe(ctk.CTkFrame):
    """Painel lateral com detalhes e ações do pedido selecionado."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        ao_editar: Callable[[Pedido], None],
        ao_confirmar: Callable[[Pedido], None],
        ao_avancar: Callable[[Pedido], None],
        ao_cancelar: Callable[[Pedido], None],
        ao_nota_fiscal: Callable[[Pedido], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=Tema.FUNDO_CARD,
            corner_radius=16,
            border_width=1,
            border_color=Tema.BORDA_CARD,
            width=290,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._pedido: Pedido | None = None
        self._ao_editar = ao_editar
        self._ao_confirmar = ao_confirmar
        self._ao_avancar = ao_avancar
        self._ao_cancelar = ao_cancelar
        self._ao_nota_fiscal = ao_nota_fiscal
        self._campos: dict[str, ctk.CTkLabel] = {}
        self._btn_editar: ctk.CTkButton
        self._btn_confirmar: ctk.CTkButton
        self._btn_avancar: ctk.CTkButton
        self._btn_cancelar: ctk.CTkButton
        self._btn_nf: ctk.CTkButton
        self._frame_itens: ctk.CTkFrame
        self._construir()

    def _construir(self) -> None:
        """Monta os widgets do painel de detalhe."""
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)

        self._lbl_status = ctk.CTkLabel(
            self._scroll,
            text="",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            fg_color="transparent",
            anchor="w",
        )
        self._lbl_status.pack(anchor="w", padx=16, pady=(16, 0))

        self._lbl_titulo = ctk.CTkLabel(
            self._scroll,
            text="Selecione\num pedido",
            font=Tema.fonte_titulo(Tema.TAMANHO_H2),
            text_color=Tema.TEXTO_TITULO,
            fg_color="transparent",
            justify="left",
            anchor="w",
            wraplength=250,
        )
        self._lbl_titulo.pack(anchor="w", padx=16, pady=(2, 2))

        self._lbl_id = ctk.CTkLabel(
            self._scroll,
            text="",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        )
        self._lbl_id.pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkFrame(
            self._scroll, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0
        ).pack(fill="x", padx=16, pady=(0, 12))

        for label, chave in [
            ("Data do pedido", "data"),
            ("Valor total", "total"),
            ("Endereço", "endereco"),
            ("Observações", "obs"),
        ]:
            bloco = ctk.CTkFrame(self._scroll, fg_color="transparent")
            bloco.pack(fill="x", padx=16, pady=(0, 10))
            ctk.CTkLabel(
                bloco,
                text=label,
                font=Tema.fonte(Tema.TAMANHO_PEQUENO),
                text_color=Tema.TEXTO_SECUNDARIO,
                fg_color="transparent",
                anchor="w",
            ).pack(anchor="w")
            val = ctk.CTkLabel(
                bloco,
                text="—",
                font=Tema.fonte(Tema.TAMANHO_LABEL, "bold"),
                text_color=Tema.TEXTO_PRINCIPAL,
                fg_color="transparent",
                anchor="w",
                wraplength=250,
                justify="left",
            )
            val.pack(anchor="w")
            self._campos[chave] = val

        ctk.CTkLabel(
            self._scroll,
            text="Itens",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(4, 2))
        self._frame_itens = ctk.CTkFrame(
            self._scroll,
            fg_color=Tema.FUNDO_INPUT,
            corner_radius=8,
            border_width=1,
            border_color=Tema.BORDA_CARD,
        )
        self._frame_itens.pack(fill="x", padx=16, pady=(0, 12))

        rodape = ctk.CTkFrame(self, fg_color=Tema.FUNDO_CARD, corner_radius=0)
        rodape.pack(fill="x", side="bottom")
        ctk.CTkFrame(rodape, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).pack(
            fill="x"
        )

        self._btn_editar = Botao(
            rodape,
            "✏  Editar",
            variante="primario",
            ao_clicar=lambda: (self._ao_editar(self._pedido) if self._pedido else None),
        )
        self._btn_confirmar = Botao(
            rodape,
            "✅  Confirmar",
            variante="sucesso",
            ao_clicar=lambda: (
                self._ao_confirmar(self._pedido) if self._pedido else None
            ),
        )
        self._btn_avancar = Botao(
            rodape,
            "▶  Avançar",
            variante="primario",
            ao_clicar=lambda: (
                self._ao_avancar(self._pedido) if self._pedido else None
            ),
        )
        self._btn_cancelar = Botao(
            rodape,
            "❌  Cancelar",
            variante="perigo",
            ao_clicar=lambda: (
                self._ao_cancelar(self._pedido) if self._pedido else None
            ),
        )
        self._btn_nf = Botao(
            rodape,
            "🧾  Nota Fiscal",
            variante="aviso",
            ao_clicar=lambda: (
                self._ao_nota_fiscal(self._pedido) if self._pedido else None
            ),
        )

        for btn in (
            self._btn_editar,
            self._btn_confirmar,
            self._btn_avancar,
            self._btn_cancelar,
            self._btn_nf,
        ):
            btn.pack(fill="x", padx=16, pady=(8, 0))
            btn.configure(state="disabled")
        self._btn_cancelar.pack(pady=(8, 4))
        self._btn_nf.pack(pady=(0, 16))

    def exibir(self, pedido: Pedido) -> None:
        """Exibe os detalhes do pedido no painel lateral."""
        self._pedido = pedido
        status = pedido.status
        cor = _COR_STATUS.get(status, Tema.TEXTO_SECUNDARIO)
        icone = _ICONE_STATUS.get(status, "")

        self._lbl_status.configure(
            text=f"{icone}  {status.capitalize()}", text_color=cor
        )
        self._lbl_titulo.configure(text=pedido.nome_cliente)
        self._lbl_id.configure(text=f"Pedido #{pedido.id_pedido}")

        data_str = (
            pedido.data_pedido.strftime("%d/%m/%Y às %H:%M")
            if pedido.data_pedido
            else "—"
        )
        total_str = (
            f"R$ {pedido.valor_total:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        self._campos["data"].configure(text=data_str)
        self._campos["total"].configure(text=total_str, text_color=Tema.SUCESSO)
        self._campos["endereco"].configure(text=pedido.endereco_entrega or "—")
        obs = pedido.observacoes or "—"
        self._campos["obs"].configure(text=(obs[:80] + "…") if len(obs) > 80 else obs)

        for w in self._frame_itens.winfo_children():
            w.destroy()
        if pedido.itens:
            for item in pedido.itens:
                linha = ctk.CTkFrame(self._frame_itens, fg_color="transparent")
                linha.pack(fill="x", padx=10, pady=3)
                ctk.CTkLabel(
                    linha,
                    text=item.nome_produto,
                    font=Tema.fonte(Tema.TAMANHO_PEQUENO),
                    text_color=Tema.TEXTO_PRINCIPAL,
                    fg_color="transparent",
                    anchor="w",
                ).pack(side="left", fill="x", expand=True)
                sub = (
                    f"R$ {item.subtotal:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                ctk.CTkLabel(
                    linha,
                    text=sub,
                    font=Tema.fonte(Tema.TAMANHO_PEQUENO, "bold"),
                    text_color=Tema.TEXTO_PRINCIPAL,
                    fg_color="transparent",
                    anchor="e",
                ).pack(side="right")
                ctk.CTkLabel(
                    linha,
                    text=(
                        f"{item.quantidade:.2f} {item.unidade}"
                        f" × R$ {item.preco_unitario:.2f}"
                    ),
                    font=Tema.fonte(Tema.TAMANHO_PEQUENO),
                    text_color=Tema.TEXTO_SECUNDARIO,
                    fg_color="transparent",
                    anchor="w",
                ).pack(anchor="w")
        else:
            ctk.CTkLabel(
                self._frame_itens,
                text="Sem itens",
                font=Tema.fonte(Tema.TAMANHO_PEQUENO),
                text_color=Tema.TEXTO_PLACEHOLDER,
                fg_color="transparent",
            ).pack(pady=8)

        self._btn_editar.configure(
            state="normal" if status == "PENDENTE" else "disabled"
        )
        self._btn_confirmar.configure(
            state="normal" if status == "PENDENTE" else "disabled"
        )
        pode_avancar = status in STATUS_AVANCAR
        self._btn_avancar.configure(state="normal" if pode_avancar else "disabled")
        pode_cancelar = status not in ("ENTREGUE", "CANCELADO")
        self._btn_cancelar.configure(state="normal" if pode_cancelar else "disabled")
        pode_nf = status not in ("PENDENTE", "CANCELADO")
        self._btn_nf.configure(state="normal" if pode_nf else "disabled")

    def limpar(self) -> None:
        """Reseta o painel para o estado inicial (sem pedido selecionado)."""
        self._pedido = None
        self._lbl_status.configure(text="")
        self._lbl_titulo.configure(text="Selecione\num pedido")
        self._lbl_id.configure(text="")
        for campo in self._campos.values():
            campo.configure(text="—", text_color=Tema.TEXTO_PRINCIPAL)
        for w in self._frame_itens.winfo_children():
            w.destroy()
        for btn in (
            self._btn_editar,
            self._btn_confirmar,
            self._btn_avancar,
            self._btn_cancelar,
            self._btn_nf,
        ):
            btn.configure(state="disabled")


# ---------------------------------------------------------------------------
# Tela principal de Vendas — CTkFrame (embedded)
# ---------------------------------------------------------------------------


class TelaVendas(ctk.CTkFrame):
    """Tela de gerenciamento de vendas/pedidos. Embarcada no menu."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        usuario: Usuario | None = None,
    ) -> None:
        super().__init__(master, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._usuario = usuario
        self._pedidos: list[Pedido] = []
        self._filtrados: list[Pedido] = []

        self._campo_busca: CampoTexto
        self._combo_status: ComboSelecao
        self._tabela: _TabelaPedidos
        self._painel: _PainelDetalhe
        self._barra: BarraStatus

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._construir_ui()
        self._carregar()

    def _construir_ui(self) -> None:
        """Monta a interface da tela de vendas."""
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        topo.columnconfigure(1, weight=1)

        Titulo(topo, "💰  Vendas").grid(row=0, column=0, sticky="w")

        filtros = ctk.CTkFrame(topo, fg_color="transparent")
        filtros.grid(row=0, column=1, sticky="ew", padx=24)
        filtros.columnconfigure(0, weight=1)

        self._campo_busca = CampoTexto(filtros, placeholder="🔍  Buscar por cliente...")
        self._campo_busca.grid(row=0, column=0, sticky="ew")
        self._campo_busca.bind("<KeyRelease>", lambda _: self._filtrar())

        self._combo_status = ComboSelecao(
            filtros,
            valores=[
                "TODOS",
                "PENDENTE",
                "CONFIRMADO",
                "PREPARANDO",
                "ENVIADO",
                "ENTREGUE",
                "CANCELADO",
            ],
            width=160,
        )
        self._combo_status.set("TODOS")
        self._combo_status.grid(row=0, column=1, padx=(10, 0))
        self._combo_status.bind("<<ComboboxSelected>>", lambda _: self._carregar())

        Botao(
            topo, "+ Novo Pedido", variante="sucesso", ao_clicar=self._novo_pedido
        ).grid(row=0, column=2, sticky="e")

        ctk.CTkFrame(self, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=24, pady=(12, 0)
        )

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="nsew", padx=24, pady=12)
        corpo.grid_rowconfigure(0, weight=1)
        corpo.grid_columnconfigure(0, weight=1)

        self._tabela = _TabelaPedidos(corpo)
        self._tabela.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._tabela.ao_selecionar(self._ao_selecionar)

        self._painel = _PainelDetalhe(
            corpo,
            ao_editar=self._editar_pedido,
            ao_confirmar=self._confirmar_pedido,
            ao_avancar=self._avancar_status,
            ao_cancelar=self._cancelar_pedido,
            ao_nota_fiscal=self._abrir_nota_fiscal,
        )
        self._painel.grid(row=0, column=1, sticky="nsew")

        self._barra = BarraStatus(self)
        self._barra.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))

    def _carregar(self) -> None:
        """Carrega os pedidos do banco aplicando o filtro de status."""
        status = self._combo_status.get()
        try:
            with obter_conexao() as conn:
                repo = VendaRepo(conn)
                self._pedidos = repo.listar_pedidos(
                    status=status if status != "TODOS" else None
                )
                for p in self._pedidos:
                    p.itens = repo.listar_itens(p.id_pedido)  # type: ignore[arg-type]
        except ConexaoError as e:
            self._barra.erro(str(e))
            return
        self._painel.limpar()
        self._filtrar()

    def _filtrar(self) -> None:
        """Filtra os pedidos carregados pelo termo de busca."""
        termo = self._campo_busca.get().strip().lower()
        self._filtrados = (
            [p for p in self._pedidos if termo in p.nome_cliente.lower()]
            if termo
            else list(self._pedidos)
        )
        self._tabela.popular(self._filtrados)
        total = len(self._filtrados)
        if termo:
            msg = f"{total} resultado(s) para" f' "{self._campo_busca.get().strip()}".'
        else:
            msg = f"{total} pedido(s) encontrado(s)."
        self._barra.info(msg)

    def _ao_selecionar(self, pedido: Pedido) -> None:
        """Exibe o detalhe do pedido selecionado na tabela."""
        self._painel.exibir(pedido)

    def _novo_pedido(self) -> None:
        """Abre o formulário para criação de novo pedido."""
        _JanelaPedido(
            cast(ctk.CTk, self.winfo_toplevel()),
            pedido=None,
            usuario=self._usuario,
            ao_salvar=self._carregar,
        ).grab_set()

    def _editar_pedido(self, pedido: Pedido) -> None:
        """Abre o formulário de edição para o pedido informado."""
        _JanelaPedido(
            cast(ctk.CTk, self.winfo_toplevel()),
            pedido=pedido,
            usuario=self._usuario,
            ao_salvar=self._carregar,
        ).grab_set()

    def _confirmar_pedido(self, pedido: Pedido) -> None:
        """Confirma o pedido e atualiza o estoque."""
        if pedido.id_pedido is None:
            return
        id_usuario = self._usuario.id if self._usuario else 0
        try:
            with obter_conexao() as conn:
                VendaRepo(conn).confirmar_pedido(pedido.id_pedido, id_usuario)
            self._barra.sucesso(
                f"Pedido #{pedido.id_pedido} confirmado! Estoque atualizado."
            )
        except (
            ConexaoError,
            ValueError,
            pyodbc.Error,
        ) as e:  # pylint: disable=c-extension-no-member
            self._barra.erro(str(e))
        self._carregar()

    def _avancar_status(self, pedido: Pedido) -> None:
        """Avança o status do pedido para o próximo estágio."""
        if pedido.id_pedido is None:
            return
        try:
            with obter_conexao() as conn:
                novo = VendaRepo(conn).avancar_status(pedido.id_pedido)
            self._barra.sucesso(f"Pedido #{pedido.id_pedido} → {novo.capitalize()}.")
        except (
            ConexaoError,
            ValueError,
            pyodbc.Error,
        ) as e:  # pylint: disable=c-extension-no-member
            self._barra.erro(str(e))
        self._carregar()

    def _cancelar_pedido(self, pedido: Pedido) -> None:
        """Cancela o pedido selecionado."""
        if pedido.id_pedido is None:
            return
        id_usuario = self._usuario.id if self._usuario else 0
        try:
            with obter_conexao() as conn:
                VendaRepo(conn).cancelar_pedido(pedido.id_pedido, id_usuario)
            self._barra.sucesso(f"Pedido #{pedido.id_pedido} cancelado.")
        except (
            ConexaoError,
            ValueError,
            pyodbc.Error,
        ) as e:  # pylint: disable=c-extension-no-member
            self._barra.erro(str(e))
        self._carregar()

    def _abrir_nota_fiscal(self, pedido: Pedido) -> None:
        """Busca ou emite a NF do pedido e abre o visualizador."""
        if pedido.id_pedido is None:
            return
        try:
            with obter_conexao() as conn:
                repo = VendaRepo(conn)
                nf = repo.buscar_nota_fiscal(pedido.id_pedido)
                if nf is None:
                    id_emitente = 1  # pylint: disable=fixme
                    repo.emitir_nota_fiscal(
                        id_pedido=pedido.id_pedido,
                        id_emitente=id_emitente,
                        id_destinatario=pedido.id_cliente,
                    )
                    nf = repo.buscar_nota_fiscal(pedido.id_pedido)
        except (
            ConexaoError,
            ValueError,
            pyodbc.Error,
        ) as e:  # pylint: disable=c-extension-no-member
            self._barra.erro(str(e))
            return

        if nf is None:
            self._barra.erro("Não foi possível gerar a Nota Fiscal.")
            return

        _JanelaNotaFiscal(
            cast(ctk.CTk, self.winfo_toplevel()), pedido=pedido, nota=nf
        ).grab_set()


# ---------------------------------------------------------------------------
# Formulário de pedido — CTkToplevel (modal)
# ---------------------------------------------------------------------------


class _JanelaPedido(ctk.CTkToplevel):
    """Formulário modal para criação e edição de pedidos."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        pedido: Pedido | None,
        usuario: Usuario | None,
        ao_salvar: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._pedido = pedido
        self._usuario = usuario
        self._ao_salvar = ao_salvar
        self._editando = pedido is not None
        self._itens: list[ItemPedido] = list(pedido.itens) if pedido else []
        self._clientes: list[tuple[int, str]] = []
        self._enderecos: list[tuple[int, str]] = []
        self._materiais: list[Material] = []
        self._id_pedido_rascunho: int | None = pedido.id_pedido if pedido else None

        self._combo_cliente: ComboSelecao
        self._combo_endereco: ComboSelecao
        self._f_obs: CampoTexto
        self._combo_material: ComboSelecao
        self._f_qtd: CampoTexto
        self._lbl_estoque: ctk.CTkLabel
        self._frame_itens: ctk.CTkFrame
        self._lbl_total: ctk.CTkLabel
        self._barra: BarraStatus

        titulo = "Editar Pedido" if self._editando else "Novo Pedido"
        self.title(f"FerroFlux — {titulo}")
        self.geometry("720x700")
        self.minsize(660, 620)
        self.resizable(True, True)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()
        self._carregar_dados()
        self._construir_ui()
        if self._editando and pedido:
            self._preencher(pedido)
        if self._erro_carga:
            self._barra.erro(self._erro_carga)

    def _centralizar(self) -> None:
        """Centraliza a janela na tela."""
        self.update_idletasks()
        w, h = 720, 700
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _carregar_dados(self) -> None:
        """Carrega clientes e materiais disponíveis do banco."""
        self._erro_carga: str | None = None
        try:
            with obter_conexao() as conn:
                self._clientes = VendaRepo(conn).listar_clientes()
                self._materiais = MaterialRepo(conn).listar_todos(apenas_ativos=True)
        except ConexaoError as e:
            self._erro_carga = f"Erro de conexão ao carregar dados: {e}"
        except pyodbc.Error as e:  # pylint: disable=c-extension-no-member
            self._erro_carga = f"Erro no banco ao carregar dados: {e}"

    def _construir_ui(self) -> None:
        """Monta todos os widgets do formulário de pedido."""
        raiz = ctk.CTkFrame(self, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        raiz.pack(fill="both", expand=True)
        raiz.grid_rowconfigure(0, weight=1)
        raiz.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(raiz, fg_color=Tema.FUNDO_JANELA)
        scroll.grid(row=0, column=0, sticky="nsew")

        card = CartaoFrame(scroll)  # type: ignore[arg-type]
        card.pack(fill="x", padx=20, pady=16)

        prefixo = "✏  Editar" if self._editando else "💰  Novo"
        Titulo(card, f"{prefixo} Pedido").pack(pady=(22, 2), padx=24, anchor="w")
        Subtitulo(card, "Preencha os dados do pedido.").pack(padx=24, anchor="w")
        Separador(card).pack(fill="x", padx=24, pady=12)

        Rotulo(card, "Cliente: *").pack(anchor="w", padx=24, pady=(0, 2))
        nomes_clientes = [f"{cid} — {nome}" for cid, nome in self._clientes]
        self._combo_cliente = ComboSelecao(card, valores=nomes_clientes)
        self._combo_cliente.pack(fill="x", padx=24)
        self._combo_cliente.bind(
            "<<ComboboxSelected>>", lambda _: self._ao_trocar_cliente()
        )

        Rotulo(card, "Endereço de entrega:").pack(anchor="w", padx=24, pady=(10, 2))
        self._combo_endereco = ComboSelecao(
            card, valores=["— Selecione o cliente primeiro —"]
        )
        self._combo_endereco.pack(fill="x", padx=24)

        Rotulo(card, "Observações:").pack(anchor="w", padx=24, pady=(10, 2))
        self._f_obs = CampoTexto(
            card, placeholder="Informações adicionais sobre o pedido..."
        )
        self._f_obs.pack(fill="x", padx=24)

        Separador(card).pack(fill="x", padx=24, pady=12)
        Rotulo(card, "Itens do pedido: *").pack(anchor="w", padx=24, pady=(0, 8))

        frame_add = ctk.CTkFrame(
            card,
            fg_color=Tema.FUNDO_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=Tema.BORDA_CARD,
        )
        frame_add.pack(fill="x", padx=24, pady=(0, 8))
        frame_add.columnconfigure(0, weight=1)

        nomes_mat = [f"{m.id} — {m.nome} ({m.unidade})" for m in self._materiais]
        Rotulo(frame_add, "Produto:").grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 2)
        )
        self._combo_material = ComboSelecao(frame_add, valores=nomes_mat)
        self._combo_material.grid(row=1, column=0, sticky="ew", padx=12)

        Rotulo(frame_add, "Qtd:").grid(row=0, column=1, sticky="w", padx=(8, 12))
        self._f_qtd = CampoTexto(frame_add, placeholder="0.00", width=90)
        self._f_qtd.grid(row=1, column=1, padx=(8, 12))

        self._lbl_estoque = ctk.CTkLabel(
            frame_add,
            text="Estoque: —",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
        )
        self._lbl_estoque.grid(row=2, column=0, sticky="w", padx=12, pady=(4, 10))

        Botao(
            frame_add,
            "+ Adicionar",
            variante="primario",
            ao_clicar=self._adicionar_item,
            width=110,
            height=36,
        ).grid(row=1, column=2, padx=(0, 12))

        self._combo_material.bind(
            "<<ComboboxSelected>>", lambda _: self._ao_trocar_material()
        )

        self._frame_itens = ctk.CTkFrame(card, fg_color="transparent")
        self._frame_itens.pack(fill="x", padx=24)

        self._lbl_total = ctk.CTkLabel(
            card,
            text="Total: R$ 0,00",
            font=Tema.fonte_titulo(Tema.TAMANHO_H2),
            text_color=Tema.SUCESSO,
            fg_color="transparent",
            anchor="e",
        )
        self._lbl_total.pack(anchor="e", padx=24, pady=(12, 0))

        Separador(card).pack(fill="x", padx=24, pady=12)

        self._barra = BarraStatus(card)
        self._barra.pack(fill="x", padx=24, pady=(0, 8))

        fb = ctk.CTkFrame(card, fg_color="transparent")
        fb.pack(fill="x", padx=24, pady=(0, 24))
        fb.columnconfigure((0, 1), weight=1)
        Botao(fb, "Cancelar", variante="neutro", ao_clicar=self.destroy).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        Botao(fb, "💾  Salvar Pedido", variante="sucesso", ao_clicar=self._salvar).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        self._atualizar_lista_itens()

    def _preencher(self, pedido: Pedido) -> None:
        """Preenche os campos com os dados de um pedido existente."""
        for i, (cid, _) in enumerate(self._clientes):
            if cid == pedido.id_cliente:
                self._combo_cliente.set(self._combo_cliente.cget("values")[i])
                self._ao_trocar_cliente()
                break
        self._f_obs.insert(0, pedido.observacoes or "")

    def _id_cliente_selecionado(self) -> int | None:
        """Retorna o ID do cliente atualmente selecionado no combo."""
        val = self._combo_cliente.get()
        if not val or "—" not in val:
            return None
        try:
            return int(val.split("—")[0].strip())
        except ValueError:
            return None

    def _ao_trocar_cliente(self) -> None:
        """Atualiza o combo de endereços ao trocar o cliente."""
        id_cliente = self._id_cliente_selecionado()
        if id_cliente is None:
            return
        try:
            with obter_conexao() as conn:
                enderecos = VendaRepo(conn).listar_enderecos_cliente(id_cliente)
        except ConexaoError as e:
            enderecos = []
            self._barra.erro(f"Não foi possível carregar endereços: {e}")
        except pyodbc.Error as e:  # pylint: disable=c-extension-no-member
            enderecos = []
            self._barra.erro(f"Erro no banco ao carregar endereços: {e}")
        self._enderecos = enderecos
        valores = [desc for _, desc in enderecos] or ["— Sem endereços cadastrados —"]
        self._combo_endereco.configure(values=valores)
        self._combo_endereco.set(valores[0])

    def _ao_trocar_material(self) -> None:
        """Atualiza o label de estoque ao trocar o material selecionado."""
        val = self._combo_material.get()
        if not val or "—" not in val:
            return
        try:
            id_prod = int(val.split("—")[0].strip())
            with obter_conexao() as conn:
                est = VendaRepo(conn).estoque_disponivel(id_prod)
            unidade = next((m.unidade for m in self._materiais if m.id == id_prod), "")
            self._lbl_estoque.configure(
                text=f"Estoque disponível: {est:.2f} {unidade}",
                text_color=Tema.SUCESSO if est > 0 else Tema.PERIGO,
            )
        except (ValueError, ConexaoError):
            self._lbl_estoque.configure(
                text="Estoque: —", text_color=Tema.TEXTO_SECUNDARIO
            )

    def _adicionar_item(self) -> None:
        """Valida e adiciona um item à lista do pedido."""
        val = self._combo_material.get()
        if not val or "—" not in val:
            self._barra.erro("Selecione um produto.")
            return
        try:
            id_prod = int(val.split("—")[0].strip())
        except ValueError:
            self._barra.erro("Produto inválido.")
            return

        try:
            qtd = float(self._f_qtd.get().replace(",", "."))
            if qtd <= 0:
                raise ValueError
        except ValueError:
            self._barra.erro("Informe uma quantidade válida maior que zero.")
            return

        material = next((m for m in self._materiais if m.id == id_prod), None)
        if material is None:
            self._barra.erro("Produto não encontrado.")
            return

        try:
            with obter_conexao() as conn:
                disponivel = VendaRepo(conn).estoque_disponivel(id_prod)
        except ConexaoError as e:
            self._barra.erro(str(e))
            return

        if disponivel < qtd:
            self._barra.erro(
                f"Estoque insuficiente: disponível"
                f" {disponivel:.2f} {material.unidade}."
            )
            return

        self._itens = [it for it in self._itens if it.id_produto != id_prod]
        self._itens.append(
            ItemPedido(
                id_produto=id_prod,
                nome_produto=material.nome,
                unidade=material.unidade,
                quantidade=qtd,
                preco_unitario=material.preco_venda,
            )
        )
        self._f_qtd.delete(0, "end")
        self._atualizar_lista_itens()
        self._barra.info(f"{material.nome} adicionado.")

    def _remover_item(self, id_produto: int) -> None:
        """Remove o item com o id_produto informado da lista."""
        self._itens = [it for it in self._itens if it.id_produto != id_produto]
        self._atualizar_lista_itens()

    def _atualizar_lista_itens(self) -> None:
        """Redesenha a lista de itens e recalcula o total."""
        for w in self._frame_itens.winfo_children():
            w.destroy()

        if not self._itens:
            ctk.CTkLabel(
                self._frame_itens,
                text="Nenhum item adicionado.",
                font=Tema.fonte(Tema.TAMANHO_LABEL),
                text_color=Tema.TEXTO_PLACEHOLDER,
                fg_color="transparent",
            ).pack(pady=8)
        else:
            for item in self._itens:
                linha = ctk.CTkFrame(
                    self._frame_itens,
                    fg_color=Tema.FUNDO_INPUT,
                    corner_radius=8,
                    border_width=1,
                    border_color=Tema.BORDA_CARD,
                )
                linha.pack(fill="x", pady=(0, 6))
                linha.columnconfigure(1, weight=1)

                ctk.CTkLabel(
                    linha,
                    text=item.nome_produto,
                    font=Tema.fonte(Tema.TAMANHO_LABEL, "bold"),
                    text_color=Tema.TEXTO_TITULO,
                    fg_color="transparent",
                    anchor="w",
                ).grid(
                    row=0,
                    column=0,
                    columnspan=2,
                    sticky="w",
                    padx=12,
                    pady=(8, 0),
                )

                sub = (
                    f"R$ {item.subtotal:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                ctk.CTkLabel(
                    linha,
                    text=(
                        f"{item.quantidade:.2f} {item.unidade}"
                        f" × R$ {item.preco_unitario:.2f} = {sub}"
                    ),
                    font=Tema.fonte(Tema.TAMANHO_PEQUENO),
                    text_color=Tema.TEXTO_SECUNDARIO,
                    fg_color="transparent",
                    anchor="w",
                ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

                Botao(
                    linha,
                    "✕",
                    variante="perigo",
                    width=32,
                    height=28,
                    ao_clicar=lambda p=item.id_produto: self._remover_item(p),
                ).grid(row=0, column=2, rowspan=2, padx=(0, 8))

        total = sum(it.subtotal for it in self._itens)
        total_str = (
            f"Total: R$ {total:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        self._lbl_total.configure(text=total_str)

    def _salvar(self) -> None:
        """Valida os dados e persiste o pedido no banco."""
        id_cliente = self._id_cliente_selecionado()
        if id_cliente is None:
            self._barra.erro("Selecione um cliente.")
            return
        if not self._itens:
            self._barra.erro("Adicione ao menos um item ao pedido.")
            return

        valores_end = self._combo_endereco.cget("values")
        val_end = self._combo_endereco.get()
        idx_end = valores_end.index(val_end) if val_end in valores_end else -1
        id_endereco = (
            self._enderecos[idx_end][0] if 0 <= idx_end < len(self._enderecos) else None
        )
        obs = self._f_obs.get().strip()

        self._barra.info("Salvando...")
        self.update_idletasks()

        try:
            with obter_conexao() as conn:
                repo = VendaRepo(conn)
                if self._editando and self._id_pedido_rascunho is not None:
                    repo.atualizar_observacoes(
                        self._id_pedido_rascunho, obs, id_endereco
                    )
                    repo.salvar_itens(self._id_pedido_rascunho, self._itens)
                    self._barra.sucesso("Pedido atualizado com sucesso!")
                else:
                    id_pedido = repo.criar_pedido(id_cliente, obs, id_endereco)
                    repo.salvar_itens(id_pedido, self._itens)
                    self._barra.sucesso(f"Pedido #{id_pedido} criado com sucesso!")

        except (
            ConexaoError,
            ValueError,
            pyodbc.Error,
        ) as e:  # pylint: disable=c-extension-no-member
            self._barra.erro(str(e))
            return

        self._ao_salvar()
        self.after(800, self.destroy)


# ---------------------------------------------------------------------------
# Visualizador de Nota Fiscal — CTkToplevel (modal)
# ---------------------------------------------------------------------------


class _JanelaNotaFiscal(ctk.CTkToplevel):
    """Janela modal de visualização de Nota Fiscal."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        pedido: Pedido,
        nota: NotaFiscal,
    ) -> None:
        super().__init__(master)
        self._pedido = pedido
        self._nota = nota
        self.title(f"FerroFlux — Nota Fiscal #{nota.id_nota}")
        self.geometry("620x780")
        self.resizable(True, True)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()
        self._construir()

    def _centralizar(self) -> None:
        """Centraliza a janela na tela."""
        self.update_idletasks()
        w, h = 620, 780
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _construir(self) -> None:
        """Monta o layout da nota fiscal."""
        scroll = ctk.CTkScrollableFrame(self, fg_color=Tema.FUNDO_JANELA)
        scroll.pack(fill="both", expand=True)

        card = CartaoFrame(scroll)  # type: ignore[arg-type]
        card.pack(fill="x", padx=20, pady=16)

        cab = ctk.CTkFrame(card, fg_color=Tema.PRIMARIO, corner_radius=10)
        cab.pack(fill="x", padx=20, pady=(20, 16))

        ctk.CTkLabel(
            cab,
            text="NOTA FISCAL",
            font=Tema.fonte_titulo(Tema.TAMANHO_H1),
            text_color="#ffffff",
            fg_color="transparent",
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            cab,
            text=f"Nº {self._nota.id_nota:06d}  •  {self._nota.tipo_nota}",
            font=Tema.fonte(Tema.TAMANHO_H3),
            text_color="#dde3f5",
            fg_color="transparent",
        ).pack(pady=(0, 4))
        data_str = (
            self._nota.data_emissao.strftime("%d/%m/%Y %H:%M")
            if self._nota.data_emissao
            else "—"
        )
        ctk.CTkLabel(
            cab,
            text=f"Emitida em {data_str}",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            text_color="#dde3f5",
            fg_color="transparent",
        ).pack(pady=(0, 16))

        def secao(titulo: str) -> ctk.CTkFrame:
            ctk.CTkLabel(
                card,
                text=titulo,
                font=Tema.fonte(Tema.TAMANHO_PEQUENO),
                text_color=Tema.TEXTO_SECUNDARIO,
                fg_color="transparent",
                anchor="w",
            ).pack(anchor="w", padx=20, pady=(12, 2))
            f = ctk.CTkFrame(
                card,
                fg_color=Tema.FUNDO_INPUT,
                corner_radius=8,
                border_width=1,
                border_color=Tema.BORDA_CARD,
            )
            f.pack(fill="x", padx=20, pady=(0, 4))
            return f

        def par(frame: ctk.CTkFrame, rotulo: str, valor: str) -> None:
            linha = ctk.CTkFrame(frame, fg_color="transparent")
            linha.pack(fill="x", padx=14, pady=4)
            linha.columnconfigure(1, weight=1)
            ctk.CTkLabel(
                linha,
                text=rotulo,
                font=Tema.fonte(Tema.TAMANHO_PEQUENO),
                text_color=Tema.TEXTO_SECUNDARIO,
                fg_color="transparent",
                anchor="w",
                width=120,
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                linha,
                text=valor,
                font=Tema.fonte(Tema.TAMANHO_LABEL, "bold"),
                text_color=Tema.TEXTO_PRINCIPAL,
                fg_color="transparent",
                anchor="w",
                wraplength=360,
                justify="left",
            ).grid(row=0, column=1, sticky="w")

        f_emit = secao("EMITENTE")
        par(f_emit, "Razão Social", self._nota.nome_emitente)

        f_dest = secao("DESTINATÁRIO / CLIENTE")
        par(f_dest, "Nome", self._nota.nome_destinatario)
        if self._pedido.endereco_entrega:
            par(f_dest, "Endereço", self._pedido.endereco_entrega)

        f_ped = secao("PEDIDO")
        par(f_ped, "Nº do Pedido", f"#{self._pedido.id_pedido}")
        par(f_ped, "Status", self._pedido.status.capitalize())

        ctk.CTkLabel(
            card,
            text="ITENS",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        ).pack(anchor="w", padx=20, pady=(12, 2))

        f_itens = ctk.CTkFrame(
            card,
            fg_color=Tema.FUNDO_INPUT,
            corner_radius=8,
            border_width=1,
            border_color=Tema.BORDA_CARD,
        )
        f_itens.pack(fill="x", padx=20, pady=(0, 4))

        cab_itens = ctk.CTkFrame(f_itens, fg_color=Tema.NEUTRO, corner_radius=0)
        cab_itens.pack(fill="x")
        cab_itens.columnconfigure(0, weight=1)
        for col, texto, w in [
            (0, "Produto", 0),
            (1, "Qtd", 60),
            (2, "Un.", 40),
            (3, "Preço Unit.", 90),
            (4, "Subtotal", 90),
        ]:
            ctk.CTkLabel(
                cab_itens,
                text=texto,
                font=Tema.fonte(Tema.TAMANHO_PEQUENO, "bold"),
                text_color=Tema.TEXTO_SECUNDARIO,
                fg_color="transparent",
                anchor="w" if col == 0 else "e",
                width=w if w else 0,
            ).grid(
                row=0,
                column=col,
                sticky="ew" if col == 0 else "e",
                padx=(12, 4),
                pady=6,
            )

        for item in self._pedido.itens:
            linha = ctk.CTkFrame(f_itens, fg_color="transparent")
            linha.pack(fill="x")
            linha.columnconfigure(0, weight=1)
            ctk.CTkFrame(
                linha, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0
            ).pack(fill="x")
            conteudo = ctk.CTkFrame(linha, fg_color="transparent")
            conteudo.pack(fill="x")
            conteudo.columnconfigure(0, weight=1)

            sub = (
                f"R$ {item.subtotal:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            pu = (
                f"R$ {item.preco_unitario:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

            ctk.CTkLabel(
                conteudo,
                text=item.nome_produto,
                font=Tema.fonte(Tema.TAMANHO_LABEL),
                text_color=Tema.TEXTO_PRINCIPAL,
                fg_color="transparent",
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=(12, 4), pady=6)
            for col, texto in [
                (1, f"{item.quantidade:.2f}"),
                (2, item.unidade),
                (3, pu),
                (4, sub),
            ]:
                ctk.CTkLabel(
                    conteudo,
                    text=texto,
                    font=Tema.fonte(Tema.TAMANHO_LABEL),
                    text_color=Tema.TEXTO_PRINCIPAL,
                    fg_color="transparent",
                    anchor="e",
                ).grid(row=0, column=col, sticky="e", padx=(0, 12), pady=6)

        f_total = ctk.CTkFrame(card, fg_color=Tema.SUCESSO, corner_radius=10)
        f_total.pack(fill="x", padx=20, pady=12)
        total_str = (
            f"R$ {self._nota.valor_total:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        ctk.CTkLabel(
            f_total,
            text="VALOR TOTAL",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            text_color="#ffffff",
            fg_color="transparent",
        ).pack(side="left", padx=16, pady=14)
        ctk.CTkLabel(
            f_total,
            text=total_str,
            font=Tema.fonte_titulo(Tema.TAMANHO_H1),
            text_color="#ffffff",
            fg_color="transparent",
        ).pack(side="right", padx=16)

        if self._nota.observacoes:
            f_obs = secao("OBSERVAÇÕES")
            ctk.CTkLabel(
                f_obs,
                text=self._nota.observacoes,
                font=Tema.fonte(Tema.TAMANHO_LABEL),
                text_color=Tema.TEXTO_PRINCIPAL,
                fg_color="transparent",
                anchor="w",
                wraplength=520,
                justify="left",
            ).pack(anchor="w", padx=14, pady=10)

        ctk.CTkLabel(
            card,
            text=(
                f"Status da NF: {self._nota.status}" "  •  FerroFlux Sistema de Gestão"
            ),
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_PLACEHOLDER,
            fg_color="transparent",
        ).pack(pady=(8, 20))

        Botao(card, "✕  Fechar", variante="neutro", ao_clicar=self.destroy).pack(
            padx=20, pady=(0, 20)
        )
