"""
test_entidade_repo.py — Testes de repositories/entidade_repo.py

Execute:
    pytest tests/test_entidade_repo.py -v
"""

import pytest
from unittest.mock import MagicMock

from repositories.entidade_repo import (
    Contato, Endereco, Entidade, EntidadeRepo
)


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def _row_entidade(id=1, nome="João", cpf="123.456.789-00", cnpj=None,
                  eh_cliente=True, eh_fornecedor=False, ativo=True,
                  data=None, obs=""):
    return (id, nome, cpf, cnpj, eh_cliente, eh_fornecedor, ativo, data, obs)


# ══════════════════════════════════════════════════════
#  MODELO Entidade
# ══════════════════════════════════════════════════════

class TestEntidadeModelo:

    def test_documento_retorna_cpf_quando_disponivel(self):
        e = Entidade(nome="João", cpf="123.456.789-00", eh_cliente=True)
        assert e.documento == "123.456.789-00"

    def test_documento_retorna_cnpj_quando_sem_cpf(self):
        e = Entidade(nome="Empresa", cnpj="12.345.678/0001-99", eh_fornecedor=True)
        assert e.documento == "12.345.678/0001-99"

    def test_documento_retorna_traco_quando_sem_documento(self):
        e = Entidade(nome="Sem doc", eh_cliente=True)
        assert e.documento == "—"

    def test_tipo_pessoa_pf_quando_tem_cpf(self):
        e = Entidade(nome="PF", cpf="111.222.333-44", eh_cliente=True)
        assert e.tipo_pessoa == "PF"

    def test_tipo_pessoa_pj_quando_tem_cnpj(self):
        e = Entidade(nome="PJ", cnpj="00.000.000/0000-00", eh_fornecedor=True)
        assert e.tipo_pessoa == "PJ"

    def test_contato_principal_retorna_principal(self):
        e = Entidade(nome="X", cpf="1", eh_cliente=True, contatos=[
            Contato(tipo="TELEFONE", valor="(11) 1111-1111", principal=False),
            Contato(tipo="CELULAR",  valor="(11) 99999-0000", principal=True),
        ])
        assert "99999-0000" in e.contato_principal

    def test_contato_principal_retorna_primeiro_se_nenhum_marcado(self):
        e = Entidade(nome="X", cpf="1", eh_cliente=True, contatos=[
            Contato(tipo="EMAIL", valor="x@x.com", principal=False),
        ])
        assert "x@x.com" in e.contato_principal

    def test_contato_principal_sem_contatos_retorna_traco(self):
        e = Entidade(nome="X", cpf="1", eh_cliente=True)
        assert e.contato_principal == "—"

    def test_endereco_principal_retorna_principal(self):
        end1 = Endereco(logradouro="Rua A", principal=False)
        end2 = Endereco(logradouro="Rua B", principal=True)
        e = Entidade(nome="X", cpf="1", eh_cliente=True, enderecos=[end1, end2])
        assert e.endereco_principal.logradouro == "Rua B"

    def test_endereco_principal_retorna_primeiro_se_nenhum_marcado(self):
        end = Endereco(logradouro="Rua C", principal=False)
        e = Entidade(nome="X", cpf="1", eh_cliente=True, enderecos=[end])
        assert e.endereco_principal is not None

    def test_endereco_principal_none_sem_enderecos(self):
        e = Entidade(nome="X", cpf="1", eh_cliente=True)
        assert e.endereco_principal is None


# ══════════════════════════════════════════════════════
#  REPOSITÓRIO — INSERIR (validações)
# ══════════════════════════════════════════════════════

class TestInserirEntidade:

    def test_levanta_error_sem_cpf_e_sem_cnpj(self, mock_conn):
        conn, _ = mock_conn
        repo = EntidadeRepo(conn)
        e = Entidade(nome="Sem Doc", eh_cliente=True)

        with pytest.raises(ValueError, match="CPF ou CNPJ"):
            repo.inserir(e)

    def test_levanta_error_nao_e_cliente_nem_fornecedor(self, mock_conn):
        conn, _ = mock_conn
        repo = EntidadeRepo(conn)
        e = Entidade(nome="Nenhum", cpf="000.000.000-00",
                     eh_cliente=False, eh_fornecedor=False)

        with pytest.raises(ValueError, match="[Cc]liente.*[Ff]ornecedor|[Ff]ornecedor.*[Cc]liente"):
            repo.inserir(e)

    def test_inserir_retorna_id(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (10,)
        repo = EntidadeRepo(conn)
        e = Entidade(nome="João", cpf="123.456.789-00", eh_cliente=True)

        id_criado = repo.inserir(e)
        assert id_criado == 10
        conn.commit.assert_called_once()

    def test_inserir_sem_id_levanta_conexao_error(self, mock_conn):
        from database.conexao import ConexaoError
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = EntidadeRepo(conn)
        e = Entidade(nome="João", cpf="123.456.789-00", eh_cliente=True)

        with pytest.raises(ConexaoError):
            repo.inserir(e)
        conn.rollback.assert_called_once()

    def test_inserir_preenche_id_na_entidade(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (99,)
        repo = EntidadeRepo(conn)
        e = Entidade(nome="João", cpf="123.456.789-00", eh_cliente=True)

        repo.inserir(e)
        assert e.id == 99


# ══════════════════════════════════════════════════════
#  REPOSITÓRIO — ATUALIZAR
# ══════════════════════════════════════════════════════

class TestAtualizarEntidade:

    def test_atualizar_sem_id_levanta_value_error(self, mock_conn):
        conn, _ = mock_conn
        repo = EntidadeRepo(conn)
        e = Entidade(nome="X", cpf="1", eh_cliente=True)  # id=None

        with pytest.raises(ValueError, match="sem ID"):
            repo.atualizar(e)

    def test_atualizar_faz_commit(self, mock_conn):
        conn, cursor = mock_conn
        # Para salvar_contatos e salvar_enderecos (sem itens não faz queries adicionais)
        repo = EntidadeRepo(conn)
        e = Entidade(id=1, nome="João", cpf="123.456.789-00", eh_cliente=True)

        repo.atualizar(e)
        conn.commit.assert_called_once()

    def test_atualizar_executa_update_entidade(self, mock_conn):
        conn, cursor = mock_conn
        repo = EntidadeRepo(conn)
        e = Entidade(id=1, nome="João", cpf="123.456.789-00", eh_cliente=True)

        repo.atualizar(e)
        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        assert any("UPDATE Entidade" in s for s in sqls)


# ══════════════════════════════════════════════════════
#  REPOSITÓRIO — DESATIVAR / REATIVAR
# ══════════════════════════════════════════════════════

class TestDesativarReativar:

    def test_desativar_usa_ativo_false(self, mock_conn):
        conn, cursor = mock_conn
        repo = EntidadeRepo(conn)
        repo.desativar(5)

        sql = cursor.execute.call_args[0][0]
        assert "Ativo = FALSE" in sql
        conn.commit.assert_called_once()

    def test_reativar_usa_ativo_true(self, mock_conn):
        conn, cursor = mock_conn
        repo = EntidadeRepo(conn)
        repo.reativar(5)

        sql = cursor.execute.call_args[0][0]
        assert "Ativo = TRUE" in sql
        conn.commit.assert_called_once()


# ══════════════════════════════════════════════════════
#  REPOSITÓRIO — CONSULTAS
# ══════════════════════════════════════════════════════

class TestConsultasEntidade:

    def test_listar_apenas_ativos_usa_filtro(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = EntidadeRepo(conn)
        repo.listar(apenas_ativos=True)

        sql = cursor.execute.call_args[0][0]
        assert "Ativo = TRUE" in sql

    def test_listar_apenas_clientes_usa_filtro(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = EntidadeRepo(conn)
        repo.listar(apenas_clientes=True)

        sql = cursor.execute.call_args[0][0]
        assert "EhCliente = TRUE" in sql

    def test_listar_apenas_fornecedores_usa_filtro(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = EntidadeRepo(conn)
        repo.listar(apenas_fornecedores=True)

        sql = cursor.execute.call_args[0][0]
        assert "EhFornecedor = TRUE" in sql

    def test_buscar_por_id_retorna_none_quando_nao_encontrado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = []
        repo = EntidadeRepo(conn)

        resultado = repo.buscar_por_id(999)
        assert resultado is None

    def test_buscar_por_nome_usa_like(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        repo = EntidadeRepo(conn)
        repo.buscar_por_nome("João")

        params = cursor.execute.call_args[0][1]
        assert "%João%" in params

    def test_documento_existe_verifica_cpf(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (1,)
        repo = EntidadeRepo(conn)

        assert repo.documento_existe(cpf="123.456.789-00", cnpj=None) is True

    def test_documento_existe_false_quando_nao_encontrado(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = EntidadeRepo(conn)

        assert repo.documento_existe(cpf="000.000.000-00", cnpj=None) is False

    def test_documento_existe_ignorar_proprio_id(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        repo = EntidadeRepo(conn)
        repo.documento_existe(cpf="123.456.789-00", cnpj=None, ignorar_id=5)

        sql = cursor.execute.call_args[0][0]
        assert "IDEntidade <>" in sql


# ══════════════════════════════════════════════════════
#  CONTATOS
# ══════════════════════════════════════════════════════

class TestSalvarContatos:

    def test_deleta_contatos_antes_de_inserir(self, mock_conn):
        conn, cursor = mock_conn
        repo = EntidadeRepo(conn)
        contatos = [Contato(tipo="EMAIL", valor="x@x.com")]
        repo.salvar_contatos(1, contatos)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        assert any("DELETE FROM Contato" in s for s in sqls)

    def test_ignora_contatos_com_valor_vazio(self, mock_conn):
        conn, cursor = mock_conn
        repo = EntidadeRepo(conn)
        contatos = [Contato(tipo="EMAIL", valor="   ")]  # só espaços
        repo.salvar_contatos(1, contatos)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        inserts = [s for s in sqls if "INSERT INTO Contato" in s]
        assert len(inserts) == 0

    def test_insere_contato_valido(self, mock_conn):
        conn, cursor = mock_conn
        repo = EntidadeRepo(conn)
        contatos = [Contato(tipo="CELULAR", valor="(11) 99999-0000")]
        repo.salvar_contatos(1, contatos)

        sqls = [c[0][0] for c in cursor.execute.call_args_list]
        inserts = [s for s in sqls if "INSERT INTO Contato" in s]
        assert len(inserts) == 1
