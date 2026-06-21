# Guia de instalação — FerroFlux

Este guia descreve como configurar o ambiente completo para rodar o FerroFlux,
incluindo o banco de dados SQL Server e o driver de conexão ODBC.

---

## 1. Instalar o SQL Server Express (gratuito)

O FerroFlux usa SQL Server como banco de dados local. A versão Express é
gratuita e suficiente para uso em ferros-velhos de pequeno e médio porte.

1. Acesse: https://www.microsoft.com/pt-br/sql-server/sql-server-downloads
2. Baixe o **SQL Server Express**
3. Execute o instalador e escolha a opção **Básica**
4. Anote o nome da instância criada (ex: `SQLEXPRESS`)

---

## 2. Instalar o ODBC Driver for SQL Server

O `pyodbc` precisa deste driver para se conectar ao banco.

1. Acesse: https://learn.microsoft.com/pt-br/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Baixe o **ODBC Driver 17** (ou 18) para Windows
3. Execute o instalador padrão (Next > Next > Finish)

Para verificar se foi instalado corretamente, abra o **Gerenciador de Fonte de Dados ODBC**
(pesquise "ODBC" no menu Iniciar) e confirme que o driver aparece na aba "Drivers".

---

## 3. Criar o banco de dados

Abra o **SQL Server Management Studio (SSMS)** — disponível gratuitamente em:
https://learn.microsoft.com/pt-br/sql/ssms/download-sql-server-management-studio-ssms

Conecte-se à instância local e execute:

```sql
CREATE DATABASE FerroFlux;
```

Em seguida, execute o script de criação das tabelas:

```bash
# Via linha de comando (ajuste o nome da instância)
sqlcmd -S .\SQLEXPRESS -d FerroFlux -i docs\schema.sql
```

Ou abra o arquivo `docs/schema.sql` no SSMS e execute (F5).

---

## 4. Configurar a string de conexão

Localize o arquivo de configuração do projeto:

```
database/conexao.py
```

Edite a string de conexão com os dados da sua instância:

```python
# Exemplo para SQL Server Express com autenticação Windows
CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=.\\SQLEXPRESS;"   # ou o nome do seu servidor
    "DATABASE=FerroFlux;"
    "Trusted_Connection=yes;"
)

# Exemplo com usuário e senha (autenticação SQL)
CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=.\\SQLEXPRESS;"
    "DATABASE=FerroFlux;"
    "UID=seu_usuario;"
    "PWD=sua_senha;"
)
```

---

## 5. Executar o projeto

### Via executável (usuário final)

Após configurar o banco de dados, basta executar `FerroFlux.exe`.
O aplicativo abre a tela de login diretamente.

### Via código-fonte (desenvolvedor)

```bash
pip install -r requirements.txt
python telas/login.py
```

---

## Solução de problemas comuns

**Erro: `pyodbc.InterfaceError: ('IM002', ...)`**
→ O ODBC Driver não está instalado ou o nome do driver na string de conexão está incorreto.
→ Verifique os drivers disponíveis com:
```python
import pyodbc
print(pyodbc.drivers())
```

**Erro: `Login failed for user`**
→ Verifique as credenciais na string de conexão.
→ Se usar autenticação Windows, confirme que `Trusted_Connection=yes` está definido.

**Erro: `Cannot open database "FerroFlux"`**
→ O banco não foi criado. Execute o passo 3 deste guia.

**O executável abre e fecha imediatamente**
→ Problema de conexão com o banco. Execute via código-fonte para ver o erro completo:
```bash
python telas/login.py
```

---

## Requisitos mínimos do sistema

| Componente | Requisito |
|---|---|
| Sistema operacional | Windows 10 ou superior |
| RAM | 4 GB (recomendado 8 GB) |
| Espaço em disco | ~500 MB (SQL Server Express + aplicativo) |
| SQL Server | Express 2019 ou superior |
| ODBC Driver | 17 ou 18 |
