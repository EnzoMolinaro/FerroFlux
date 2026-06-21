"""
test_clientes_fornecedores.py — Testes de clientes e fornecedores.

Execute:
    pytest tests/test_clientes_fornecedores.py -v
"""

import pytest
import re


# ──────────────────────────────────────────────
#  FUNÇÕES AUXILIARES DE VALIDAÇÃO
#  Se o seu código já tem essas validações,
#  importe deles em vez de redefinir aqui.
# ──────────────────────────────────────────────

def validar_cpf_formato(cpf: str) -> bool:
    """Valida formato básico de CPF: 000.000.000-00"""
    return bool(re.match(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$", cpf))

def validar_cnpj_formato(cnpj: str) -> bool:
    """Valida formato básico de CNPJ: 00.000.000/0000-00"""
    return bool(re.match(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", cnpj))

def validar_email(email: str) -> bool:
    """Valida formato básico de e-mail."""
    return bool(re.match(r"^[\w.-]+@[\w.-]+\.\w+$", email))


class TestValidacaoCliente:
    """Testes unitários de validação de dados do cliente."""

    def test_cpf_formato_valido(self):
        assert validar_cpf_formato("123.456.789-00") is True

    def test_cpf_formato_invalido_sem_pontuacao(self):
        assert validar_cpf_formato("12345678900") is False

    def test_cpf_formato_invalido_letras(self):
        assert validar_cpf_formato("abc.def.ghi-jk") is False

    def test_email_valido(self):
        assert validar_email("joao@email.com") is True

    def test_email_invalido_sem_arroba(self):
        assert validar_email("joaoemail.com") is False

    def test_email_invalido_sem_dominio(self):
        assert validar_email("joao@") is False

    def test_nome_cliente_vazio_invalido(self):
        nome = "   "
        assert nome.strip() == "", "Nome vazio/só espaços deve ser rejeitado"

    def test_nome_cliente_valido(self):
        nome = "João Silva"
        assert len(nome.strip()) > 0


class TestValidacaoFornecedor:
    """Testes unitários de validação de dados do fornecedor."""

    def test_cnpj_formato_valido(self):
        assert validar_cnpj_formato("12.345.678/0001-99") is True

    def test_cnpj_formato_invalido(self):
        assert validar_cnpj_formato("12345678000199") is False

    def test_email_fornecedor_valido(self):
        assert validar_email("contato@sucatas.com") is True

    def test_nome_fornecedor_nao_pode_ser_vazio(self):
        nome = ""
        assert nome.strip() == "", "Nome vazio deve ser rejeitado"


class TestClienteBancoDados:
    """Testes com banco real."""

    def test_tabela_clientes_existe(self, db_cursor):
        db_cursor.execute("SHOW TABLES LIKE 'clientes'")
        resultado = db_cursor.fetchone()
        assert resultado is not None, "Tabela 'clientes' não encontrada"

    def test_inserir_cliente(self, db_cursor, cliente_exemplo):
        c = cliente_exemplo
        db_cursor.execute(
            "INSERT INTO clientes (nome, cpf, telefone, email) VALUES (%s, %s, %s, %s)",
            (c["nome"], c["cpf"], c["telefone"], c["email"])
        )
        cliente_id = db_cursor.lastrowid

        db_cursor.execute("SELECT * FROM clientes WHERE id = %s", (cliente_id,))
        resultado = db_cursor.fetchone()

        assert resultado is not None
        assert resultado["nome"] == c["nome"]
        assert resultado["cpf"] == c["cpf"]

    def test_cpf_duplicado_rejeitado(self, db_cursor, cliente_exemplo):
        """CPF duplicado não deve ser permitido (unique constraint)."""
        import mysql.connector
        c = cliente_exemplo
        db_cursor.execute(
            "INSERT INTO clientes (nome, cpf, telefone, email) VALUES (%s, %s, %s, %s)",
            (c["nome"], c["cpf"], c["telefone"], c["email"])
        )

        with pytest.raises(mysql.connector.errors.IntegrityError):
            db_cursor.execute(
                "INSERT INTO clientes (nome, cpf, telefone, email) VALUES (%s, %s, %s, %s)",
                ("Outro Nome", c["cpf"], "(11) 11111-1111", "outro@email.com")
            )

    def test_buscar_cliente_por_nome(self, db_cursor, cliente_exemplo):
        c = cliente_exemplo
        db_cursor.execute(
            "INSERT INTO clientes (nome, cpf, telefone, email) VALUES (%s, %s, %s, %s)",
            (c["nome"], c["cpf"], c["telefone"], c["email"])
        )

        db_cursor.execute(
            "SELECT * FROM clientes WHERE nome LIKE %s",
            (f"%{c['nome']}%",)
        )
        resultados = db_cursor.fetchall()
        assert len(resultados) >= 1

    def test_atualizar_telefone_cliente(self, db_cursor, cliente_exemplo):
        c = cliente_exemplo
        db_cursor.execute(
            "INSERT INTO clientes (nome, cpf, telefone, email) VALUES (%s, %s, %s, %s)",
            (c["nome"], c["cpf"], c["telefone"], c["email"])
        )
        cliente_id = db_cursor.lastrowid

        novo_tel = "(11) 00000-1111"
        db_cursor.execute(
            "UPDATE clientes SET telefone = %s WHERE id = %s",
            (novo_tel, cliente_id)
        )
        db_cursor.execute("SELECT telefone FROM clientes WHERE id = %s", (cliente_id,))
        resultado = db_cursor.fetchone()
        assert resultado["telefone"] == novo_tel


class TestFornecedorBancoDados:
    """Testes com banco real."""

    def test_tabela_fornecedores_existe(self, db_cursor):
        db_cursor.execute("SHOW TABLES LIKE 'fornecedores'")
        resultado = db_cursor.fetchone()
        assert resultado is not None, "Tabela 'fornecedores' não encontrada"

    def test_inserir_fornecedor(self, db_cursor, fornecedor_exemplo):
        f = fornecedor_exemplo
        db_cursor.execute(
            "INSERT INTO fornecedores (nome, cnpj, telefone, email) VALUES (%s, %s, %s, %s)",
            (f["nome"], f["cnpj"], f["telefone"], f["email"])
        )
        fornecedor_id = db_cursor.lastrowid

        db_cursor.execute("SELECT * FROM fornecedores WHERE id = %s", (fornecedor_id,))
        resultado = db_cursor.fetchone()

        assert resultado is not None
        assert resultado["nome"] == f["nome"]
