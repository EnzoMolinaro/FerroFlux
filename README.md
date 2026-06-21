# ⚙️ FerroFlux

> Sistema de gerenciamento de estoque para ferros-velhos de pequeno e médio porte

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Concluído-brightgreen?style=flat-square)

O FerroFlux substitui processos manuais por uma plataforma digital intuitiva que centraliza o controle de materiais recicláveis — desenvolvido como projeto de extensão universitária em parceria com a **Seiti Sucatas**.

---

## Funcionalidades

| Módulo | Descrição |
|---|---|
| **Gestão de produtos** | Cadastro, consulta, edição e exclusão de itens no estoque |
| **Estoque em tempo real** | Controle automático de entradas e saídas de materiais |
| **Consulta e filtragem** | Busca por nome, código ou categoria com filtros dinâmicos |
| **Registro de movimentações** | Log completo com data, hora e usuário responsável |
| **Gerenciamento de usuários** | Controle de acesso por perfil (administrador e operador) |
| **Faturamento** | Consulta de faturamento com acesso restrito ao administrador |
| **Nota Fiscal Paulista** | Geração e armazenamento de NF-e integrado ao sistema |
| **Cadastro de clientes** | Armazenamento de contatos e destino de entrega |

---

## Pré-requisitos e instalação

O FerroFlux é uma aplicação **desktop com banco de dados local**. O banco de dados roda diretamente no computador do cliente e requer configuração prévia — a instalação é feita de forma assistida pela equipe.

### Dependências obrigatórias

| Requisito | Versão | Observação |
|---|---|---|
| Windows | 10 ou superior | Sistema operacional |
| SQL Server / SQL Server Express | 2019+ | Banco de dados local — gratuito na versão Express |
| ODBC Driver for SQL Server | 17 ou 18 | Driver de conexão ([baixar aqui](https://learn.microsoft.com/pt-br/sql/connect/odbc/download-odbc-driver-for-sql-server)) |

> **Por que essa dependência?** O FerroFlux usa `pyodbc` para conectar ao SQL Server, que oferece robustez e segurança para dados de negócio. O SQL Server Express é gratuito e suficiente para o porte de um ferro-velho de pequeno/médio porte.

### Windows — executável (recomendado)

1. Instale o **SQL Server Express** e o **ODBC Driver 17+** (links acima)
2. Configure o banco de dados conforme o guia [`docs/INSTALL.md`](docs/INSTALL.md)
3. Acesse a seção [**Releases**](../../releases) deste repositório
4. Baixe e execute `FerroFlux.exe`

### A partir do código-fonte

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/ferroflux.git
cd ferroflux

# Instale as dependências Python
pip install -r requirements.txt
# customtkinter==5.2.2 · darkdetect==0.8.0 · pyodbc==5.3.0

# Configure a string de conexão no banco
# (veja docs/INSTALL.md para criar o banco e as tabelas)

# Execute a aplicação
python telas/login.py
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.x |
| Interface gráfica | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) 5.2.2 |
| Banco de dados | SQL Server / SQL Server Express |
| Driver de banco | pyodbc 5.3.0 |
| Detecção de tema | darkdetect 0.8.0 |
| Distribuição | PyInstaller — `.exe` com ícone e atalho na área de trabalho |
| Plataforma principal | Windows 10+ |

---

## Contexto do projeto

Desenvolvido ao longo de um curso de graduação como **projeto de extensão universitária**, o FerroFlux nasceu de uma entrevista com o proprietário da Seiti Sucatas, que relatou dificuldades no controle de estoque pela falta de integração entre suas ferramentas.

O sistema une tecnologia, organização de processos e sustentabilidade — propósito central das práticas extensionistas. A parceria com um negócio real permitiu que os requisitos fossem levantados diretamente com o usuário final, resultando em um produto alinhado às necessidades do mercado.

---

## Requisitos não funcionais

- **Compatibilidade:** Windows, Linux e macOS
- **Desempenho:** tempo de resposta inferior a 2 segundos em 95% das operações
- **Segurança:** autenticação por login e senha com controle de acesso por perfil
- **Portabilidade:** instalação via executável ou scripts automatizados
- **Usabilidade:** interface acessível voltada a usuários sem perfil técnico

---

## Equipe

Projeto desenvolvido por:

- [Nome do integrante 1]
- [Nome do integrante 2]
- [Nome do integrante 3]
- *(adicione os demais)*

Curso: [Nome do Curso] · [Nome da Faculdade] · [Ano de conclusão]

Orientação: Profª Claudia [Sobrenome]

---

## Licença

Distribuído sob a licença **MIT**. Veja o arquivo [`LICENSE`](LICENSE) para mais informações.

---

> *"O projeto FerroFlux aborda uma necessidade real do mercado e apresenta uma proposta relevante, unindo tecnologia, organização de processos e sustentabilidade."*
> — Profª Claudia, orientadora do projeto
