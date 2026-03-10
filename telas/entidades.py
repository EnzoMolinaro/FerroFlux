"""
telas/clientes.py
-----------------
Tela de gerenciamento de clientes do FerroFlux.
Para fornecedores, basta criar telas/fornecedores.py com:

    from telas.clientes import _TelaEntidade

    class TelaFornecedores(_TelaEntidade):
        def __init__(self, master, usuario=None):
            super().__init__(master, usuario, modo="fornecedor")

Modos disponíveis:
    "cliente"    — filtra EhCliente=TRUE, título "Clientes"
    "fornecedor" — filtra EhFornecedor=TRUE, título "Fornecedores"
    "ambos"      — sem filtro de tipo
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from typing import Callable, Literal

import customtkinter as ctk
import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError, obter_conexao
from repositories.entidade import Contato, Endereco, Entidade, EntidadeRepo
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

ModoTela = Literal["cliente", "fornecedor", "ambos"]

# ---------------------------------------------------------------------------
# Estilo da tabela
# ---------------------------------------------------------------------------


def _aplicar_estilo_tabela() -> None:
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Entidade.Treeview",
        background=Tema.FUNDO_INPUT,
        foreground=Tema.TEXTO_PRINCIPAL,
        fieldbackground=Tema.FUNDO_INPUT,
        rowheight=36,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_CORPO),
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Entidade.Treeview.Heading",
        background=Tema.FUNDO_JANELA,
        foreground=Tema.TEXTO_SECUNDARIO,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_LABEL, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Entidade.Treeview",
        background=[("selected", Tema.PRIMARIO)],
        foreground=[("selected", "#ffffff")],
    )
    style.map("Entidade.Treeview.Heading", background=[("active", Tema.NEUTRO)])
    style.layout(
        "Entidade.Treeview",
        [
            ("Treeview.treearea", {"sticky": "nswe"}),
        ],
    )


# ---------------------------------------------------------------------------
# Colunas da tabela
# ---------------------------------------------------------------------------

AnchorTabela = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]

_COLUNAS: list[tuple[str, str, int, AnchorTabela]] = [
    ("nome", "Nome", 240, "w"),
    ("documento", "CPF / CNPJ", 140, "w"),
    ("tipo", "Tipo", 50, "center"),
    ("contato", "Contato", 180, "w"),
    ("cidade", "Cidade / UF", 150, "w"),
    ("status", "Status", 80, "center"),
]


# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------


class _TabelaEntidades(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkFrame, **kwargs) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        super().__init__(master, **kwargs)
        _aplicar_estilo_tabela()
        self._ordem: dict[str, bool] = {}
        self._callback: Callable[[Entidade], None] | None = None
        self._entidades: list[Entidade] = []
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
            style="Entidade.Treeview",
            selectmode="browse",
            yscrollcommand=sb_y.set,
            xscrollcommand=sb_x.set,
        )
        for col_id, cab, larg, anchor in _COLUNAS:
            self._tree.heading(
                col_id, text=cab, command=lambda c=col_id: self._ordenar(c)
            )
            self._tree.column(col_id, width=larg, minwidth=larg, anchor=anchor)

        sb_y.config(command=self._tree.yview)
        sb_x.config(command=self._tree.xview)

        self._tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        sb_y.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=8)
        sb_x.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 4))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tree.tag_configure("par", background=Tema.FUNDO_INPUT)
        self._tree.tag_configure("impar", background=Tema.FUNDO_CARD)
        self._tree.tag_configure("inativo", foreground=Tema.TEXTO_PLACEHOLDER)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def popular(self, entidades: list[Entidade]) -> None:
        self._entidades = entidades
        self._tree.delete(*self._tree.get_children())
        for i, e in enumerate(entidades):
            tag_linha = "par" if i % 2 == 0 else "impar"
            tags: list[str] = [tag_linha]
            if not e.ativo:
                tags.append("inativo")

            # Cidade do endereço principal
            end = e.endereco_principal
            cidade_uf = f"{end.cidade} / {end.estado}" if end else "—"

            self._tree.insert(
                "",
                "end",
                iid=str(i),
                tags=tags,
                values=(
                    e.nome,
                    e.documento,
                    e.tipo_pessoa,
                    e.contato_principal,
                    cidade_uf,
                    "✅ Ativo" if e.ativo else "❌ Inativo",
                ),
            )

    def ao_selecionar(self, callback: Callable[[Entidade], None]) -> None:
        self._callback = callback

    def _on_select(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self._entidades) and self._callback:
            self._callback(self._entidades[idx])

    def _ordenar(self, coluna: str) -> None:
        crescente = not self._ordem.get(coluna, False)
        self._ordem[coluna] = crescente
        mapa = {
            "nome": "nome",
            "documento": "documento",
            "tipo": "tipo_pessoa",
            "status": "ativo",
        }
        attr = mapa.get(coluna, "nome")
        self._entidades.sort(
            key=lambda e: str(getattr(e, attr, "")),
            reverse=not crescente,
        )
        self.popular(self._entidades)
        for c, cab, *_ in _COLUNAS:
            seta = (" ↑" if crescente else " ↓") if c == coluna else ""
            self._tree.heading(c, text=cab + seta)


# ---------------------------------------------------------------------------
# Painel lateral de detalhes
# ---------------------------------------------------------------------------


class _PainelDetalhe(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkFrame,
        ao_editar: Callable[[Entidade], None],
        ao_toggle: Callable[[Entidade], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=Tema.FUNDO_CARD,
            corner_radius=16,
            border_width=1,
            border_color=Tema.BORDA_CARD,
            width=270,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._ao_editar = ao_editar
        self._ao_toggle = ao_toggle
        self._entidade: Entidade | None = None
        self._construir()

    def _construir(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.pack(fill="both", expand=True)

        self._titulo = ctk.CTkLabel(
            self._scroll,
            text="Selecione\num item",
            font=Tema.fonte_titulo(Tema.TAMANHO_H2),
            text_color=Tema.TEXTO_TITULO,
            fg_color="transparent",
            justify="left",
            anchor="w",
            wraplength=230,
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

        ctk.CTkFrame(
            self._scroll, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0
        ).pack(fill="x", padx=16, pady=(0, 12))

        self._campos: dict[str, ctk.CTkLabel] = {}
        for label, chave in [
            ("Documento", "documento"),
            ("Tipo", "tipo"),
            ("Papéis", "papeis"),
            ("Status", "status"),
            ("Contatos", "contatos"),
            ("Endereço", "endereco"),
            ("Observações", "obs"),
        ]:
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
                wraplength=230,
                justify="left",
            )
            val.pack(anchor="w")
            self._campos[chave] = val

        # Botões fixos no fundo
        rodape = ctk.CTkFrame(self, fg_color=Tema.FUNDO_CARD, corner_radius=0)
        rodape.pack(fill="x", side="bottom")
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

    def exibir(self, entidade: Entidade) -> None:
        self._entidade = entidade
        self._titulo.configure(text=entidade.nome)
        self._subtitulo.configure(text=f"ID #{entidade.id}")

        papeis: list[str] = []
        if entidade.eh_cliente:
            papeis.append("Cliente")
        if entidade.eh_fornecedor:
            papeis.append("Fornecedor")

        # Contatos formatados
        contatos_txt = (
            "\n".join(
                f"{'★ ' if c.principal else ''}{c.tipo}: {c.valor}"
                for c in entidade.contatos
            )
            or "—"
        )

        # Endereço principal
        end = entidade.endereco_principal
        if end:
            num = f", {end.numero}" if end.numero else ""
            bairro = f"\n{end.bairro}" if end.bairro else ""
            cidade = f"\n{end.cidade} - {end.estado}" if end.cidade else ""
            endereco_txt = f"{end.logradouro}{num}{bairro}{cidade}"
        else:
            endereco_txt = "—"

        self._campos["documento"].configure(text=entidade.documento)
        self._campos["tipo"].configure(text=entidade.tipo_pessoa)
        self._campos["papeis"].configure(text=" / ".join(papeis) or "—")
        self._campos["status"].configure(
            text="✅ Ativo" if entidade.ativo else "❌ Inativo",
            text_color=Tema.SUCESSO if entidade.ativo else Tema.PERIGO,
        )
        self._campos["contatos"].configure(text=contatos_txt)
        self._campos["endereco"].configure(text=endereco_txt)
        self._campos["obs"].configure(
            text=(
                (entidade.observacoes[:80] + "…")
                if len(entidade.observacoes) > 80
                else (entidade.observacoes or "—")
            )
        )

        self._btn_editar.configure(state="normal")
        self._btn_toggle.configure(
            state="normal",
            text="🚫  Desativar" if entidade.ativo else "✅  Reativar",
        )

    def limpar(self) -> None:
        self._entidade = None
        self._titulo.configure(text="Selecione\num item")
        self._subtitulo.configure(text="")
        for campo in self._campos.values():
            campo.configure(text="—", text_color=Tema.TEXTO_PRINCIPAL)
        self._btn_editar.configure(state="disabled")
        self._btn_toggle.configure(state="disabled", text="🚫  Desativar")

    def _on_editar(self) -> None:
        if self._entidade is not None:
            self._ao_editar(self._entidade)

    def _on_toggle(self) -> None:
        if self._entidade is not None:
            self._ao_toggle(self._entidade)


# ---------------------------------------------------------------------------
# Tela base — usada por TelaClientes e TelaFornecedores
# ---------------------------------------------------------------------------


class _TelaEntidade(ctk.CTkToplevel):
    """
    Tela genérica de gestão de entidades.
    Subclasse com modo="cliente" ou modo="fornecedor".
    """

    _TITULOS: dict[str, str] = {
        "cliente": "👥  Clientes",
        "fornecedor": "🏭  Fornecedores",
        "ambos": "👤  Entidades",
    }

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        usuario: Usuario | None = None,
        modo: ModoTela = "cliente",
    ) -> None:
        super().__init__(master)
        self._usuario = usuario
        self._modo: ModoTela = modo
        self._titulo_tela = self._TITULOS.get(modo, "Entidades")

        self.title(f"FerroFlux — {self._titulo_tela.lstrip('👥🏭👤 ')}")
        self.minsize(960, 580)
        self.geometry("1140x680")
        self.resizable(True, True)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()

        self._entidades: list[Entidade] = []
        self._lista_filtrada: list[Entidade] = []

        self._raiz = ctk.CTkFrame(self, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._raiz.pack(fill="both", expand=True)
        self._raiz.grid_rowconfigure(2, weight=1)
        self._raiz.grid_columnconfigure(0, weight=1)

        self._construir_ui()
        self._carregar()

    def _centralizar(self) -> None:
        self.update_idletasks()
        w, h = 1140, 680
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _construir_ui(self) -> None:
        # ── Cabeçalho ──────────────────────────────────────────────────
        topo = ctk.CTkFrame(self._raiz, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        topo.columnconfigure(1, weight=1)

        Titulo(topo, self._titulo_tela).grid(row=0, column=0, sticky="w")

        busca_frame = ctk.CTkFrame(topo, fg_color="transparent")
        busca_frame.grid(row=0, column=1, sticky="ew", padx=24)
        busca_frame.columnconfigure(0, weight=1)

        self._campo_busca = CampoTexto(
            busca_frame, placeholder="🔍  Buscar por nome ou documento..."
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

        Botao(
            topo,
            "+ Novo",
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

        # ── Corpo ──────────────────────────────────────────────────────
        corpo = ctk.CTkFrame(self._raiz, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="nsew", padx=24, pady=12)
        corpo.grid_rowconfigure(0, weight=1)
        corpo.grid_columnconfigure(0, weight=1)

        self._tabela = _TabelaEntidades(corpo)
        self._tabela.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._tabela.ao_selecionar(self._ao_selecionar)

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
                repo = EntidadeRepo(conn)
                self._entidades = repo.listar(
                    apenas_clientes=(self._modo == "cliente"),
                    apenas_fornecedores=(self._modo == "fornecedor"),
                    apenas_ativos=apenas_ativos,
                )
                # Carrega contatos e endereços para exibição na tabela
                for ent in self._entidades:
                    if ent.id is not None:
                        ent.contatos = repo.listar_contatos(ent.id)
                        ent.enderecos = repo.listar_enderecos(ent.id)
        except ConexaoError as e:
            self._barra.erro(str(e))
            return

        self._painel.limpar()
        self._filtrar()

    def _filtrar(self) -> None:
        termo = self._campo_busca.get().strip().lower()
        self._lista_filtrada = (
            [
                e
                for e in self._entidades
                if termo in e.nome.lower() or termo in (e.documento or "").lower()
            ]
            if termo
            else list(self._entidades)
        )
        self._tabela.popular(self._lista_filtrada)
        total = len(self._lista_filtrada)
        total_geral = len(self._entidades)
        if termo:
            self._barra.info(
                f'{total} resultado(s) para "{self._campo_busca.get().strip()}"'
                f"  (de {total_geral} total)"
            )
        else:
            self._barra.info(f"{total_geral} registro(s) encontrado(s).")

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _ao_selecionar(self, entidade: Entidade) -> None:
        self._painel.exibir(entidade)

    def _abrir_cadastro(self) -> None:
        _JanelaCadastroEntidade(
            self,
            entidade=None,
            modo=self._modo,
            ao_salvar=self._carregar,
        ).grab_set()

    def _abrir_edicao(self, entidade: Entidade) -> None:
        # Recarrega com detalhes completos antes de abrir o form
        try:
            with obter_conexao() as conn:
                id_ent = entidade.id
                if id_ent is None:
                    self._barra.erro("Entidade sem ID.")
                    return
                completa = EntidadeRepo(conn).buscar_por_id(
                    id_ent,
                    carregar_detalhes=True,
                )
        except ConexaoError as e:
            self._barra.erro(str(e))
            return
        _JanelaCadastroEntidade(
            self,
            entidade=completa,
            modo=self._modo,
            ao_salvar=self._carregar,
        ).grab_set()

    def _toggle_ativo(self, entidade: Entidade) -> None:
        id_entidade = entidade.id
        if id_entidade is None:
            self._barra.erro("Entidade sem ID — operação impossível.")
            return
        try:
            with obter_conexao() as conn:
                repo = EntidadeRepo(conn)
                if entidade.ativo:
                    repo.desativar(id_entidade)
                    self._barra.sucesso(f'"{entidade.nome}" desativado.')
                else:
                    repo.reativar(id_entidade)
                    self._barra.sucesso(f'"{entidade.nome}" reativado.')
        except ConexaoError as e:
            self._barra.erro(str(e))
        self._carregar()


# ---------------------------------------------------------------------------
# Telas públicas
# ---------------------------------------------------------------------------


class TelaClientes(_TelaEntidade):
    """Tela de gestão de clientes. Registrada no menu como 'clientes'."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        usuario: Usuario | None = None,
    ) -> None:
        super().__init__(master, usuario, modo="cliente")


class TelaFornecedores(_TelaEntidade):
    """Tela de gestão de fornecedores. Registrada no menu como 'fornecedores'."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        usuario: Usuario | None = None,
    ) -> None:
        super().__init__(master, usuario, modo="fornecedor")


# ---------------------------------------------------------------------------
# Formulário de cadastro / edição
# ---------------------------------------------------------------------------


class _JanelaCadastroEntidade(ctk.CTkToplevel):
    """
    Formulário de cadastro/edição com abas:
        Aba 1 — Dados gerais (nome, documento, tipo)
        Aba 2 — Contatos
        Aba 3 — Endereço
    """

    def __init__(
        self,
        master: ctk.CTkToplevel,
        entidade: Entidade | None,
        modo: ModoTela,
        ao_salvar: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._entidade = entidade
        self._modo = modo
        self._ao_salvar = ao_salvar
        self._editando = entidade is not None

        titulo = "Editar" if self._editando else "Novo"
        tipo = {"cliente": "Cliente", "fornecedor": "Fornecedor", "ambos": "Entidade"}
        self.title(f"FerroFlux — {titulo} {tipo.get(modo, 'Entidade')}")
        self.geometry("580x720")
        self.minsize(520, 620)
        self.resizable(True, False)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()
        self._construir_ui()

        if self._editando and self._entidade is not None:
            self._preencher(self._entidade)

    def _centralizar(self) -> None:
        self.update_idletasks()
        w, h = 580, 720
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        _frame_raiz = ctk.CTkFrame(self, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        _frame_raiz.pack(fill="both", expand=True)
        _frame_raiz.grid_rowconfigure(0, weight=1)
        _frame_raiz.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(_frame_raiz, fg_color=Tema.FUNDO_JANELA)
        scroll.grid(row=0, column=0, sticky="nsew")

        card = CartaoFrame(scroll)
        card.pack(fill="x", padx=20, pady=16)

        tipo_str = {
            "cliente": "Cliente",
            "fornecedor": "Fornecedor",
            "ambos": "Entidade",
        }
        icone = {"cliente": "👥", "fornecedor": "🏭", "ambos": "👤"}
        prefixo = (
            "✏  Editar" if self._editando else f"{icone.get(self._modo, '👤')}  Novo"
        )
        Titulo(card, f"{prefixo} {tipo_str.get(self._modo, 'Entidade')}").pack(
            pady=(22, 2), padx=24, anchor="w"
        )
        Subtitulo(card, "Preencha os dados abaixo.").pack(padx=24, anchor="w")
        Separador(card).pack(fill="x", padx=24, pady=12)

        def campo(
            label: str, placeholder: str = "", parent: ctk.CTkFrame | None = None
        ) -> CampoTexto:
            p = parent or card
            Rotulo(p, label).pack(anchor="w", padx=24, pady=(8, 2))
            c = CampoTexto(p, placeholder=placeholder)
            c.pack(fill="x", padx=24)
            return c

        # ── Dados gerais ───────────────────────────────────────────
        self._f_nome = campo(
            "Nome / Razão Social: *", "Ex: João Silva ou Empresa Ltda."
        )

        # CPF / CNPJ lado a lado
        fdoc = ctk.CTkFrame(card, fg_color="transparent")
        fdoc.pack(fill="x", padx=24, pady=(8, 0))
        fdoc.columnconfigure((0, 1), weight=1)
        Rotulo(fdoc, "CPF:").grid(row=0, column=0, sticky="w")
        Rotulo(fdoc, "CNPJ:").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._f_cpf = CampoTexto(fdoc, placeholder="000.000.000-00")
        self._f_cpf.grid(row=1, column=0, sticky="ew")
        self._f_cnpj = CampoTexto(fdoc, placeholder="00.000.000/0000-00")
        self._f_cnpj.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        # Papéis (checkboxes)
        Rotulo(card, "Papel no sistema: *").pack(anchor="w", padx=24, pady=(12, 4))
        fpapeis = ctk.CTkFrame(card, fg_color="transparent")
        fpapeis.pack(anchor="w", padx=24)

        self._chk_cliente = ctk.CTkCheckBox(
            fpapeis,
            text="Cliente",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            text_color=Tema.TEXTO_PRINCIPAL,
        )
        self._chk_cliente.pack(side="left", padx=(0, 16))
        self._chk_fornecedor = ctk.CTkCheckBox(
            fpapeis,
            text="Fornecedor",
            font=Tema.fonte(Tema.TAMANHO_LABEL),
            text_color=Tema.TEXTO_PRINCIPAL,
        )
        self._chk_fornecedor.pack(side="left")

        # Pré-marca conforme o modo
        if self._modo == "cliente":
            self._chk_cliente.select()
        elif self._modo == "fornecedor":
            self._chk_fornecedor.select()

        self._f_obs = campo("Observações:", "Informações adicionais...")

        Separador(card).pack(fill="x", padx=24, pady=12)

        # ── Contato principal ──────────────────────────────────────
        Rotulo(card, "Contato principal:").pack(anchor="w", padx=24, pady=(0, 4))
        fcontato = ctk.CTkFrame(card, fg_color="transparent")
        fcontato.pack(fill="x", padx=24)
        fcontato.columnconfigure(1, weight=1)

        Rotulo(fcontato, "Tipo:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._f_contato_tipo = ComboSelecao(
            fcontato,
            valores=["CELULAR", "WHATSAPP", "TELEFONE", "EMAIL"],
        )
        self._f_contato_tipo.set("CELULAR")
        self._f_contato_tipo.grid(row=0, column=1, sticky="ew")

        Rotulo(fcontato, "Valor:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0)
        )
        self._f_contato_valor = CampoTexto(fcontato, placeholder="(11) 91234-5678")
        self._f_contato_valor.grid(row=1, column=1, sticky="ew", pady=(6, 0))

        Separador(card).pack(fill="x", padx=24, pady=12)

        # ── Endereço ───────────────────────────────────────────────
        Rotulo(card, "Endereço:").pack(anchor="w", padx=24, pady=(0, 4))

        self._f_logradouro = campo("Logradouro:", "Rua, Av., Travessa...")
        self._f_numero = campo("Número:", "S/N")

        fcomp_cep = ctk.CTkFrame(card, fg_color="transparent")
        fcomp_cep.pack(fill="x", padx=24, pady=(8, 0))
        fcomp_cep.columnconfigure((0, 1), weight=1)
        Rotulo(fcomp_cep, "Complemento:").grid(row=0, column=0, sticky="w")
        Rotulo(fcomp_cep, "CEP:").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._f_complemento = CampoTexto(fcomp_cep, placeholder="Apto, Sala...")
        self._f_complemento.grid(row=1, column=0, sticky="ew")
        self._f_cep = CampoTexto(fcomp_cep, placeholder="00000-000")
        self._f_cep.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        self._f_bairro = campo("Bairro:", "Nome do bairro")

        fcid_uf = ctk.CTkFrame(card, fg_color="transparent")
        fcid_uf.pack(fill="x", padx=24, pady=(8, 0))
        fcid_uf.columnconfigure(0, weight=3)
        fcid_uf.columnconfigure(1, weight=1)
        Rotulo(fcid_uf, "Cidade:").grid(row=0, column=0, sticky="w")
        Rotulo(fcid_uf, "UF:").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._f_cidade = CampoTexto(fcid_uf, placeholder="São Paulo")
        self._f_cidade.grid(row=1, column=0, sticky="ew")
        self._f_uf = CampoTexto(fcid_uf, placeholder="SP")
        self._f_uf.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        Rotulo(card, "* Campos obrigatórios", secundario=True).pack(
            anchor="w", padx=24, pady=(12, 0)
        )
        Separador(card).pack(fill="x", padx=24, pady=12)

        # ── Barra + botões ──────────────────────────────────────────
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

    def _preencher(self, e: Entidade) -> None:
        self._f_nome.insert(0, e.nome)
        self._f_cpf.insert(0, e.cpf or "")
        self._f_cnpj.insert(0, e.cnpj or "")
        self._f_obs.insert(0, e.observacoes or "")

        if e.eh_cliente:
            self._chk_cliente.select()
        if e.eh_fornecedor:
            self._chk_fornecedor.select()

        # Contato principal
        contato_preenchido = False
        for c in e.contatos:
            if c.principal:
                self._f_contato_tipo.set(c.tipo)
                self._f_contato_valor.insert(0, c.valor)
                contato_preenchido = True
                break
        if not contato_preenchido and e.contatos:
            self._f_contato_tipo.set(e.contatos[0].tipo)
            self._f_contato_valor.insert(0, e.contatos[0].valor)

        # Endereço principal
        end = e.endereco_principal
        if end:
            self._f_logradouro.insert(0, end.logradouro)
            self._f_numero.insert(0, end.numero)
            self._f_complemento.insert(0, end.complemento)
            self._f_cep.insert(0, end.cep)
            self._f_bairro.insert(0, end.bairro)
            self._f_cidade.insert(0, end.cidade)
            self._f_uf.insert(0, end.estado)

    # ------------------------------------------------------------------
    # Validação e salvamento
    # ------------------------------------------------------------------

    def _validar(self) -> Entidade | None:
        nome = self._f_nome.get().strip()
        if not nome:
            self._barra.erro("O nome é obrigatório.")
            return None

        cpf = self._f_cpf.get().strip() or None
        cnpj = self._f_cnpj.get().strip() or None
        if not cpf and not cnpj:
            self._barra.erro("Informe CPF ou CNPJ.")
            return None

        eh_cliente = bool(self._chk_cliente.get())
        eh_fornecedor = bool(self._chk_fornecedor.get())
        if not eh_cliente and not eh_fornecedor:
            self._barra.erro("Marque ao menos um papel: Cliente ou Fornecedor.")
            return None

        # Contato
        contatos: list[Contato] = []
        valor_contato = self._f_contato_valor.get().strip()
        if valor_contato:
            contatos.append(
                Contato(
                    tipo=self._f_contato_tipo.get(),
                    valor=valor_contato,
                    principal=True,
                )
            )

        # Endereço
        enderecos: list[Endereco] = []
        logradouro = self._f_logradouro.get().strip()
        if logradouro:
            cidade = self._f_cidade.get().strip()
            uf = self._f_uf.get().strip()
            if not cidade or not uf:
                self._barra.erro("Informe cidade e UF para o endereço.")
                return None
            # Preserva IDs em modo edição
            end_orig = (
                self._entidade.endereco_principal
                if self._entidade is not None
                else None
            )
            enderecos.append(
                Endereco(
                    logradouro=logradouro,
                    numero=self._f_numero.get().strip(),
                    complemento=self._f_complemento.get().strip(),
                    cep=self._f_cep.get().strip(),
                    bairro=self._f_bairro.get().strip(),
                    cidade=cidade,
                    estado=uf,
                    tipo="COMERCIAL",
                    principal=True,
                    id_endereco=end_orig.id_endereco if end_orig else None,
                    id_bairro=end_orig.id_bairro if end_orig else None,
                    id_cidade=end_orig.id_cidade if end_orig else None,
                )
            )

        id_original = self._entidade.id if self._entidade is not None else None

        return Entidade(
            id=id_original,
            nome=nome,
            cpf=cpf,
            cnpj=cnpj,
            eh_cliente=eh_cliente,
            eh_fornecedor=eh_fornecedor,
            ativo=True,
            observacoes=self._f_obs.get().strip(),
            contatos=contatos,
            enderecos=enderecos,
        )

    def _salvar(self) -> None:
        entidade = self._validar()
        if entidade is None:
            return

        self._barra.info("Salvando...")
        self.update_idletasks()

        try:
            with obter_conexao() as conn:
                repo = EntidadeRepo(conn)

                if repo.documento_existe(entidade.cpf, entidade.cnpj, entidade.id):
                    self._barra.erro("CPF ou CNPJ já cadastrado para outra entidade.")
                    return

                if self._editando:
                    repo.atualizar(entidade)
                    self._barra.sucesso("Registro atualizado com sucesso!")
                else:
                    repo.inserir(entidade)
                    self._barra.sucesso("Registro cadastrado com sucesso!")

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
    tela = TelaClientes(app)
    tela.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()
