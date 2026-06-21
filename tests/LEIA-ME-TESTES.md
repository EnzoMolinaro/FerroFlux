# Guia de Testes — FerroFlux

## Estrutura Completa

```
seu_projeto/
│
├── pytest.ini
└── tests/
    ├── conftest.py                  ← fixtures: mock_conn, db_connection, exemplos
    ├── test_seguranca.py            ← hash_senha, senha_valida, login_valido
    ├── test_conexao.py              ← ConfigConexao, string ODBC, testar_conexao
    ├── test_material_repo.py        ← MaterialRepo completo
    ├── test_usuario_repo.py         ← usuario_repo (funções e helpers)
    ├── test_venda_repo.py           ← VendaRepo, ItemPedido, status de pedido
    ├── test_entidade_repo.py        ← EntidadeRepo, Entidade, Contato
    ├── test_relatorio_repo.py       ← RelatorioRepo, KPIs, séries, tops
    ├── test_componentes.py          ← Tema, CampoData._parse, BarraStatus
    └── test_menu.py                 ← permissões ADM/FUNCIONARIO
```

---

## Instalação

```bash
pip install pytest
# pyodbc e customtkinter já devem estar instalados no projeto
```

---

## Configuração (banco real)

```sql
CREATE DATABASE ferroflux_test;
-- Execute aqui os mesmos scripts SQL do banco de produção
```

Ajuste em `tests/conftest.py`:

```python
CONFIG_TESTE = ConfigConexao(
    servidor="localhost",
    porta=3307,
    usuario="root",
    senha="",           # sua senha
    banco="ferroflux_test",
)
```

> ⚠️ **Nunca aponte para o banco `ferroflux` (produção).**
> O fixture `db_cursor` faz rollback automático após cada teste.

---

## Como Executar

```bash
# Todos os testes
pytest

# Só unitários — rodam sem banco, imediatamente
pytest tests/test_seguranca.py tests/test_conexao.py tests/test_menu.py
pytest tests/test_venda_repo.py tests/test_entidade_repo.py
pytest tests/test_relatorio_repo.py tests/test_componentes.py
pytest tests/test_material_repo.py::TestMaterialRepoUnitario
pytest tests/test_usuario_repo.py

# Só testes com banco real
pytest tests/test_material_repo.py::TestMaterialRepoBanco -v

# Um arquivo específico
pytest tests/test_venda_repo.py -v

# Filtrando por nome de classe ou método
pytest -k "TestItemPedido" -v
pytest -k "status" -v
```

---

## Resumo dos Testes por Arquivo

### `test_seguranca.py` — 11 testes, 100% unitários
- SHA-256: 64 chars, determinístico, não expõe senha
- `senha_valida`: mínimo 6 chars
- `login_valido`: 3–30 chars, só `\w`, rejeita espaço/arroba/hífen

### `test_conexao.py` — 12 testes, 100% unitários
- `ConfigConexao.__str__` não exibe senha
- Connection string ODBC: driver, servidor, porta, charset
- `_detectar_driver`: cache, sem driver disponível
- `testar_conexao`: retorna (True, versão) ou (False, msg)

### `test_material_repo.py` — 24 testes (18 unit + 6 banco)
- `listar_todos`, `buscar_por_id`, `buscar_por_nome`
- `inserir`: 3 INSERTs + commit, `ConexaoError` sem ID
- `atualizar`: histórico de preço só quando muda
- `desativar`/`reativar`, `ajustar_estoque`

### `test_usuario_repo.py` — 22 testes, 100% unitários
- `_row_para_usuario`: conversão de linha para dataclass
- `_perfil_id`: encontrado / não encontrado
- `buscar_por_login_e_senha`: autenticação, filtro `Ativo = 1`
- `login_existe`: com e sem `exceto_id`
- `cadastrar`: INSERTs em Usuario + UsuarioPerfil, `ConexaoError`
- `atualizar`: com/sem senha, substitui perfil (DELETE + INSERT)
- `desativar`/`reativar`/`redefinir_senha`

### `test_venda_repo.py` — 30 testes, 100% unitários
- `ItemPedido.__post_init__`: subtotal, arredondamento
- `STATUS_PEDIDO` e `STATUS_AVANCAR`: todos os fluxos
- `estoque_disponivel`, `validar_estoque_pedido`
- `criar_pedido`: status PENDENTE, `ConexaoError`
- `salvar_itens`: DELETE + INSERT + UPDATE ValorTotal
- `confirmar_pedido`: sem itens, estoque insuficiente, MovimentacaoEstoque
- `cancelar_pedido`: ENTREGUE bloqueado, estorno de estoque
- `avancar_status`: cada transição e erros
- `emitir_nota_fiscal`: PENDENTE/CANCELADO bloqueados, status EMITIDA

### `test_entidade_repo.py` — 26 testes, 100% unitários
- Properties de `Entidade`: `documento`, `tipo_pessoa`, `contato_principal`
- `inserir`: sem CPF/CNPJ, sem cliente/fornecedor, `ConexaoError`
- `atualizar`: sem ID, UPDATE + commit
- `listar`: filtros cliente/fornecedor/ativo
- `buscar_por_nome`: parâmetro LIKE
- `documento_existe`: CPF, CNPJ, `ignorar_id`
- `salvar_contatos`: DELETE + INSERT, ignora valor vazio

### `test_relatorio_repo.py` — 28 testes, 100% unitários
- `_MESES_PT`: 12 meses, Jan e Dez
- `ResumoFinanceiro`: margem e ticket com divisão por zero
- `_f` e `_i`: default quando None
- `_filtro_periodo`: sem datas, só início, só fim, ambas
- `resumo()`: KPIs, lucro, margem, ticket
- `faturamento_mensal()`: label, lucro por mês, `ultimos_n_meses`
- `top_clientes()` e `top_produtos()`: dados e `limite`
- `detalhe_pedidos()`: linhas e lucro por linha

### `test_componentes.py` — 27 testes, 100% unitários
- `Tema`: cores hex, tamanhos positivos, H1 > H2 > H3
- `CampoData._parse`: válidas, inválidas, bissexto, espaços
- `_ESTILOS_BOTAO`: 5 variantes, 3 cores cada, hover ≠ bg
- `BarraStatus`: prefixos ✓/✕, cores por tipo, limpar

### `test_menu.py` — 9 testes, 100% unitários
- ADM vê 7 módulos, FUNCIONARIO vê 4
- Módulos restritos bloqueados para FUNCIONARIO
- Perfil inválido vê 0 módulos

---

## Total: ~189 testes | ~181 unitários | ~8 com banco real
