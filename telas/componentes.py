"""
telas/componentes.py
--------------------
Biblioteca de componentes reutilizáveis para a interface FerroFlux.
Construída sobre CustomTkinter.

Instale com: pip install customtkinter

Componentes disponíveis:
    Tema            — paleta de cores e fontes centralizada
    JanelaPadrao    — janela raiz com aparência padrão
    CartaoFrame     — frame com visual de card/painel
    Titulo          — título principal da tela (H1 ou H2)
    Subtitulo       — texto descritivo abaixo do título
    Rotulo          — label de campo de formulário
    CampoTexto      — input estilizado com foco, max_length opcional
    CampoSenha      — input de senha (herda CampoTexto)
    CampoData       — input formatado dd/mm/aaaa com validação embutida
    Botao           — botão semântico (primario/sucesso/perigo/aviso/neutro)
    BotaoIcone      — botão quadrado com ícone (menu principal)
    BarraStatus     — faixa de feedback (info/sucesso/erro)
    Separador       — linha divisória horizontal
    ListaSelecao    — listbox + scrollbar integrada
    ComboSelecao    — combobox estilizado
    Tooltip         — dica flutuante ao passar o mouse sobre qualquer widget
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Callable, Literal

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Tema
# ---------------------------------------------------------------------------


class Tema:
    """
    Fonte única de verdade para cores e tipografia do FerroFlux.
    Tema claro, moderno e limpo.
    Todos os atributos são constantes de classe — não instancie esta classe.
    """

    # --- Fundo ---
    FUNDO_JANELA = "#f0f4ff"  # azul-gelo muito suave — fundo geral
    FUNDO_CARD = "#ffffff"  # branco puro — cards
    FUNDO_INPUT = "#f8f9fe"  # quase branco com toque azulado — inputs
    FUNDO_STATUS = "#f0f4ff"  # mesma do fundo — barra de status

    # --- Bordas ---
    BORDA_CARD = "#dde3f5"  # azul-cinza suave
    BORDA_INPUT = "#cdd5f0"  # um grau mais escuro
    BORDA_FOCO = "#4f7cff"  # azul elétrico ao focar

    # --- Texto ---
    TEXTO_TITULO = "#0f1733"  # azul-marinho quase preto
    TEXTO_PRINCIPAL = "#1e2a4a"  # azul-marinho médio
    TEXTO_SECUNDARIO = "#6b7a9e"  # azul-cinza — hints, labels menores
    TEXTO_PLACEHOLDER = "#a8b3d1"  # cinza claro — placeholder

    # --- Ações ---
    PRIMARIO = "#4f7cff"
    PRIMARIO_HOVER = "#3a68f0"
    PRIMARIO_TEXTO = "#ffffff"

    SUCESSO = "#10b981"
    SUCESSO_HOVER = "#059669"
    SUCESSO_TEXTO = "#ffffff"

    PERIGO = "#f43f5e"
    PERIGO_HOVER = "#e11d48"
    PERIGO_TEXTO = "#ffffff"

    AVISO = "#f59e0b"
    AVISO_HOVER = "#d97706"
    AVISO_TEXTO = "#ffffff"

    NEUTRO = "#e2e8f8"
    NEUTRO_HOVER = "#cdd5f0"
    NEUTRO_TEXTO = "#1e2a4a"

    # --- Botão de menu ---
    BOTAO_MENU_BG = "#eef2ff"
    BOTAO_MENU_HOVER = "#dde5ff"
    BOTAO_MENU_BORDA = "#c7d2fe"
    BOTAO_MENU_ICONE = "#4f7cff"
    BOTAO_MENU_TEXTO = "#1e2a4a"

    # --- Botão sair ---
    BOTAO_SAIR_BG = "#fff1f3"
    BOTAO_SAIR_HOVER = "#ffe4e8"
    BOTAO_SAIR_BORDA = "#fda4af"
    BOTAO_SAIR_ICONE = "#f43f5e"
    BOTAO_SAIR_TEXTO = "#1e2a4a"

    # --- Scrollbar ---
    SCROLL_FUNDO = "#e2e8f8"
    SCROLL_BOTAO = "#a8b3d1"

    # --- Barra de status ---
    STATUS_INFO = "#6b7a9e"
    STATUS_SUCESSO = "#059669"
    STATUS_ERRO = "#e11d48"

    # --- Tipografia ---
    # DM Sans: moderna, humanista, excelente legibilidade
    # Trebuchet MS: fallback universal Windows quando DM Sans não estiver instalada
    FAMILIA_TITULO = "DM Sans"
    FAMILIA_CORPO = "DM Sans"
    FAMILIA_MONO = "Cascadia Code"
    FAMILIA_FB = "Trebuchet MS"
    FAMILIA_MONO_FB = "Consolas"

    TAMANHO_H1 = 26
    TAMANHO_H2 = 18
    TAMANHO_H3 = 14
    TAMANHO_LABEL = 12
    TAMANHO_CORPO = 12
    TAMANHO_PEQUENO = 10
    TAMANHO_BOTAO = 12
    TAMANHO_ICONE = 30
    TAMANHO_ICONE_TX = 11

    @classmethod
    def aplicar(cls) -> None:
        """Aplica o tema claro como padrão do CustomTkinter."""
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

    @classmethod
    def fonte(
        cls,
        tamanho: int,
        peso: Literal["normal", "bold"] = "normal",
        familia: str | None = None,
    ) -> ctk.CTkFont:
        """Retorna uma CTkFont com os padrões do tema."""
        return ctk.CTkFont(
            family=familia or cls.FAMILIA_CORPO,
            size=tamanho,
            weight=peso,
        )

    @classmethod
    def fonte_titulo(cls, tamanho: int | None = None) -> ctk.CTkFont:
        """Retorna uma CTkFont bold para títulos."""
        return ctk.CTkFont(
            family=cls.FAMILIA_TITULO,
            size=tamanho or cls.TAMANHO_H2,
            weight="bold",
        )

    @classmethod
    def fonte_mono(cls, tamanho: int | None = None) -> ctk.CTkFont:
        """Retorna uma CTkFont monoespaçada (barra de status, código)."""
        return ctk.CTkFont(
            family=cls.FAMILIA_MONO,
            size=tamanho or cls.TAMANHO_PEQUENO,
        )


# ---------------------------------------------------------------------------
# Janela base
# ---------------------------------------------------------------------------


class JanelaPadrao(ctk.CTk):
    """
    Janela raiz com aparência padrão FerroFlux.
    Centraliza automaticamente na tela ao ser criada.

    Uso:
        janela = JanelaPadrao("Login", 480, 580)
        janela.mainloop()
    """

    def __init__(
        self,
        titulo: str,
        largura: int,
        altura: int,
        redimensionavel: bool = False,
    ) -> None:
        Tema.aplicar()
        super().__init__()

        self.title(titulo)
        self.geometry(f"{largura}x{altura}")
        self.resizable(redimensionavel, redimensionavel)
        self.configure(fg_color=Tema.FUNDO_JANELA)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------


class CartaoFrame(ctk.CTkFrame):
    """
    Frame com visual de card branco com borda suave.
    Aceita CTkScrollableFrame como master para uso em telas roláveis.

    Uso:
        card = CartaoFrame(janela)
        card.pack(padx=24, pady=16, fill="both", expand=True)
    """

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame | ctk.CTkScrollableFrame,
        **kwargs,
    ) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        super().__init__(master, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tipografia
# ---------------------------------------------------------------------------


class Titulo(ctk.CTkLabel):
    """
    Título principal da tela.

    Parâmetros:
        grande: True para splash/welcome (H1), False para telas normais (H2).

    Uso:
        Titulo(card, "FerroFlux", grande=True).pack(pady=(28, 6))
        Titulo(card, "Gerenciar Materiais").pack(pady=(28, 6))
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        texto: str,
        grande: bool = False,
        **kwargs,
    ) -> None:
        tamanho = Tema.TAMANHO_H1 if grande else Tema.TAMANHO_H2
        kwargs.setdefault("text_color", Tema.TEXTO_TITULO)
        super().__init__(master, text=texto, font=Tema.fonte_titulo(tamanho), **kwargs)


class Subtitulo(ctk.CTkLabel):
    """
    Texto descritivo abaixo do título.

    Uso:
        Subtitulo(card, "Faça login para continuar").pack(pady=(0, 24))
    """

    def __init__(self, master: ctk.CTkFrame, texto: str, **kwargs) -> None:
        kwargs.setdefault("text_color", Tema.TEXTO_SECUNDARIO)
        super().__init__(master, text=texto, font=Tema.fonte(Tema.TAMANHO_H3), **kwargs)


class Rotulo(ctk.CTkLabel):
    """
    Label de campo de formulário.

    Parâmetros:
        secundario: True para hints e observações (cor e peso mais suaves).

    Uso:
        Rotulo(card, "Nome completo: *").pack(anchor="w", pady=(12, 3))
        Rotulo(card, "* Campos obrigatórios", secundario=True).pack(anchor="w")
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        texto: str,
        secundario: bool = False,
        **kwargs,
    ) -> None:
        cor: str = Tema.TEXTO_SECUNDARIO if secundario else Tema.TEXTO_PRINCIPAL
        peso: Literal["normal", "bold"] = "normal" if secundario else "bold"
        kwargs.setdefault("text_color", cor)
        super().__init__(
            master, text=texto, font=Tema.fonte(Tema.TAMANHO_LABEL, peso), **kwargs
        )


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class CampoTexto(ctk.CTkEntry):
    """
    Campo de texto estilizado com highlight ao focar.

    Parâmetros:
        placeholder: texto exibido quando o campo está vazio.
        max_length:  limite de caracteres (None = sem limite).

    Uso:
        campo = CampoTexto(card, placeholder="Ex: João da Silva", max_length=100)
        campo.pack(fill="x", pady=(3, 14))
        valor = campo.get().strip()
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        placeholder: str = "",
        max_length: int | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_INPUT)
        kwargs.setdefault("border_color", Tema.BORDA_INPUT)
        kwargs.setdefault("text_color", Tema.TEXTO_PRINCIPAL)
        kwargs.setdefault("placeholder_text_color", Tema.TEXTO_PLACEHOLDER)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("height", 42)
        kwargs.setdefault("font", Tema.fonte(Tema.TAMANHO_CORPO))
        super().__init__(master, placeholder_text=placeholder, **kwargs)

        self.bind("<FocusIn>", lambda _: self.configure(border_color=Tema.BORDA_FOCO))
        self.bind("<FocusOut>", lambda _: self.configure(border_color=Tema.BORDA_INPUT))

        if max_length is not None:
            self._max_length = max_length
            vcmd = (self.register(self._validar_length), "%P")
            self.configure(validate="key", validatecommand=vcmd)

    def _validar_length(self, novo_valor: str) -> bool:
        """Rejeita entrada que exceda max_length."""
        return len(novo_valor) <= self._max_length


class CampoSenha(CampoTexto):
    """
    Campo de senha — herda CampoTexto com show="*".

    Uso:
        campo = CampoSenha(card, placeholder="Mínimo 6 caracteres")
        campo.pack(fill="x", pady=(3, 14))
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        placeholder: str = "Digite a senha",
        **kwargs,
    ) -> None:
        kwargs["show"] = "*"
        super().__init__(master, placeholder=placeholder, **kwargs)


class CampoData(ctk.CTkFrame):
    """
    Campo de data formatado como dd/mm/aaaa.

    Aplica máscara automaticamente enquanto o usuário digita e
    valida a data ao perder o foco. Se inválida, borda fica vermelha
    e get() retorna None.

    Uso:
        campo = CampoData(card)
        campo.pack(fill="x", pady=(3, 14))

        dt: datetime | None = campo.get()   # None se inválido ou vazio
        campo.set(datetime(2025, 1, 31))    # preenche programaticamente
    """

    def __init__(self, master: ctk.CTkFrame, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 0)
        super().__init__(master, **kwargs)

        self._var = tk.StringVar()
        self._entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            placeholder_text="dd/mm/aaaa",
            fg_color=Tema.FUNDO_INPUT,
            border_color=Tema.BORDA_INPUT,
            text_color=Tema.TEXTO_PRINCIPAL,
            placeholder_text_color=Tema.TEXTO_PLACEHOLDER,
            corner_radius=8,
            border_width=1,
            height=42,
            font=Tema.fonte(Tema.TAMANHO_CORPO),
            width=140,
        )
        self._entry.pack(fill="x", expand=True)
        self._entry.bind(
            "<FocusIn>", lambda _: self._entry.configure(border_color=Tema.BORDA_FOCO)
        )
        self._entry.bind("<FocusOut>", self._ao_perder_foco)
        self._var.trace_add("write", lambda *_: self._aplicar_mascara())
        self._aplicando_mascara = False

    def _aplicar_mascara(self) -> None:
        """Insere '/' automaticamente nas posições 2 e 5 enquanto o usuário digita."""
        if self._aplicando_mascara:
            return
        self._aplicando_mascara = True
        try:
            raw = self._var.get().replace("/", "")[:8]  # só dígitos, máx 8
            formatado = ""
            for i, c in enumerate(raw):
                if not c.isdigit():
                    continue
                if i in (2, 4):
                    formatado += "/"
                formatado += c
            pos = self._entry.index("insert")
            self._var.set(formatado)
            # Reposiciona o cursor após a formatação
            novo_pos = min(pos + (1 if pos in (2, 5) else 0), len(formatado))
            self._entry.icursor(novo_pos)
        finally:
            self._aplicando_mascara = False

    def _ao_perder_foco(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        """Valida a data ao sair do campo — borda vermelha se inválida."""
        valor = self._var.get().strip()
        if not valor:
            self._entry.configure(border_color=Tema.BORDA_INPUT)
            return
        if self._parse(valor) is None:
            self._entry.configure(border_color=Tema.PERIGO)
        else:
            self._entry.configure(border_color=Tema.BORDA_INPUT)

    @staticmethod
    def _parse(valor: str) -> datetime | None:
        """Tenta interpretar a string como dd/mm/aaaa. Retorna None se inválida."""
        try:
            return datetime.strptime(valor.strip(), "%d/%m/%Y")
        except ValueError:
            return None

    def get(self) -> datetime | None:
        """
        Retorna o valor como datetime ou None se vazio / inválido.

        Uso:
            dt = campo_data.get()
            if dt is None:
                barra.erro("Data inválida.")
        """
        return self._parse(self._var.get())

    def set(self, data: datetime) -> None:
        """Preenche o campo com um objeto datetime."""
        self._var.set(data.strftime("%d/%m/%Y"))

    def limpar(self) -> None:
        """Limpa o campo e restaura a borda padrão."""
        self._var.set("")
        self._entry.configure(border_color=Tema.BORDA_INPUT)


# ---------------------------------------------------------------------------
# Botões
# ---------------------------------------------------------------------------

_ESTILOS_BOTAO: dict[str, tuple[str, str, str]] = {
    "primario": (Tema.PRIMARIO, Tema.PRIMARIO_HOVER, Tema.PRIMARIO_TEXTO),
    "sucesso": (Tema.SUCESSO, Tema.SUCESSO_HOVER, Tema.SUCESSO_TEXTO),
    "perigo": (Tema.PERIGO, Tema.PERIGO_HOVER, Tema.PERIGO_TEXTO),
    "aviso": (Tema.AVISO, Tema.AVISO_HOVER, Tema.AVISO_TEXTO),
    "neutro": (Tema.NEUTRO, Tema.NEUTRO_HOVER, Tema.NEUTRO_TEXTO),
}


class Botao(ctk.CTkButton):
    """
    Botão com variante semântica.

    Variantes: "primario" | "sucesso" | "perigo" | "aviso" | "neutro"

    Uso:
        Botao(card, "Salvar", variante="sucesso",
              ao_clicar=minha_funcao).pack(fill="x", pady=4)
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        texto: str,
        variante: str = "primario",
        ao_clicar: Callable | None = None,
        **kwargs,
    ) -> None:
        bg, hover, fg = _ESTILOS_BOTAO.get(variante, _ESTILOS_BOTAO["primario"])
        kwargs.setdefault("fg_color", bg)
        kwargs.setdefault("hover_color", hover)
        kwargs.setdefault("text_color", fg)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("height", 44)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("font", Tema.fonte(Tema.TAMANHO_BOTAO, "bold"))
        super().__init__(master, text=texto, command=ao_clicar, **kwargs)


class BotaoIcone(ctk.CTkFrame):
    """
    Botão grande quadrado com ícone e legenda — menu principal.

    Parâmetros:
        variante: "padrao" | "sair"

    Uso:
        BotaoIcone(grade, "📦", "Materiais",
                   ao_clicar=abrir_materiais).grid(row=0, column=0, padx=6, pady=6)
    """

    TAMANHO = 132

    def __init__(
        self,
        master: ctk.CTkFrame,
        icone: str,
        texto: str,
        ao_clicar: Callable | None = None,
        variante: str = "padrao",
        **kwargs,
    ) -> None:
        if variante == "sair":
            bg = Tema.BOTAO_SAIR_BG
            hover = Tema.BOTAO_SAIR_HOVER
            borda = Tema.BOTAO_SAIR_BORDA
            cor_ic = Tema.BOTAO_SAIR_ICONE
            cor_tx = Tema.BOTAO_SAIR_TEXTO
        else:
            bg = Tema.BOTAO_MENU_BG
            hover = Tema.BOTAO_MENU_HOVER
            borda = Tema.BOTAO_MENU_BORDA
            cor_ic = Tema.BOTAO_MENU_ICONE
            cor_tx = Tema.BOTAO_MENU_TEXTO

        super().__init__(
            master,
            width=self.TAMANHO,
            height=self.TAMANHO,
            fg_color=bg,
            corner_radius=14,
            border_width=1,
            border_color=borda,
            cursor="hand2",
            **kwargs,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._bg = bg
        self._hover = hover
        self._callback = ao_clicar

        self._icone = ctk.CTkLabel(
            self,
            text=icone,
            font=ctk.CTkFont(size=Tema.TAMANHO_ICONE),
            text_color=cor_ic,
            fg_color="transparent",
        )
        self._icone.pack(pady=(22, 4))

        self._texto_label = ctk.CTkLabel(
            self,
            text=texto,
            font=Tema.fonte(Tema.TAMANHO_ICONE_TX, "bold"),
            text_color=cor_tx,
            fg_color="transparent",
            justify="center",
        )
        self._texto_label.pack()

        for w in (self, self._icone, self._texto_label):
            w.bind("<Enter>", lambda _: self.configure(fg_color=self._hover))
            w.bind("<Leave>", lambda _: self.configure(fg_color=self._bg))
            w.bind("<Button-1>", lambda _: self._callback() if self._callback else None)


# ---------------------------------------------------------------------------
# Barra de status
# ---------------------------------------------------------------------------


class BarraStatus(ctk.CTkFrame):
    """
    Faixa de feedback — exibe mensagens de info / sucesso / erro.

    Uso:
        barra = BarraStatus(card)
        barra.pack(fill="x", padx=24, pady=(8, 20))

        barra.info("Aguardando...")
        barra.sucesso("Registro salvo!")
        barra.erro("Login inválido.")
        barra.limpar()
    """

    def __init__(self, master: ctk.CTkFrame, **kwargs) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_STATUS)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Tema.BORDA_CARD)
        kwargs.setdefault("height", 36)
        super().__init__(master, **kwargs)

        self._label = ctk.CTkLabel(
            self,
            text="",
            font=Tema.fonte_mono(),
            text_color=Tema.STATUS_INFO,
            fg_color="transparent",
            anchor="w",
        )
        self._label.pack(padx=14, fill="x", expand=True)

    def _set(self, texto: str, cor: str) -> None:
        self._label.configure(text=texto, text_color=cor)

    def info(self, texto: str) -> None:
        """Exibe mensagem informativa (cinza)."""
        self._set(f"  {texto}", Tema.STATUS_INFO)

    def sucesso(self, texto: str) -> None:
        """Exibe mensagem de sucesso (verde)."""
        self._set(f"✓  {texto}", Tema.STATUS_SUCESSO)

    def erro(self, texto: str) -> None:
        """Exibe mensagem de erro (vermelho)."""
        self._set(f"✕  {texto}", Tema.STATUS_ERRO)

    def limpar(self) -> None:
        """Remove o texto da barra."""
        self._set("", Tema.STATUS_INFO)


# ---------------------------------------------------------------------------
# Separador
# ---------------------------------------------------------------------------


class Separador(ctk.CTkFrame):
    """
    Linha divisória horizontal sutil.

    Uso:
        Separador(card).pack(fill="x", padx=24, pady=12)
    """

    def __init__(self, master: ctk.CTkFrame, **kwargs) -> None:
        kwargs.setdefault("fg_color", Tema.BORDA_CARD)
        kwargs.setdefault("height", 1)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)


# ---------------------------------------------------------------------------
# Lista de seleção
# ---------------------------------------------------------------------------


class ListaSelecao(ctk.CTkFrame):
    """
    Listbox estilizado com scrollbar integrada.

    Uso:
        lista = ListaSelecao(card, altura=7)
        lista.pack(fill="both", expand=True, padx=24, pady=(4, 0))

        lista.inserir("Texto do item")
        lista.limpar()
        idx  = lista.selecao_atual()         # int | None
        lista.ao_selecionar(minha_funcao)    # callback(idx: int)
        n    = lista.total()                 # int
        lista.limpar_selecao()
    """

    def __init__(self, master: ctk.CTkFrame, altura: int = 8, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        sb = tk.Scrollbar(
            self,
            orient="vertical",
            bg=Tema.SCROLL_FUNDO,
            troughcolor=Tema.FUNDO_INPUT,
            activebackground=Tema.PRIMARIO,
            highlightthickness=0,
            bd=0,
        )
        sb.pack(side="right", fill="y")

        self._lb = tk.Listbox(
            self,
            height=altura,
            bg=Tema.FUNDO_INPUT,
            fg=Tema.TEXTO_PRINCIPAL,
            selectbackground=Tema.PRIMARIO,
            selectforeground="#ffffff",
            activestyle="none",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=Tema.BORDA_INPUT,
            highlightcolor=Tema.BORDA_FOCO,
            font=(Tema.FAMILIA_FB, Tema.TAMANHO_CORPO),
            yscrollcommand=sb.set,
            selectmode="single",
            cursor="hand2",
        )
        self._lb.pack(side="left", fill="both", expand=True)
        sb.config(command=self._lb.yview)

    def inserir(self, texto: str, pos: int | str = tk.END) -> None:
        """Insere um item na lista."""
        self._lb.insert(pos, f"  {texto}")

    def limpar(self) -> None:
        """Remove todos os itens da lista."""
        self._lb.delete(0, tk.END)

    def selecao_atual(self) -> int | None:
        """Retorna o índice do item selecionado ou None."""
        sel = self._lb.curselection()
        return sel[0] if sel else None

    def ao_selecionar(self, callback: Callable[[int], None]) -> None:
        """Registra um callback chamado com o índice ao selecionar um item."""

        def _h(_: tk.Event) -> None:  # type: ignore[type-arg]
            idx = self.selecao_atual()
            if idx is not None:
                callback(idx)

        self._lb.bind("<<ListboxSelect>>", _h)

    def limpar_selecao(self) -> None:
        """Desfaz a seleção atual."""
        self._lb.selection_clear(0, tk.END)

    def total(self) -> int:
        """Retorna o número de itens na lista."""
        return self._lb.size()


# ---------------------------------------------------------------------------
# Combobox
# ---------------------------------------------------------------------------


class ComboSelecao(ctk.CTkComboBox):
    """
    Combobox estilizado.

    Uso:
        combo = ComboSelecao(card, valores=["ADM", "Funcionário"])
        combo.pack(fill="x", pady=(3, 14))
        valor = combo.get()
    """

    def __init__(
        self,
        master: ctk.CTkFrame,
        valores: list[str] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("fg_color", Tema.FUNDO_INPUT)
        kwargs.setdefault("border_color", Tema.BORDA_INPUT)
        kwargs.setdefault("button_color", Tema.PRIMARIO)
        kwargs.setdefault("button_hover_color", Tema.PRIMARIO_HOVER)
        kwargs.setdefault("text_color", Tema.TEXTO_PRINCIPAL)
        kwargs.setdefault("dropdown_fg_color", Tema.FUNDO_CARD)
        kwargs.setdefault("dropdown_hover_color", Tema.NEUTRO)
        kwargs.setdefault("dropdown_text_color", Tema.TEXTO_PRINCIPAL)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("height", 42)
        kwargs.setdefault("state", "readonly")
        kwargs.setdefault("font", Tema.fonte(Tema.TAMANHO_CORPO))
        super().__init__(master, values=valores or [], **kwargs)

        self.bind("<FocusIn>", lambda _: self.configure(border_color=Tema.BORDA_FOCO))
        self.bind("<FocusOut>", lambda _: self.configure(border_color=Tema.BORDA_INPUT))


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------


class Tooltip:
    """
    Dica flutuante exibida ao passar o mouse sobre qualquer widget.
    Aparece após 500 ms e some ao mover o mouse para fora.

    Uso:
        campo = CampoTexto(card, placeholder="Login")
        Tooltip(campo, "Somente letras, números e _")

        btn = Botao(card, "Salvar", variante="sucesso", ao_clicar=salvar)
        Tooltip(btn, "Salva as alterações no banco de dados")
    """

    _DELAY_MS = 500
    _BG = "#1e2a4a"
    _FG = "#ffffff"
    _FONTE = ("Trebuchet MS", 10)
    _PAD = 6

    def __init__(self, widget: tk.Widget, texto: str) -> None:
        self._widget = widget
        self._texto = texto
        self._janela: tk.Toplevel | None = None
        self._job: str | None = None

        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._cancelar, add="+")
        widget.bind("<Destroy>", self._cancelar, add="+")

    def _agendar(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        """Agenda a exibição do tooltip após o delay."""
        self._cancelar(_)
        self._job = self._widget.after(self._DELAY_MS, self._mostrar)

    def _mostrar(self) -> None:
        """Cria a janela flutuante do tooltip."""
        if self._janela:
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4

        self._janela = tk.Toplevel(self._widget)
        self._janela.wm_overrideredirect(True)  # sem decoração de janela
        self._janela.wm_geometry(f"+{x}+{y}")
        self._janela.attributes("-topmost", True)

        frame = tk.Frame(
            self._janela,
            bg=self._BG,
            bd=1,
            relief="flat",
            padx=self._PAD,
            pady=self._PAD,
        )
        frame.pack()
        tk.Label(
            frame,
            text=self._texto,
            bg=self._BG,
            fg=self._FG,
            font=self._FONTE,
            justify="left",
            wraplength=280,
        ).pack()

    def _cancelar(self, _: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        """Cancela o agendamento e fecha a janela se estiver aberta."""
        if self._job:
            self._widget.after_cancel(self._job)
            self._job = None
        if self._janela:
            self._janela.destroy()
            self._janela = None
