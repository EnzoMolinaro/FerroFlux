"""
telas/materiais.py
------------------
Tela de gerenciamento de materiais do FerroFlux.

Funcionalidades:
    - Tabela com colunas (Treeview) e ordenação por clique
    - Busca em tempo real por nome
    - Painel lateral com detalhes e ações sempre visíveis
    - Tela cheia / redimensionável
    - Cadastrar, editar, desativar/reativar materiais
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from typing import Callable, Literal

import customtkinter as ctk
import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError, obter_conexao
from repositories.material_repo import Material, MaterialRepo
from repositories.usuario_repo import Usuario
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

# ---------------------------------------------------------------------------
# Estilo da tabela (ttk.Treeview)
# ---------------------------------------------------------------------------


def _aplicar_estilo_tabela() -> None:
    """Aplica o tema visual ao Treeview, integrado com o Tema do FerroFlux."""
    style = ttk.Style()
    style.theme_use("default")

    style.configure(
        "Materiais.Treeview",
        background=Tema.FUNDO_INPUT,
        foreground=Tema.TEXTO_PRINCIPAL,
        fieldbackground=Tema.FUNDO_INPUT,
        rowheight=36,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_CORPO),
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Materiais.Treeview.Heading",
        background=Tema.FUNDO_JANELA,
        foreground=Tema.TEXTO_SECUNDARIO,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_LABEL, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Materiais.Treeview",
        background=[("selected", Tema.PRIMARIO)],
        foreground=[("selected", "#ffffff")],
    )
    style.map(
        "Materiais.Treeview.Heading",
        background=[("active", Tema.NEUTRO)],
    )
    style.layout(
        "Materiais.Treeview",
        [
            ("Treeview.treearea", {"sticky": "nswe"}),
        ],
    )


# ---------------------------------------------------------------------------
# Tabela de materiais
# ---------------------------------------------------------------------------

AnchorTabela = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]
_COLUNAS: list[tuple[str, str, int, AnchorTabela]] = [
    # (id_coluna, cabeçalho, largura_min, anchor)
    ("nome", "Nome", 220, "w"),
    ("unidade", "Unid.", 60, "center"),
    ("custo", "Custo (R$)", 100, "e"),
    ("venda", "Venda (R$)", 100, "e"),
    ("estoque", "Estoque", 100, "e"),
    ("minimo", "Mínimo", 80, "e"),
    ("status", "Status", 80, "center"),
]


class _TabelaMateriais(ctk.CTkFrame):
    """
    Treeview estilizado com scrollbar, cabeçalhos clicáveis para ordenar,
    e callback de seleção.
    """

    def __init__(self, master: ctk.CTkFrame, **kwargs) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        super().__init__(master, **kwargs)

        _aplicar_estilo_tabela()
        self._ordem: dict[str, bool] = {}  # coluna -> crescente?
        self._callback_selecao: Callable[[Material], None] | None = None
        self._materiais: list[Material] = []

        self._construir()

    def _construir(self) -> None:
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
            style="Materiais.Treeview",
            selectmode="browse",
            yscrollcommand=sb_y.set,
            xscrollcommand=sb_x.set,
        )

        for col_id, cabecalho, largura, anchor in _COLUNAS:
            self._tree.heading(
                col_id,
                text=cabecalho,
                command=lambda c=col_id: self._ordenar(c),
            )
            self._tree.column(col_id, width=largura, minwidth=largura, anchor=anchor)

        sb_y.config(command=self._tree.yview)
        sb_x.config(command=self._tree.xview)

        self._tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        sb_y.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=8)
        sb_x.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 4))

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Linhas alternadas
        self._tree.tag_configure("par", background=Tema.FUNDO_INPUT)
        self._tree.tag_configure("impar", background=Tema.FUNDO_CARD)
        self._tree.tag_configure("inativo", foreground=Tema.TEXTO_PLACEHOLDER)

    def popular(self, materiais: list[Material]) -> None:
        self._materiais = materiais
        self._tree.delete(*self._tree.get_children())
        for i, m in enumerate(materiais):
            tag_linha = "par" if i % 2 == 0 else "impar"
            tags: list[str] = [tag_linha]
            if not m.ativo:
                tags.append("inativo")
            self._tree.insert(
                "",
                "end",
                iid=str(i),
                tags=tags,
                values=(
                    m.nome,
                    m.unidade,
                    f"{m.preco_custo:,.2f}",
                    f"{m.preco_venda:,.2f}",
                    f"{m.estoque_atual:,.2f}",
                    f"{m.estoque_minimo:,.2f}",
                    "✅ Ativo" if m.ativo else "❌ Inativo",
                ),
            )

    def limpar_selecao(self) -> None:
        self._tree.selection_remove(self._tree.selection())

    def ao_selecionar(self, callback: Callable[[Material], None]) -> None:
        self._callback_selecao = callback

    def _on_select(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self._materiais) and self._callback_selecao:
            self._callback_selecao(self._materiais[idx])

    def _ordenar(self, coluna: str) -> None:
        crescente = not self._ordem.get(coluna, False)
        self._ordem[coluna] = crescente

        mapa = {
            "nome": "nome",
            "unidade": "unidade",
            "custo": "preco_custo",
            "venda": "preco_venda",
            "estoque": "estoque_atual",
            "minimo": "estoque_minimo",
            "status": "ativo",
        }
        attr = mapa.get(coluna, "nome")
        self._materiais.sort(key=lambda m: getattr(m, attr), reverse=not crescente)
        self.popular(self._materiais)

        # Atualiza seta no cabeçalho
        for c, cab, *_ in _COLUNAS:
            seta = (" ↑" if crescente else " ↓") if c == coluna else ""
            self._tree.heading(c, text=cab + seta)


# ---------------------------------------------------------------------------
# Painel lateral de detalhes
# ---------------------------------------------------------------------------


class _PainelDetalhe(ctk.CTkFrame):
    """Painel lateral: detalhes do item selecionado + botões fixos no fundo."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        ao_editar: Callable[[Material], None],
        ao_toggle: Callable[[Material], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=Tema.FUNDO_CARD,
            corner_radius=16,
            border_width=1,
            border_color=Tema.BORDA_CARD,
            width=260,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._ao_editar = ao_editar
        self._ao_toggle = ao_toggle
        self._material: Material | None = None
        self._construir()

    def _construir(self) -> None:
        # Área de rolagem para os detalhes
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._titulo = ctk.CTkLabel(
            self._scroll,
            text="Selecione\num item",
            font=Tema.fonte_titulo(Tema.TAMANHO_H2),
            text_color=Tema.TEXTO_TITULO,
            fg_color="transparent",
            justify="left",
            anchor="w",
            wraplength=220,
        )
        self._titulo.pack(anchor="w", padx=16, pady=(20, 2))

        self._subtitulo = ctk.CTkLabel(
            self._scroll,
            text="",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        )
        self._subtitulo.pack(anchor="w", padx=16, pady=(0, 12))

        # Linha separadora
        ctk.CTkFrame(
            self._scroll, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0
        ).pack(fill="x", padx=16, pady=(0, 12))

        # Campos de detalhe
        self._campos: dict[str, ctk.CTkLabel] = {}
        linhas = [
            ("Unidade", "unidade"),
            ("Preço custo", "custo"),
            ("Preço venda", "venda"),
            ("Estoque atual", "estoque"),
            ("Estoque mín.", "minimo"),
            ("Localização", "local"),
            ("Status", "ativo"),
            ("Descrição", "descricao"),
        ]
        for label, chave in linhas:
            bloco = ctk.CTkFrame(self._scroll, fg_color="transparent")
            bloco.pack(fill="x", padx=16, pady=(0, 8))
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
                wraplength=220,
                justify="left",
            )
            val.pack(anchor="w")
            self._campos[chave] = val

        # Botões FIXOS no fundo (fora do scroll)
        rodape = ctk.CTkFrame(self, fg_color=Tema.FUNDO_CARD, corner_radius=0)
        rodape.pack(fill="x", side="bottom", padx=0, pady=0)

        ctk.CTkFrame(rodape, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).pack(
            fill="x"
        )

        self._btn_editar = Botao(
            rodape, "✏  Editar", variante="primario", ao_clicar=self._on_editar
        )
        self._btn_editar.pack(fill="x", padx=16, pady=(12, 6))

        self._btn_toggle = Botao(
            rodape, "🚫  Desativar", variante="perigo", ao_clicar=self._on_toggle
        )
        self._btn_toggle.pack(fill="x", padx=16, pady=(0, 16))

        self._btn_editar.configure(state="disabled")
        self._btn_toggle.configure(state="disabled")

    def exibir(self, material: Material) -> None:
        self._material = material
        self._titulo.configure(text=material.nome)
        self._subtitulo.configure(text=f"ID #{material.id}")

        descricao = material.descricao or "—"
        self._campos["unidade"].configure(text=material.unidade)
        self._campos["custo"].configure(text=f"R$ {material.preco_custo:,.2f}")
        self._campos["venda"].configure(text=f"R$ {material.preco_venda:,.2f}")
        self._campos["estoque"].configure(
            text=f"{material.estoque_atual:,.2f} {material.unidade}"
        )
        self._campos["minimo"].configure(
            text=f"{material.estoque_minimo:,.2f} {material.unidade}"
        )
        self._campos["local"].configure(text=material.localizacao or "—")
        self._campos["ativo"].configure(
            text="✅ Ativo" if material.ativo else "❌ Inativo",
            text_color=Tema.SUCESSO if material.ativo else Tema.PERIGO,
        )
        self._campos["descricao"].configure(text=descricao)

        self._btn_editar.configure(state="normal")
        self._btn_toggle.configure(
            state="normal",
            text="🚫  Desativar" if material.ativo else "✅  Reativar",
        )

    def limpar(self) -> None:
        self._material = None
        self._titulo.configure(text="Selecione\num item")
        self._subtitulo.configure(text="")
        for campo in self._campos.values():
            campo.configure(text="—", text_color=Tema.TEXTO_PRINCIPAL)
        self._btn_editar.configure(state="disabled")
        self._btn_toggle.configure(state="disabled", text="🚫  Desativar")

    def _on_editar(self) -> None:
        if self._material is not None:
            self._ao_editar(self._material)

    def _on_toggle(self) -> None:
        if self._material is not None:
            self._ao_toggle(self._material)


# ---------------------------------------------------------------------------
# Tela principal
# ---------------------------------------------------------------------------


class TelaMateriais(ctk.CTkToplevel):
    """
    Tela principal de materiais.

    Uso (a partir do menu):
        TelaMateriais(self, self._usuario).grab_set()
    """

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        usuario: Usuario | None = None,
    ) -> None:
        super().__init__(master)
        self._usuario = usuario
        self.title("FerroFlux — Materiais")
        self.minsize(900, 560)
        self.geometry("1100x660")
        self.resizable(True, True)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()

        self._materiais: list[Material] = []
        self._lista_filtrada: list[Material] = []

        # Frame raiz (CTkFrame) — evita passar CTkToplevel a componentes que
        # esperam CTkFrame
        self._raiz = ctk.CTkFrame(self, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._raiz.pack(fill="both", expand=True)
        self._raiz.grid_rowconfigure(1, weight=1)
        self._raiz.grid_columnconfigure(0, weight=1)

        self._construir_ui()
        self._carregar()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _centralizar(self) -> None:
        self.update_idletasks()
        w, h = 1100, 660
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _construir_ui(self) -> None:
        # ── Cabeçalho ──────────────────────────────────────────────────
        topo = ctk.CTkFrame(self._raiz, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        topo.columnconfigure(1, weight=1)

        Titulo(topo, "📦  Materiais").grid(row=0, column=0, sticky="w")

        # Busca centralizada
        busca_frame = ctk.CTkFrame(topo, fg_color="transparent")
        busca_frame.grid(row=0, column=1, sticky="ew", padx=24)
        busca_frame.columnconfigure(0, weight=1)

        self._campo_busca = CampoTexto(
            busca_frame, placeholder="🔍  Buscar por nome..."
        )
        self._campo_busca.grid(row=0, column=0, sticky="ew")
        self._campo_busca.bind("<KeyRelease>", lambda _: self._filtrar())

        self._chk_inativos = ctk.CTkCheckBox(
            busca_frame,
            text="Mostrar inativos",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            text_color=Tema.TEXTO_PRINCIPAL,
            command=self._carregar,
        )
        self._chk_inativos.grid(row=0, column=1, padx=(12, 0))

        # Botão novo
        Botao(
            topo,
            "+ Novo Material",
            variante="sucesso",
            ao_clicar=self._abrir_cadastro,
        ).grid(row=0, column=2, sticky="e")

        # ── Separador ──────────────────────────────────────────────────
        ctk.CTkFrame(
            self._raiz,
            height=1,
            fg_color=Tema.BORDA_CARD,
            corner_radius=0,
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(12, 0))

        # ── Corpo: tabela + painel ──────────────────────────────────────
        corpo = ctk.CTkFrame(self._raiz, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="nsew", padx=24, pady=12)
        self._raiz.grid_rowconfigure(2, weight=1)
        corpo.grid_rowconfigure(0, weight=1)
        corpo.grid_columnconfigure(0, weight=1)

        # Tabela
        self._tabela = _TabelaMateriais(corpo)
        self._tabela.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._tabela.ao_selecionar(self._ao_selecionar)

        # Painel lateral
        self._painel = _PainelDetalhe(
            corpo,
            ao_editar=self._abrir_edicao,
            ao_toggle=self._toggle_ativo,
        )
        self._painel.grid(row=0, column=1, sticky="nsew")

        # ── Barra de status ────────────────────────────────────────────
        self._barra = BarraStatus(self._raiz)
        self._barra.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar(self) -> None:
        apenas_ativos = not bool(self._chk_inativos.get())
        try:
            with obter_conexao() as conn:
                repo = MaterialRepo(conn)
                self._materiais = repo.listar_todos(apenas_ativos=apenas_ativos)
        except ConexaoError as e:
            self._barra.erro(str(e))
            return

        self._painel.limpar()
        self._filtrar()

    def _filtrar(self) -> None:
        termo = self._campo_busca.get().strip().lower()
        self._lista_filtrada = (
            [m for m in self._materiais if termo in m.nome.lower()]
            if termo
            else list(self._materiais)
        )
        self._tabela.popular(self._lista_filtrada)
        total = len(self._lista_filtrada)
        total_geral = len(self._materiais)
        if termo:
            self._barra.info(
                f'{total} resultado(s) para "{self._campo_busca.get().strip()}"'
                f"  (de {total_geral} total)"
            )
        else:
            self._barra.info(f"{total_geral} material(is) cadastrado(s).")

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _ao_selecionar(self, material: Material) -> None:
        self._painel.exibir(material)

    def _abrir_cadastro(self) -> None:
        _JanelaCadastroMaterial(
            self, material=None, ao_salvar=self._carregar
        ).grab_set()

    def _abrir_edicao(self, material: Material) -> None:
        _JanelaCadastroMaterial(
            self, material=material, ao_salvar=self._carregar
        ).grab_set()

    def _toggle_ativo(self, material: Material) -> None:
        id_produto = material.id
        if id_produto is None:
            self._barra.erro("Material sem ID — operação impossível.")
            return
        try:
            with obter_conexao() as conn:
                repo = MaterialRepo(conn)
                if material.ativo:
                    repo.desativar(id_produto)
                    self._barra.sucesso(f'"{material.nome}" desativado.')
                else:
                    repo.reativar(id_produto)
                    self._barra.sucesso(f'"{material.nome}" reativado.')
        except ConexaoError as e:
            self._barra.erro(str(e))
        self._carregar()


# ---------------------------------------------------------------------------
# Janela de cadastro / edição
# ---------------------------------------------------------------------------


class _JanelaCadastroMaterial(ctk.CTkToplevel):
    """Formulário para criar ou editar um material."""

    def __init__(
        self,
        master: ctk.CTkToplevel,
        material: Material | None,
        ao_salvar: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._material = material
        self._ao_salvar = ao_salvar
        self._editando = material is not None

        titulo = "Editar Material" if self._editando else "Novo Material"
        self.title(f"FerroFlux — {titulo}")
        self.geometry("520x700")
        self.minsize(480, 600)
        self.resizable(True, False)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()
        self._construir_ui()

        if self._editando and self._material is not None:
            self._preencher_campos(self._material)

    def _centralizar(self) -> None:
        self.update_idletasks()
        w, h = 520, 700
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        # Frame raiz para evitar passar CTkToplevel a CartaoFrame
        _frame_raiz = ctk.CTkFrame(self, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        _frame_raiz.pack(fill="both", expand=True)
        _frame_raiz.grid_rowconfigure(0, weight=1)
        _frame_raiz.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(_frame_raiz, fg_color=Tema.FUNDO_JANELA)
        scroll.grid(row=0, column=0, sticky="nsew")

        card = CartaoFrame(scroll)
        card.pack(fill="x", padx=20, pady=16)

        rotulo_titulo = "✏  Editar Material" if self._editando else "📦  Novo Material"
        Titulo(card, rotulo_titulo).pack(pady=(22, 2), padx=24, anchor="w")
        Subtitulo(card, "Preencha os dados do material abaixo.").pack(
            padx=24, anchor="w"
        )
        Separador(card).pack(fill="x", padx=24, pady=12)

        def campo(label: str, placeholder: str = "") -> CampoTexto:
            Rotulo(card, label).pack(anchor="w", padx=24, pady=(8, 2))
            c = CampoTexto(card, placeholder=placeholder)
            c.pack(fill="x", padx=24)
            return c

        self._f_nome = campo("Nome do material: *", "Ex: Chapa de Aço Carbono")
        self._f_codigo = campo("Código de barras:", "Opcional")
        self._f_descricao = campo("Descrição:", "Breve descrição do material")

        Rotulo(card, "Unidade de medida: *").pack(anchor="w", padx=24, pady=(8, 2))
        self._f_unidade = ComboSelecao(
            card,
            valores=["KG", "G", "UN", "M", "M²", "M³", "L", "ML", "PC", "CX", "TON"],
        )
        self._f_unidade.set("KG")
        self._f_unidade.pack(fill="x", padx=24)

        # Preços lado a lado
        fp = ctk.CTkFrame(card, fg_color="transparent")
        fp.pack(fill="x", padx=24, pady=(8, 0))
        fp.columnconfigure((0, 1), weight=1)
        Rotulo(fp, "Preço custo (R$): *").grid(row=0, column=0, sticky="w")
        Rotulo(fp, "Preço venda (R$): *").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._f_custo = CampoTexto(fp, placeholder="0,00")
        self._f_custo.grid(row=1, column=0, sticky="ew")
        self._f_venda = CampoTexto(fp, placeholder="0,00")
        self._f_venda.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        # Estoque lado a lado
        fe = ctk.CTkFrame(card, fg_color="transparent")
        fe.pack(fill="x", padx=24, pady=(8, 0))
        fe.columnconfigure((0, 1), weight=1)
        Rotulo(fe, "Estoque atual:").grid(row=0, column=0, sticky="w")
        Rotulo(fe, "Estoque mínimo:").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._f_estoque = CampoTexto(fe, placeholder="0")
        self._f_estoque.grid(row=1, column=0, sticky="ew")
        self._f_minimo = CampoTexto(fe, placeholder="0")
        self._f_minimo.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        self._f_localizacao = campo("Localização no estoque:", "Ex: Prateleira A3")

        Rotulo(card, "* Campos obrigatórios", secundario=True).pack(
            anchor="w", padx=24, pady=(10, 0)
        )
        Separador(card).pack(fill="x", padx=24, pady=12)

        self._barra = BarraStatus(card)
        self._barra.pack(fill="x", padx=24, pady=(0, 8))

        fb = ctk.CTkFrame(card, fg_color="transparent")
        fb.pack(fill="x", padx=24, pady=(0, 24))
        fb.columnconfigure((0, 1), weight=1)
        Botao(fb, "Cancelar", variante="neutro", ao_clicar=self.destroy).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        Botao(
            fb,
            "💾  Atualizar" if self._editando else "💾  Salvar",
            variante="sucesso",
            ao_clicar=self._salvar,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    # ------------------------------------------------------------------
    # Preenchimento
    # ------------------------------------------------------------------

    def _preencher_campos(self, m: Material) -> None:
        self._f_nome.insert(0, m.nome)
        self._f_codigo.insert(0, m.codigo_barras or "")
        self._f_descricao.insert(0, m.descricao or "")
        self._f_unidade.set(m.unidade)
        self._f_custo.insert(0, f"{m.preco_custo:.2f}")
        self._f_venda.insert(0, f"{m.preco_venda:.2f}")
        self._f_estoque.insert(0, f"{m.estoque_atual:.2f}")
        self._f_minimo.insert(0, f"{m.estoque_minimo:.2f}")
        self._f_localizacao.insert(0, m.localizacao or "")

    # ------------------------------------------------------------------
    # Validação e salvamento
    # ------------------------------------------------------------------

    @staticmethod
    def _ler_decimal(campo: CampoTexto, nome: str) -> float:
        texto = campo.get().strip().replace(",", ".")
        if not texto:
            return 0.0
        try:
            return float(texto)
        except ValueError as exc:
            raise ValueError(
                f'O campo "{nome}" deve ser um número válido. Valor informado: "{texto}"'
            ) from exc

    def _validar(self) -> Material | None:
        nome = self._f_nome.get().strip()
        if not nome:
            self._barra.erro("O nome do material é obrigatório.")
            return None
        if len(nome) > 255:
            self._barra.erro("Nome muito longo (máx. 255 caracteres).")
            return None

        codigo = self._f_codigo.get().strip() or None

        try:
            preco_custo = self._ler_decimal(self._f_custo, "Preço custo")
            preco_venda = self._ler_decimal(self._f_venda, "Preço venda")
            estoque = self._ler_decimal(self._f_estoque, "Estoque atual")
            est_minimo = self._ler_decimal(self._f_minimo, "Estoque mínimo")
        except ValueError as e:
            self._barra.erro(str(e))
            return None

        if preco_custo < 0 or preco_venda < 0:
            self._barra.erro("Preços não podem ser negativos.")
            return None

        id_original = self._material.id if self._material is not None else None

        return Material(
            id=id_original,
            nome=nome,
            codigo_barras=codigo,
            descricao=self._f_descricao.get().strip(),
            unidade=self._f_unidade.get(),
            preco_custo=preco_custo,
            preco_venda=preco_venda,
            estoque_atual=estoque,
            estoque_minimo=est_minimo,
            localizacao=self._f_localizacao.get().strip(),
            ativo=True,
        )

    def _salvar(self) -> None:
        material = self._validar()
        if material is None:
            return

        self._barra.info("Salvando...")
        self.update_idletasks()

        try:
            with obter_conexao() as conn:
                repo = MaterialRepo(conn)

                if material.codigo_barras is not None:
                    if repo.codigo_barras_existe(
                        material.codigo_barras, ignorar_id=material.id
                    ):
                        self._barra.erro(
                            "Código de barras já cadastrado para outro material."
                        )
                        return

                if self._editando:
                    repo.atualizar(material)
                    self._barra.sucesso("Material atualizado com sucesso!")
                else:
                    repo.inserir(material)
                    self._barra.sucesso("Material cadastrado com sucesso!")

        except ConexaoError as e:
            self._barra.erro(f"Erro de conexão: {e}")
            return
        except pyodbc.Error as e:
            self._barra.erro(f"Erro no banco de dados: {e}")
            return
        except ValueError as e:
            self._barra.erro(f"Dado inválido: {e}")
            return

        self._ao_salvar()
        self.after(800, self.destroy)


# ---------------------------------------------------------------------------
# Ponto de entrada para teste isolado
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from database.conexao import ConfigConexao, configurar

    configurar(
        ConfigConexao(
            servidor="localhost",
            porta=3306,
            usuario="root",
            senha="",
            banco="ferroflux",
        )
    )

    app = ctk.CTk()
    app.withdraw()

    tela = TelaMateriais(app)
    tela.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()
