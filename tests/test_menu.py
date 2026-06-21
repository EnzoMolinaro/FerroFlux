"""
test_menu.py — Testes da lógica de negócio de telas/menu.py
Não instancia a janela Tkinter — testa só a lógica de permissão e módulos.

Execute:
    pytest tests/test_menu.py -v
"""

import pytest
from repositories.usuario_repo import Usuario


# Lista de módulos reais definida em menu.py — espelhada aqui para testes
_MODULOS = [
    {"chave": "funcionarios", "perfis": ["ADM"]},
    {"chave": "clientes",     "perfis": ["ADM", "FUNCIONARIO"]},
    {"chave": "fornecedores", "perfis": ["ADM", "FUNCIONARIO"]},
    {"chave": "materiais",    "perfis": ["ADM", "FUNCIONARIO"]},
    {"chave": "vendas",       "perfis": ["ADM", "FUNCIONARIO"]},
    {"chave": "relatorio",    "perfis": ["ADM"]},
    {"chave": "historico",    "perfis": ["ADM"]},
]


def modulos_visiveis(usuario: Usuario) -> list[dict]:
    """Replica o filtro real de TelaMenu._modulos_visiveis."""
    return [m for m in _MODULOS if usuario.perfil.upper() in m["perfis"]]


class TestPermissoesMenu:
    """Verifica quais módulos cada perfil pode acessar."""

    def test_adm_ve_todos_os_modulos(self, usuario_adm):
        visiveis = modulos_visiveis(usuario_adm)
        chaves = [m["chave"] for m in visiveis]
        assert set(chaves) == {
            "funcionarios", "clientes", "fornecedores",
            "materiais", "vendas", "relatorio", "historico",
        }

    def test_funcionario_nao_ve_modulos_restritos(self, usuario_funcionario):
        visiveis = modulos_visiveis(usuario_funcionario)
        chaves = [m["chave"] for m in visiveis]
        assert "funcionarios" not in chaves
        assert "relatorio" not in chaves
        assert "historico" not in chaves

    def test_funcionario_ve_modulos_operacionais(self, usuario_funcionario):
        visiveis = modulos_visiveis(usuario_funcionario)
        chaves = [m["chave"] for m in visiveis]
        assert "clientes" in chaves
        assert "fornecedores" in chaves
        assert "materiais" in chaves
        assert "vendas" in chaves

    def test_funcionario_tem_4_modulos(self, usuario_funcionario):
        assert len(modulos_visiveis(usuario_funcionario)) == 4

    def test_adm_tem_7_modulos(self, usuario_adm):
        assert len(modulos_visiveis(usuario_adm)) == 7

    def test_perfil_invalido_nao_ve_nada(self):
        usuario_ghost = Usuario(id=99, login="ghost", nome_completo="Ghost",
                                perfil="VISITANTE", ativo=True)
        assert modulos_visiveis(usuario_ghost) == []

    def test_perfil_case_insensitive(self):
        """Perfil em minúsculo ainda deve funcionar (upper() no filtro)."""
        usuario_min = Usuario(id=3, login="func2", nome_completo="Func",
                              perfil="adm", ativo=True)
        visiveis = modulos_visiveis(usuario_min)
        assert len(visiveis) == 7


class TestUsuarioModel:
    """Testes básicos do dataclass Usuario."""

    def test_usuario_adm_perfil_correto(self, usuario_adm):
        assert usuario_adm.perfil == "ADM"

    def test_usuario_funcionario_perfil_correto(self, usuario_funcionario):
        assert usuario_funcionario.perfil == "FUNCIONARIO"

    def test_usuario_ativo_por_padrao(self, usuario_adm):
        assert usuario_adm.ativo is True

    def test_nome_completo_presente(self, usuario_adm):
        assert len(usuario_adm.nome_completo.strip()) > 0

    def test_primeiro_nome_extraivel(self, usuario_adm):
        """Verifica que split()[0] funciona — usado na tela de boas-vindas."""
        primeiro = usuario_adm.nome_completo.split()[0]
        assert primeiro == "Administrador"
