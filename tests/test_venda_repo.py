"""
test_venda_repo.py — Testes de repositories/venda_repo.py

Execute:
    pytest tests/test_venda_repo.py -v
"""

import pytest
from unittest.mock import MagicMock, call

from repositories.venda_repo import (
    ItemPedido, Pedido, VendaRepo, STATUS_PEDIDO, STATUS_AVANCAR
)


# ══════════════════════════════════════════════════════
#  TESTES DE MODELOS (sem banco)
# ══════════════════════════════════════════════════════

class TestItemPedido:
    """Testa o dataclass ItemPedido e seu __post_init__."""

    def test_subtotal_calculado_automaticamente(self):
        item = ItemPedido(id_produto=1, nome_produto="Ferro",
                          unidade="KG", quantidade=10.0, preco_unitario=2.50)
        assert item.subtotal == 25.00

    def test_subtotal_arredondado_2_casas(self):
        item = ItemPedido(id_produto=1, nome_produto="Alumínio",
                          unidade="KG", quantidade=7.3, preco_unitario=1.80)
        assert item.subtotal == 13.14

    def test_subtotal_zero_quando_quantidade_zero(self):
        item = ItemPedido(id_produto=1, nome_produto="X",
                          unidade="KG", quantidade=0.0, preco_unitario=5.00)
        assert item.subtotal == 0.0

    def test_subtotal_fracionado_grande(self):
        item = ItemPedido(id_produto=2, nome_produto="Cobre",
                          unidade="KG", quantidade=33.333, preco_unitario=45.00)
        assert item.subtotal == round(33.333 * 45.00, 2)


class TestStatusPedido:
    """Testa as constantes de status e o mapeamento de avanço."""

    def test_status_validos_definidos(self):
        esperados = {"PENDENTE", "CONFIRMADO", "PREPARANDO",
                     "ENVIADO", "ENTREGUE", "CANCELADO"}
        assert set(STATUS_PEDIDO) == esperados

    def test_confirmado_avanca_para_preparando(self):
        assert STATUS_AVANCAR["CONFIRMADO"] == "PREPARANDO"

    def test_preparando_avanca_para_enviado(self):
        assert STATUS_AVANCAR["PREPARANDO"] == "ENVIADO"

    def test_enviado_avanca_para_entregue(self):
        assert STATUS_AVANCAR["ENVIADO"] == "ENTREGUE"

    def test_pendente_nao_pode_avancar(self):
        assert "PENDENTE" not in STATUS_AVANCAR

    def test_cancelado_nao_pode_avancar(self):
        assert "CANCELADO" not in STATUS_AVANCAR

    def test_entregue_nao_pode_avancar(self):
        assert "ENTREGUE" not in STATUS_AVANCAR


# ══════════════════════════════════════════════════════
#  TESTES DO REPOSITÓRIO (mock)
# ══════════════════════════════════════════════════════

def _item(id_prod=1, nome="Ferro", qtd=10.0, preco=2.50, unidade="KG"):
    return ItemPedido(id_produto=id_prod, nome_produto=nome,
                      unidade=unidade, quantidade=qtd, preco_unitario=preco)


class TestEstoqueDisponivel:

    def test_retorna_quantidade_do_banco(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (75.5,)
        repo = VendaRepo(conn)
        assert repo.estoque_disponivel(1) == 75.5

    def test_retorna_zero_quando_produto_nao_tem_estoque(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = VendaRepo(conn)
        assert repo.estoque_disponivel(99) == 0.0


class TestValidarEstoquePedido:

    def test_sem_erros_quando_estoque_suficiente(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (50.0,)
        repo = VendaRepo(conn)
        erros = repo.validar_estoque_pedido([_item(qtd=10.0)])
        assert erros == []

    def test_erro_quando_estoque_insuficiente(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (5.0,)  # só 5 kg disponíveis
        repo = VendaRepo(conn)
        erros = repo.validar_estoque_pedido([_item(qtd=10.0)])
        assert len(erros) == 1
        assert "insuficiente" in erros[0].lower()

    def test_varios_itens_multiplos_erros(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [(2.0,), (1.0,)]  # ambos insuficientes
        repo = VendaRepo(conn)
        itens = [_item(id_prod=1, qtd=10.0), _item(id_prod=2, qtd=10.0)]
        erros = repo.validar_estoque_pedido(itens)
        assert len(erros) == 2

    def test_sem_itens_retorna_lista_vazia(self, mock_conn):
        conn, cursor = mock_conn
        repo = VendaRepo(conn)
        assert repo.validar_estoque_pedido([]) == []


class TestCriarPedido:

    def test_retorna_id_do_pedido(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (42,)
        repo = VendaRepo(conn)
        id_pedido = repo.criar_pedido(id_cliente=1)
        assert id_pedido == 42
        conn.commit.assert_called_once()

    def test_status_inicial_pendente(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (1,)
        repo = VendaRepo(conn)
        repo.criar_pedido(id_cliente=1)

        sql_insert = cursor.execute.call_args_list[0][0][0]
        assert "PENDENTE" in sql_insert

    def test_levanta_conexao_error_sem_id(self, mock_conn):
        from database.conexao import ConexaoError
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = VendaRepo(conn)

        with pytest.raises(ConexaoError):
            repo.criar_pedido(id_cliente=1)
        conn.rollback.assert_called_once()


class TestSalvarItens:

    def test_deleta_itens_anteriores_antes_de_inserir(self, mock_conn):
        conn, cursor = mock_conn
        repo = VendaRepo(conn)
        repo.salvar_itens(5, [_item()])

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        assert any("DELETE FROM ItemPedido" in s for s in sqls)

    def test_insere_cada_item(self, mock_conn):
        conn, cursor = mock_conn
        repo = VendaRepo(conn)
        itens = [_item(id_prod=1), _item(id_prod=2)]
        repo.salvar_itens(5, itens)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        inserts = [s for s in sqls if "INSERT INTO ItemPedido" in s]
        assert len(inserts) == 2

    def test_atualiza_valor_total_do_pedido(self, mock_conn):
        conn, cursor = mock_conn
        repo = VendaRepo(conn)
        repo.salvar_itens(5, [_item()])

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        assert any("UPDATE Pedido" in s and "ValorTotal" in s for s in sqls)

    def test_commit_ao_final(self, mock_conn):
        conn, cursor = mock_conn
        repo = VendaRepo(conn)
        repo.salvar_itens(5, [_item()])
        conn.commit.assert_called_once()


class TestConfirmarPedido:

    def test_levanta_error_sem_itens(self, mock_conn):
        conn, cursor = mock_conn
        # listar_itens retorna lista vazia
        cursor.fetchall.return_value = []
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="itens"):
            repo.confirmar_pedido(id_pedido=1, id_usuario=1)

    def test_levanta_error_estoque_insuficiente(self, mock_conn):
        conn, cursor = mock_conn
        # listar_itens retorna 1 item
        cursor.fetchall.return_value = [
            (1, 1, "Ferro", "KG", 50.0, 2.50, 125.0)
        ]
        # estoque_disponivel retorna 5 (insuficiente)
        cursor.fetchone.return_value = (5.0,)
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="[Ee]stoque"):
            repo.confirmar_pedido(id_pedido=1, id_usuario=1)

    def test_confirmar_atualiza_status_para_confirmado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [
            (1, 1, "Ferro", "KG", 10.0, 2.50, 25.0)
        ]
        cursor.fetchone.return_value = (100.0,)  # estoque suficiente
        repo = VendaRepo(conn)
        repo.confirmar_pedido(id_pedido=1, id_usuario=1)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        update_status = [s for s in sqls if "UPDATE Pedido" in s and "CONFIRMADO" in s]
        assert len(update_status) == 1

    def test_confirmar_insere_movimentacao_saida(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [
            (1, 1, "Ferro", "KG", 10.0, 2.50, 25.0)
        ]
        cursor.fetchone.return_value = (100.0,)
        repo = VendaRepo(conn)
        repo.confirmar_pedido(id_pedido=1, id_usuario=1)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        assert any("MovimentacaoEstoque" in s and "SAIDA" in s for s in sqls)


class TestCancelarPedido:

    def test_levanta_error_pedido_nao_encontrado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="[Nn]ão encontrado"):
            repo.cancelar_pedido(id_pedido=99, id_usuario=1)

    def test_levanta_error_pedido_entregue(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("ENTREGUE",)
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="[Ee]ntreg"):
            repo.cancelar_pedido(id_pedido=1, id_usuario=1)

    def test_cancelar_pendente_nao_estorna_estoque(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("PENDENTE",)
        cursor.fetchall.return_value = []
        repo = VendaRepo(conn)
        repo.cancelar_pedido(id_pedido=1, id_usuario=1)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        assert not any("MovimentacaoEstoque" in s for s in sqls)

    def test_cancelar_confirmado_estorna_estoque(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("CONFIRMADO",)
        cursor.fetchall.return_value = [
            (1, 1, "Ferro", "KG", 10.0, 2.50, 25.0)
        ]
        repo = VendaRepo(conn)
        repo.cancelar_pedido(id_pedido=1, id_usuario=1)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        assert any("MovimentacaoEstoque" in s and "ENTRADA" in s for s in sqls)


class TestAvancarStatus:

    def test_levanta_error_pedido_nao_encontrado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="[Nn]ão encontrado"):
            repo.avancar_status(99)

    def test_levanta_error_status_nao_avancavel(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("PENDENTE",)
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="PENDENTE"):
            repo.avancar_status(1)

    def test_retorna_novo_status(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("CONFIRMADO",)
        repo = VendaRepo(conn)

        novo = repo.avancar_status(1)
        assert novo == "PREPARANDO"

    def test_avancar_de_preparando_para_enviado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("PREPARANDO",)
        repo = VendaRepo(conn)

        novo = repo.avancar_status(1)
        assert novo == "ENVIADO"


class TestEmitirNotaFiscal:

    def test_levanta_error_pedido_nao_encontrado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="[Nn]ão encontrado"):
            repo.emitir_nota_fiscal(99, 1, 2)

    def test_levanta_error_pedido_pendente(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("PENDENTE", 100.0)
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="PENDENTE"):
            repo.emitir_nota_fiscal(1, 1, 2)

    def test_levanta_error_pedido_cancelado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("CANCELADO", 0.0)
        repo = VendaRepo(conn)

        with pytest.raises(ValueError, match="CANCELADO"):
            repo.emitir_nota_fiscal(1, 1, 2)

    def test_retorna_id_nota_emitida(self, mock_conn):
        conn, cursor = mock_conn
        # SELECT Status: CONFIRMADO; SELECT LAST_INSERT_ID: 7
        cursor.fetchone.side_effect = [("CONFIRMADO", 250.0), (7,)]
        repo = VendaRepo(conn)

        id_nota = repo.emitir_nota_fiscal(1, 1, 2)
        assert id_nota == 7
        conn.commit.assert_called_once()

    def test_nota_emitida_com_status_emitida(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [("CONFIRMADO", 250.0), (1,)]
        repo = VendaRepo(conn)
        repo.emitir_nota_fiscal(1, 1, 2)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        insert_nf = [s for s in sqls if "INSERT INTO NotaFiscal" in s]
        assert len(insert_nf) == 1
        assert "EMITIDA" in insert_nf[0]
