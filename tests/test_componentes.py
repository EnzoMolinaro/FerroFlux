"""
test_componentes.py — Testes de telas/componentes.py

Todos unitários — testam lógica pura sem abrir janela Tkinter.
(CampoData._parse, Tema, BarraStatus._set, ListaSelecao, etc.)

Execute:
    pytest tests/test_componentes.py -v
"""

import pytest
from datetime import datetime


# ══════════════════════════════════════════════════════
#  TEMA
# ══════════════════════════════════════════════════════

class TestTema:
    """Verifica consistência da paleta e tipografia."""

    def test_cores_primarias_sao_hex(self):
        from telas.componentes import Tema
        for attr in ("PRIMARIO", "SUCESSO", "PERIGO", "AVISO", "NEUTRO"):
            valor = getattr(Tema, attr)
            assert valor.startswith("#"), f"{attr} não é hex: {valor}"
            assert len(valor) in (4, 7), f"{attr} tem tamanho inválido: {valor}"

    def test_tamanhos_de_fonte_sao_positivos(self):
        from telas.componentes import Tema
        for attr in ("TAMANHO_H1", "TAMANHO_H2", "TAMANHO_H3",
                     "TAMANHO_LABEL", "TAMANHO_CORPO", "TAMANHO_BOTAO"):
            assert getattr(Tema, attr) > 0

    def test_h1_maior_que_h2_maior_que_h3(self):
        from telas.componentes import Tema
        assert Tema.TAMANHO_H1 > Tema.TAMANHO_H2 > Tema.TAMANHO_H3

    def test_primario_hover_diferente_de_primario(self):
        from telas.componentes import Tema
        assert Tema.PRIMARIO != Tema.PRIMARIO_HOVER

    def test_perigo_hover_diferente_de_perigo(self):
        from telas.componentes import Tema
        assert Tema.PERIGO != Tema.PERIGO_HOVER

    def test_texto_titulo_diferente_de_texto_secundario(self):
        from telas.componentes import Tema
        assert Tema.TEXTO_TITULO != Tema.TEXTO_SECUNDARIO

    def test_familia_titulo_definida(self):
        from telas.componentes import Tema
        assert len(Tema.FAMILIA_TITULO) > 0

    def test_familia_corpo_definida(self):
        from telas.componentes import Tema
        assert len(Tema.FAMILIA_CORPO) > 0


# ══════════════════════════════════════════════════════
#  CAMPO DATA — _parse (não abre Tkinter)
# ══════════════════════════════════════════════════════

class TestCampoDataParse:
    """
    _parse é um staticmethod puro — testável sem instanciar CampoData
    (que precisaria de uma janela Tk).
    """

    def test_data_valida_retorna_datetime(self):
        from telas.componentes import CampoData
        resultado = CampoData._parse("15/06/2025")
        assert isinstance(resultado, datetime)
        assert resultado.day == 15
        assert resultado.month == 6
        assert resultado.year == 2025

    def test_data_invalida_retorna_none(self):
        from telas.componentes import CampoData
        assert CampoData._parse("99/99/9999") is None

    def test_formato_errado_retorna_none(self):
        from telas.componentes import CampoData
        assert CampoData._parse("2025-06-15") is None  # ISO, não dd/mm/aaaa

    def test_string_vazia_retorna_none(self):
        from telas.componentes import CampoData
        assert CampoData._parse("") is None

    def test_dia_31_em_mes_com_30_dias_invalido(self):
        from telas.componentes import CampoData
        assert CampoData._parse("31/04/2025") is None

    def test_29_fev_ano_bissexto_valido(self):
        from telas.componentes import CampoData
        resultado = CampoData._parse("29/02/2024")
        assert resultado is not None

    def test_29_fev_ano_nao_bissexto_invalido(self):
        from telas.componentes import CampoData
        assert CampoData._parse("29/02/2025") is None

    def test_espacos_em_volta_sao_ignorados(self):
        from telas.componentes import CampoData
        resultado = CampoData._parse("  01/01/2025  ")
        assert resultado is not None

    def test_primeiro_de_janeiro_2025(self):
        from telas.componentes import CampoData
        dt = CampoData._parse("01/01/2025")
        assert dt == datetime(2025, 1, 1)

    def test_ultimo_dia_do_ano(self):
        from telas.componentes import CampoData
        dt = CampoData._parse("31/12/2025")
        assert dt is not None
        assert dt.month == 12
        assert dt.day == 31


# ══════════════════════════════════════════════════════
#  ESTILOS DE BOTÃO
# ══════════════════════════════════════════════════════

class TestEstilosBotao:
    """Verifica que todos os estilos de botão estão definidos."""

    def test_todos_os_estilos_definidos(self):
        from telas.componentes import _ESTILOS_BOTAO
        for variante in ("primario", "sucesso", "perigo", "aviso", "neutro"):
            assert variante in _ESTILOS_BOTAO, f"Estilo '{variante}' não encontrado"

    def test_cada_estilo_tem_tres_cores(self):
        from telas.componentes import _ESTILOS_BOTAO
        for variante, tupla in _ESTILOS_BOTAO.items():
            assert len(tupla) == 3, f"Estilo '{variante}' deve ter (bg, hover, fg)"

    def test_cores_de_estilos_sao_hex(self):
        from telas.componentes import _ESTILOS_BOTAO
        for variante, (bg, hover, fg) in _ESTILOS_BOTAO.items():
            for cor in (bg, hover, fg):
                assert cor.startswith("#"), \
                    f"Cor '{cor}' do estilo '{variante}' não é hexadecimal"

    def test_hover_diferente_de_bg_em_todos(self):
        from telas.componentes import _ESTILOS_BOTAO
        for variante, (bg, hover, _) in _ESTILOS_BOTAO.items():
            assert bg != hover, \
                f"bg e hover idênticos no estilo '{variante}': {bg}"


# ══════════════════════════════════════════════════════
#  BARRA DE STATUS — lógica de prefixos
# ══════════════════════════════════════════════════════

class TestBarraStatusLogica:
    """
    Testa a lógica de prefixo e cor sem instanciar widget Tkinter.
    Usamos um mock simples do label interno.
    """

    def _barra_mockada(self):
        """Cria uma BarraStatus com o label interno substituído por mock."""
        from telas.componentes import BarraStatus, Tema
        from unittest.mock import MagicMock, patch

        # Patch do CTkFrame para não precisar de Tk
        with patch("telas.componentes.ctk.CTkFrame.__init__", return_value=None), \
             patch("telas.componentes.ctk.CTkLabel"):
            barra = BarraStatus.__new__(BarraStatus)
            barra._label = MagicMock()
            return barra

    def test_sucesso_adiciona_prefixo_check(self):
        barra = self._barra_mockada()
        barra.sucesso("Salvo com sucesso!")
        texto = barra._label.configure.call_args[1]["text"]
        assert "✓" in texto

    def test_erro_adiciona_prefixo_x(self):
        barra = self._barra_mockada()
        barra.erro("Falha ao conectar.")
        texto = barra._label.configure.call_args[1]["text"]
        assert "✕" in texto

    def test_info_nao_tem_prefixo_especial(self):
        barra = self._barra_mockada()
        barra.info("Processando...")
        texto = barra._label.configure.call_args[1]["text"]
        assert "Processando..." in texto
        assert "✓" not in texto
        assert "✕" not in texto

    def test_limpar_define_texto_vazio(self):
        barra = self._barra_mockada()
        barra.limpar()
        texto = barra._label.configure.call_args[1]["text"]
        assert texto == ""

    def test_sucesso_usa_cor_verde(self):
        from telas.componentes import Tema
        barra = self._barra_mockada()
        barra.sucesso("OK")
        cor = barra._label.configure.call_args[1]["text_color"]
        assert cor == Tema.STATUS_SUCESSO

    def test_erro_usa_cor_vermelha(self):
        from telas.componentes import Tema
        barra = self._barra_mockada()
        barra.erro("Erro")
        cor = barra._label.configure.call_args[1]["text_color"]
        assert cor == Tema.STATUS_ERRO

    def test_info_usa_cor_cinza(self):
        from telas.componentes import Tema
        barra = self._barra_mockada()
        barra.info("Info")
        cor = barra._label.configure.call_args[1]["text_color"]
        assert cor == Tema.STATUS_INFO
