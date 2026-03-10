"""
telas/funcionarios.py
---------------------
Tela de gerenciamento de funcionários do FerroFlux.
Acessível apenas para usuários com perfil ADM.
Embarcada no menu como CTkFrame (single-window navigation).
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from typing import Callable, Literal, cast

import customtkinter as ctk
import pyodbc  # type: ignore[import-untyped]

from database.conexao import ConexaoError
from repositories.usuario_repo import (
    Usuario,
    atualizar,
    buscar_por_id,
    cadastrar,
    desativar,
    listar,
    login_existe,
    reativar,
    redefinir_senha,
)
from telas.componentes import (
    BarraStatus,
    Botao,
    CampoSenha,
    CampoTexto,
    CartaoFrame,
    ComboSelecao,
    Rotulo,
    Separador,
    Subtitulo,
    Tema,
    Titulo,
)
from utils.seguranca import hash_senha, login_valido, senha_valida


def _aplicar_estilo_tabela() -> None:
    """Aplica o estilo visual customizado à Treeview de funcionários."""
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Func.Treeview",
        background=Tema.FUNDO_INPUT,
        foreground=Tema.TEXTO_PRINCIPAL,
        fieldbackground=Tema.FUNDO_INPUT,
        rowheight=36,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_CORPO),
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Func.Treeview.Heading",
        background=Tema.FUNDO_JANELA,
        foreground=Tema.TEXTO_SECUNDARIO,
        font=(Tema.FAMILIA_FB, Tema.TAMANHO_LABEL, "bold"),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Func.Treeview",
        background=[("selected", Tema.PRIMARIO)],
        foreground=[("selected", "#ffffff")],
    )
    style.map("Func.Treeview.Heading", background=[("active", Tema.NEUTRO)])
    style.layout("Func.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


_COLUNAS: list[tuple[str, str, int, Literal["w", "center"]]] = [
    ("nome", "Nome completo", 260, "w"),
    ("login", "Login", 160, "w"),
    ("perfil", "Perfil", 100, "center"),
    ("status", "Status", 90, "center"),
]


class _TabelaFuncionarios(ctk.CTkFrame):
    """Frame com Treeview para listagem de funcionários."""

    def __init__(self, master: ctk.CTkFrame, **kwargs) -> None:  # type: ignore[type-arg]
        kwargs.setdefault("fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        super().__init__(master, **kwargs)
        _aplicar_estilo_tabela()
        self._ordem: dict[str, bool] = {}
        self._callback: Callable[[Usuario], None] | None = None
        self._usuarios: list[Usuario] = []
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
            style="Func.Treeview",
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

    def popular(self, usuarios: list[Usuario]) -> None:
        """Preenche a tabela com a lista de usuários fornecida."""
        self._usuarios = usuarios
        self._tree.delete(*self._tree.get_children())
        for i, u in enumerate(usuarios):
            tags: list[str] = ["par" if i % 2 == 0 else "impar"]
            if not u.ativo:
                tags.append("inativo")
            self._tree.insert(
                "",
                "end",
                iid=str(i),
                tags=tags,
                values=(
                    u.nome_completo,
                    u.login,
                    u.perfil.capitalize(),
                    "✅ Ativo" if u.ativo else "❌ Inativo",
                ),
            )

    def ao_selecionar(self, callback: Callable[[Usuario], None]) -> None:
        """Registra o callback chamado ao selecionar uma linha."""
        self._callback = callback

    def _on_select(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self._usuarios) and self._callback:
            self._callback(self._usuarios[idx])

    def _ordenar(self, coluna: str) -> None:
        """Ordena a tabela pela coluna clicada, alternando asc/desc."""
        crescente = not self._ordem.get(coluna, False)
        self._ordem[coluna] = crescente
        mapa = {
            "nome": "nome_completo",
            "login": "login",
            "perfil": "perfil",
            "status": "ativo",
        }
        attr = mapa.get(coluna, "nome_completo")
        self._usuarios.sort(
            key=lambda u: str(getattr(u, attr, "")), reverse=not crescente
        )
        self.popular(self._usuarios)
        for c, cab, *_ in _COLUNAS:
            seta = (" ↑" if crescente else " ↓") if c == coluna else ""
            self._tree.heading(c, text=cab + seta)


class _PainelDetalhe(ctk.CTkFrame):
    """Painel lateral com detalhes e ações do funcionário selecionado."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        ao_editar: Callable[[Usuario], None],
        ao_toggle: Callable[[Usuario], None],
        ao_redefinir_senha: Callable[[Usuario], None],
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
        self._ao_redefinir_senha = ao_redefinir_senha
        self._usuario: Usuario | None = None
        self._campos: dict[str, ctk.CTkLabel] = {}
        self._btn_editar: ctk.CTkButton
        self._btn_senha: ctk.CTkButton
        self._btn_toggle: ctk.CTkButton
        self._construir()

    def _construir(self) -> None:
        """Monta os widgets do painel de detalhe."""
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        self._titulo = ctk.CTkLabel(
            scroll,
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
            scroll,
            text="",
            font=Tema.fonte(Tema.TAMANHO_PEQUENO),
            text_color=Tema.TEXTO_SECUNDARIO,
            fg_color="transparent",
            anchor="w",
        )
        self._subtitulo.pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkFrame(scroll, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).pack(
            fill="x", padx=16, pady=(0, 12)
        )

        for label, chave in [
            ("Login", "login"),
            ("Perfil", "perfil"),
            ("Status", "status"),
        ]:
            bloco = ctk.CTkFrame(scroll, fg_color="transparent")
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
                wraplength=230,
                justify="left",
            )
            val.pack(anchor="w")
            self._campos[chave] = val

        rodape = ctk.CTkFrame(self, fg_color=Tema.FUNDO_CARD, corner_radius=0)
        rodape.pack(fill="x", side="bottom")
        ctk.CTkFrame(rodape, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).pack(
            fill="x"
        )

        self._btn_editar = Botao(
            rodape, "✏  Editar", variante="primario", ao_clicar=self._on_editar
        )
        self._btn_editar.pack(fill="x", padx=16, pady=(12, 6))

        self._btn_senha = Botao(
            rodape,
            "🔑  Redefinir Senha",
            variante="aviso",
            ao_clicar=self._on_senha,
        )
        self._btn_senha.pack(fill="x", padx=16, pady=(0, 6))

        self._btn_toggle = Botao(
            rodape, "🚫  Desativar", variante="perigo", ao_clicar=self._on_toggle
        )
        self._btn_toggle.pack(fill="x", padx=16, pady=(0, 16))

        for btn in (self._btn_editar, self._btn_senha, self._btn_toggle):
            btn.configure(state="disabled")

    def exibir(self, usuario: Usuario) -> None:
        """Exibe os dados do funcionário no painel lateral."""
        self._usuario = usuario
        self._titulo.configure(text=usuario.nome_completo)
        self._subtitulo.configure(text=f"ID #{usuario.id}")
        self._campos["login"].configure(text=usuario.login)
        self._campos["perfil"].configure(text=usuario.perfil.capitalize())
        self._campos["status"].configure(
            text="✅ Ativo" if usuario.ativo else "❌ Inativo",
            text_color=Tema.SUCESSO if usuario.ativo else Tema.PERIGO,
        )
        self._btn_editar.configure(state="normal")
        self._btn_senha.configure(state="normal")
        self._btn_toggle.configure(
            state="normal",
            text="🚫  Desativar" if usuario.ativo else "✅  Reativar",
        )

    def limpar(self) -> None:
        """Reseta o painel para o estado inicial (sem funcionário selecionado)."""
        self._usuario = None
        self._titulo.configure(text="Selecione\num item")
        self._subtitulo.configure(text="")
        for campo in self._campos.values():
            campo.configure(text="—", text_color=Tema.TEXTO_PRINCIPAL)
        for btn in (self._btn_editar, self._btn_senha, self._btn_toggle):
            btn.configure(state="disabled")
        self._btn_toggle.configure(text="🚫  Desativar")

    def _on_editar(self) -> None:
        """Aciona o callback de edição se houver usuário selecionado."""
        if self._usuario:
            self._ao_editar(self._usuario)

    def _on_toggle(self) -> None:
        """Aciona o callback de ativar/desativar se houver usuário selecionado."""
        if self._usuario:
            self._ao_toggle(self._usuario)

    def _on_senha(self) -> None:
        """Aciona o callback de redefinição de senha se houver usuário selecionado."""
        if self._usuario:
            self._ao_redefinir_senha(self._usuario)


# ---------------------------------------------------------------------------
# Tela principal — CTkFrame (embedded)
# ---------------------------------------------------------------------------


class TelaFuncionarios(ctk.CTkFrame):
    """Tela de gerenciamento de funcionários. Embarcada no menu principal."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        usuario: Usuario | None = None,
    ) -> None:
        super().__init__(master, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        self._usuario_logado = usuario
        self._funcionarios: list[Usuario] = []
        self._lista_filtrada: list[Usuario] = []

        self._campo_busca: CampoTexto
        self._chk_inativos: ctk.CTkCheckBox
        self._tabela: _TabelaFuncionarios
        self._painel: _PainelDetalhe
        self._barra: BarraStatus

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._construir_ui()
        self._carregar()

    def _construir_ui(self) -> None:
        """Monta a interface da tela de funcionários."""
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        topo.columnconfigure(1, weight=1)

        Titulo(topo, "👤  Funcionários").grid(row=0, column=0, sticky="w")

        busca_frame = ctk.CTkFrame(topo, fg_color="transparent")
        busca_frame.grid(row=0, column=1, sticky="ew", padx=24)
        busca_frame.columnconfigure(0, weight=1)

        self._campo_busca = CampoTexto(
            busca_frame, placeholder="🔍  Buscar por nome ou login..."
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

        Botao(topo, "+ Novo", variante="sucesso", ao_clicar=self._abrir_cadastro).grid(
            row=0, column=2, sticky="e"
        )

        ctk.CTkFrame(self, height=1, fg_color=Tema.BORDA_CARD, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=24, pady=(12, 0)
        )

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="nsew", padx=24, pady=12)
        corpo.grid_rowconfigure(0, weight=1)
        corpo.grid_columnconfigure(0, weight=1)

        self._tabela = _TabelaFuncionarios(corpo)
        self._tabela.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._tabela.ao_selecionar(self._ao_selecionar)

        self._painel = _PainelDetalhe(
            corpo,
            ao_editar=self._abrir_edicao,
            ao_toggle=self._toggle_ativo,
            ao_redefinir_senha=self._abrir_redefinir_senha,
        )
        self._painel.grid(row=0, column=1, sticky="nsew")

        self._barra = BarraStatus(self)
        self._barra.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))

    def _carregar(self) -> None:
        """Carrega a lista de funcionários do banco."""
        apenas_ativos = not bool(self._chk_inativos.get())
        try:
            self._funcionarios = listar(apenas_ativos=apenas_ativos)
        except ConexaoError as e:
            self._barra.erro(str(e))
            return
        self._painel.limpar()
        self._filtrar()

    def _filtrar(self) -> None:
        """Filtra os funcionários carregados pelo termo de busca."""
        termo = self._campo_busca.get().strip().lower()
        self._lista_filtrada = (
            [
                u
                for u in self._funcionarios
                if termo in u.nome_completo.lower() or termo in u.login.lower()
            ]
            if termo
            else list(self._funcionarios)
        )
        self._tabela.popular(self._lista_filtrada)
        total = len(self._lista_filtrada)
        total_geral = len(self._funcionarios)
        if termo:
            self._barra.info(
                f'{total} resultado(s) para "{self._campo_busca.get().strip()}"'
                f"  (de {total_geral} total)"
            )
        else:
            self._barra.info(f"{total_geral} funcionário(s) encontrado(s).")

    def _ao_selecionar(self, usuario: Usuario) -> None:
        """Exibe o detalhe do funcionário selecionado na tabela."""
        self._painel.exibir(usuario)

    def _abrir_cadastro(self) -> None:
        """Abre o formulário de cadastro de novo funcionário."""
        _JanelaCadastroFuncionario(
            cast(ctk.CTk, self.winfo_toplevel()),
            usuario=None,
            ao_salvar=self._carregar,
        ).grab_set()

    def _abrir_edicao(self, usuario: Usuario) -> None:
        """Busca o funcionário completo e abre o formulário de edição."""
        try:
            completo = buscar_por_id(usuario.id)
        except ConexaoError as e:
            self._barra.erro(str(e))
            return
        if completo is None:
            self._barra.erro("Funcionário não encontrado.")
            return
        _JanelaCadastroFuncionario(
            cast(ctk.CTk, self.winfo_toplevel()),
            usuario=completo,
            ao_salvar=self._carregar,
        ).grab_set()

    def _toggle_ativo(self, usuario: Usuario) -> None:
        """Ativa ou desativa o funcionário conforme o estado atual."""
        try:
            if usuario.ativo:
                desativar(usuario.id)
                self._barra.sucesso(f'"{usuario.nome_completo}" desativado.')
            else:
                reativar(usuario.id)
                self._barra.sucesso(f'"{usuario.nome_completo}" reativado.')
        except ConexaoError as e:
            self._barra.erro(str(e))
        self._carregar()

    def _abrir_redefinir_senha(self, usuario: Usuario) -> None:
        """Abre o formulário de redefinição de senha para o funcionário."""
        _JanelaRedefinirSenha(
            cast(ctk.CTk, self.winfo_toplevel()),
            usuario=usuario,
            ao_salvar=self._carregar,
        ).grab_set()


# ---------------------------------------------------------------------------
# Formulários — CTkToplevel (modais)
# ---------------------------------------------------------------------------


class _JanelaCadastroFuncionario(ctk.CTkToplevel):
    """Formulário modal para cadastro e edição de funcionários."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        usuario: Usuario | None,
        ao_salvar: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._usuario = usuario
        self._ao_salvar = ao_salvar
        self._editando = usuario is not None

        self.title(
            "FerroFlux — " + ("Editar" if self._editando else "Novo") + " Funcionário"
        )
        self.geometry("500x560")
        self.minsize(460, 520)
        self.resizable(True, False)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()

        self._f_nome: CampoTexto
        self._f_login: CampoTexto
        self._f_perfil: ComboSelecao
        self._f_senha: CampoSenha
        self._f_confirmar: CampoSenha
        self._barra: BarraStatus

        self._construir_ui()

        if self._editando and self._usuario is not None:
            self._preencher(self._usuario)

    def _centralizar(self) -> None:
        """Centraliza a janela na tela."""
        self.update_idletasks()
        w, h = 500, 560
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _construir_ui(self) -> None:
        """Monta todos os widgets do formulário de funcionário."""
        raiz = ctk.CTkFrame(self, fg_color=Tema.FUNDO_JANELA, corner_radius=0)
        raiz.pack(fill="both", expand=True)
        raiz.grid_rowconfigure(0, weight=1)
        raiz.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(raiz, fg_color=Tema.FUNDO_JANELA)
        scroll.grid(row=0, column=0, sticky="nsew")

        card = CartaoFrame(scroll)
        card.pack(fill="x", padx=20, pady=16)

        prefixo = "✏  Editar" if self._editando else "👤  Novo"
        Titulo(card, f"{prefixo} Funcionário").pack(pady=(22, 2), padx=24, anchor="w")
        Subtitulo(card, "Preencha os dados abaixo.").pack(padx=24, anchor="w")
        Separador(card).pack(fill="x", padx=24, pady=12)

        def campo(label: str, placeholder: str = "") -> CampoTexto:
            Rotulo(card, label).pack(anchor="w", padx=24, pady=(8, 2))
            c = CampoTexto(card, placeholder=placeholder)
            c.pack(fill="x", padx=24)
            return c

        self._f_nome = campo("Nome completo: *", "Ex: João da Silva")
        self._f_login = campo("Login: *", "Somente letras, números e _")

        Rotulo(card, "Perfil: *").pack(anchor="w", padx=24, pady=(12, 2))
        self._f_perfil = ComboSelecao(card, valores=["ADM", "FUNCIONARIO"])
        self._f_perfil.set("FUNCIONARIO")
        self._f_perfil.pack(fill="x", padx=24)

        Separador(card).pack(fill="x", padx=24, pady=12)
        senha_hint = (
            "Mínimo 6 caracteres"
            if not self._editando
            else "Deixe em branco para não alterar"
        )
        Rotulo(card, "Senha:" + (" *" if not self._editando else "")).pack(
            anchor="w", padx=24, pady=(0, 2)
        )
        self._f_senha = CampoSenha(card, placeholder=senha_hint)
        self._f_senha.pack(fill="x", padx=24)

        Rotulo(card, "Confirmar senha:" + (" *" if not self._editando else "")).pack(
            anchor="w", padx=24, pady=(10, 2)
        )
        self._f_confirmar = CampoSenha(card, placeholder="Repita a senha")
        self._f_confirmar.pack(fill="x", padx=24)

        Rotulo(card, "* Campos obrigatórios", secundario=True).pack(
            anchor="w", padx=24, pady=(14, 0)
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

    def _preencher(self, u: Usuario) -> None:
        """Preenche os campos com os dados do funcionário existente."""
        self._f_nome.insert(0, u.nome_completo)
        self._f_login.insert(0, u.login)
        self._f_perfil.set(u.perfil.upper())

    def _validar(self) -> tuple[str, str, str, str | None] | None:
        """Valida os campos e retorna (nome, login, perfil, senha_hash) ou None."""
        nome = self._f_nome.get().strip()
        login = self._f_login.get().strip()
        perfil = self._f_perfil.get().strip()
        senha = self._f_senha.get()
        confirmar = self._f_confirmar.get()

        if not nome:
            self._barra.erro("Nome completo é obrigatório.")
            return None

        ok, msg = login_valido(login)
        if not ok:
            self._barra.erro(msg)
            return None

        if not perfil:
            self._barra.erro("Selecione um perfil.")
            return None

        senha_hash: str | None = None
        if senha or confirmar:
            ok, msg = senha_valida(senha)
            if not ok:
                self._barra.erro(msg)
                return None
            if senha != confirmar:
                self._barra.erro("As senhas não coincidem.")
                return None
            senha_hash = hash_senha(senha)
        elif not self._editando:
            self._barra.erro("Senha é obrigatória.")
            return None

        return nome, login, perfil, senha_hash

    def _salvar(self) -> None:
        """Valida os dados e persiste o funcionário no banco."""
        dados = self._validar()
        if dados is None:
            return

        nome, login, perfil, senha_hash = dados
        exceto_id = self._usuario.id if self._usuario else None

        self._barra.info("Salvando...")
        self.update_idletasks()

        try:
            if login_existe(login, exceto_id=exceto_id):
                self._barra.erro("Este login já está em uso.")
                return

            if self._editando and self._usuario is not None:
                atualizar(
                    id_usuario=self._usuario.id,
                    login=login,
                    nome_completo=nome,
                    perfil=perfil,
                    senha_hash=senha_hash,
                )
                self._barra.sucesso("Funcionário atualizado com sucesso!")
            else:
                if senha_hash is None:
                    self._barra.erro("Senha é obrigatória.")
                    return
                cadastrar(
                    login=login,
                    senha_hash=senha_hash,
                    nome_completo=nome,
                    perfil=perfil,
                )
                self._barra.sucesso("Funcionário cadastrado com sucesso!")

        except ConexaoError as e:
            self._barra.erro(f"Erro de conexão: {e}")
            return
        except pyodbc.Error as e:
            self._barra.erro(f"Erro no banco de dados: {e}")
            return
        except ValueError as e:
            self._barra.erro(str(e))
            return

        self._ao_salvar()
        self.after(800, self.destroy)


class _JanelaRedefinirSenha(ctk.CTkToplevel):
    """Formulário modal para redefinição de senha de um funcionário."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkToplevel,
        usuario: Usuario,
        ao_salvar: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._usuario = usuario
        self._ao_salvar = ao_salvar

        self.title(f"FerroFlux — Redefinir Senha: {usuario.nome_completo}")
        self.geometry("420x380")
        self.resizable(False, False)
        self.configure(fg_color=Tema.FUNDO_JANELA)
        self._centralizar()

        self._f_senha: CampoSenha
        self._f_confirmar: CampoSenha
        self._barra: BarraStatus

        self._construir_ui()

    def _centralizar(self) -> None:
        """Centraliza a janela na tela."""
        self.update_idletasks()
        w, h = 420, 380
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _construir_ui(self) -> None:
        """Monta os widgets do formulário de redefinição de senha."""
        card = CartaoFrame(cast(ctk.CTkFrame, self))
        card.pack(fill="both", expand=True, padx=20, pady=20)

        Titulo(card, "🔑  Redefinir Senha").pack(anchor="w", padx=24, pady=(22, 2))
        Subtitulo(card, f"Usuário: {self._usuario.nome_completo}").pack(
            anchor="w", padx=24
        )
        Separador(card).pack(fill="x", padx=24, pady=12)

        Rotulo(card, "Nova senha: *").pack(anchor="w", padx=24, pady=(0, 2))
        self._f_senha = CampoSenha(card, placeholder="Mínimo 6 caracteres")
        self._f_senha.pack(fill="x", padx=24)

        Rotulo(card, "Confirmar nova senha: *").pack(anchor="w", padx=24, pady=(10, 2))
        self._f_confirmar = CampoSenha(card, placeholder="Repita a senha")
        self._f_confirmar.pack(fill="x", padx=24)

        Separador(card).pack(fill="x", padx=24, pady=12)

        self._barra = BarraStatus(card)
        self._barra.pack(fill="x", padx=24, pady=(0, 8))

        fb = ctk.CTkFrame(card, fg_color="transparent")
        fb.pack(fill="x", padx=24, pady=(0, 24))
        fb.columnconfigure((0, 1), weight=1)
        Botao(fb, "Cancelar", variante="neutro", ao_clicar=self.destroy).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        Botao(fb, "💾  Salvar", variante="sucesso", ao_clicar=self._salvar).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

    def _salvar(self) -> None:
        """Valida as senhas e persiste a nova senha no banco."""
        senha = self._f_senha.get()
        confirmar = self._f_confirmar.get()

        ok, msg = senha_valida(senha)
        if not ok:
            self._barra.erro(msg)
            return
        if senha != confirmar:
            self._barra.erro("As senhas não coincidem.")
            return

        self._barra.info("Salvando...")
        self.update_idletasks()

        try:
            redefinir_senha(self._usuario.id, hash_senha(senha))
            self._barra.sucesso("Senha redefinida com sucesso!")
        except ConexaoError as e:
            self._barra.erro(f"Erro de conexão: {e}")
            return

        self._ao_salvar()
        self.after(800, self.destroy)
