CREATE DATABASE FerroFlux;
USE FerroFlux;

CREATE TABLE ConexoesBancoDeDados (
    IDConexoesBancoDeDados INT AUTO_INCREMENT PRIMARY KEY,
    Servidor VARCHAR(100) NOT NULL,
    Porta VARCHAR(50) NOT NULL,
    Usuario VARCHAR(50) NOT NULL,
    Senha VARCHAR(50) NOT NULL,
    BancoDeDados VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE Cidade (
    IDCidade INT AUTO_INCREMENT PRIMARY KEY,
    Nome VARCHAR(100) NOT NULL,
    Estado VARCHAR(50) NOT NULL,
    UNIQUE (Nome, Estado)
) ENGINE=InnoDB;

CREATE TABLE Bairro (
    IDBairro INT AUTO_INCREMENT PRIMARY KEY,
    Nome VARCHAR(100) NOT NULL,
    IDCidade INT NOT NULL,
    FOREIGN KEY (IDCidade) REFERENCES Cidade(IDCidade) ON DELETE CASCADE,
    UNIQUE (Nome, IDCidade)
) ENGINE=InnoDB;

CREATE TABLE EnderecoBase (
    IDEndereco INT AUTO_INCREMENT PRIMARY KEY,
    Logradouro VARCHAR(255) NOT NULL,
    Numero VARCHAR(20),
    Complemento VARCHAR(100),
    CEP VARCHAR(10),
    IDBairro INT NOT NULL,
    FOREIGN KEY (IDBairro) REFERENCES Bairro(IDBairro) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE Entidade (
    IDEntidade INT AUTO_INCREMENT PRIMARY KEY,
    Nome VARCHAR(255) NOT NULL,
    CPF VARCHAR(14) NULL UNIQUE,
    CNPJ VARCHAR(18) NULL UNIQUE,
    EhCliente BOOLEAN DEFAULT FALSE,
    EhFornecedor BOOLEAN DEFAULT FALSE,
    Ativo BOOLEAN DEFAULT TRUE,
    DataCriacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    Observacoes TEXT,
    CHECK (CPF IS NOT NULL OR CNPJ IS NOT NULL),
    CHECK (EhCliente = TRUE OR EhFornecedor = TRUE)
) ENGINE=InnoDB;

CREATE TABLE EntidadeEndereco (
    IDEntidadeEndereco INT AUTO_INCREMENT PRIMARY KEY,
    IDEntidade INT NOT NULL,
    IDEndereco INT NOT NULL,
    TipoEndereco ENUM('RESIDENCIAL', 'COMERCIAL', 'ENTREGA', 'COBRANCA') DEFAULT 'COMERCIAL',
    Principal BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (IDEntidade) REFERENCES Entidade(IDEntidade) ON DELETE CASCADE,
    FOREIGN KEY (IDEndereco) REFERENCES EnderecoBase(IDEndereco) ON DELETE CASCADE,
    UNIQUE (IDEntidade, IDEndereco, TipoEndereco)
) ENGINE=InnoDB;

CREATE TABLE Contato (
    IDContato INT AUTO_INCREMENT PRIMARY KEY,
    IDEntidade INT NOT NULL,
    TipoContato ENUM('EMAIL', 'TELEFONE', 'CELULAR', 'WHATSAPP') NOT NULL,
    Valor VARCHAR(255) NOT NULL,
    Principal BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (IDEntidade) REFERENCES Entidade(IDEntidade) ON DELETE CASCADE,
    INDEX(IDEntidade, TipoContato)
) ENGINE=InnoDB;

CREATE TABLE ProdutoBase (
    IDProduto INT AUTO_INCREMENT PRIMARY KEY,
    Nome VARCHAR(255) NOT NULL,
    Descricao TEXT,
    CodigoBarras VARCHAR(100) UNIQUE,
    UnidadeMedida VARCHAR(20) DEFAULT 'UN',
    Ativo BOOLEAN DEFAULT TRUE,
    DataCriacao DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE Estoque (
    IDEstoque INT AUTO_INCREMENT PRIMARY KEY,
    IDProduto INT NOT NULL,
    Quantidade DECIMAL(10, 2) NOT NULL DEFAULT 0,
    EstoqueMinimo DECIMAL(10, 2) DEFAULT 0,
    Localizacao VARCHAR(100),
    UltimaMovimentacao DATETIME,
    UNIQUE (IDProduto),
    FOREIGN KEY (IDProduto) REFERENCES ProdutoBase(IDProduto) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE HistoricoPrecos (
    IDHistoricoPreco INT AUTO_INCREMENT PRIMARY KEY,
    IDProduto INT NOT NULL,
    PrecoCusto DECIMAL(10, 2) NOT NULL,
    PrecoVenda DECIMAL(10, 2) NOT NULL,
    DataInicioVigencia DATETIME NOT NULL,
    DataFimVigencia DATETIME,
    FOREIGN KEY (IDProduto) REFERENCES ProdutoBase(IDProduto) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Usuario (
    IDUsuario INT AUTO_INCREMENT PRIMARY KEY,
    Login VARCHAR(50) NOT NULL UNIQUE,
    SenhaHash VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE Perfil (
    IDPerfil INT AUTO_INCREMENT PRIMARY KEY,
    Nome VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE UsuarioPerfil (
    IDUsuario INT NOT NULL,
    IDPerfil INT NOT NULL,
    PRIMARY KEY (IDUsuario, IDPerfil),
    FOREIGN KEY (IDUsuario) REFERENCES Usuario(IDUsuario) ON DELETE CASCADE,
    FOREIGN KEY (IDPerfil) REFERENCES Perfil(IDPerfil) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Permissao (
    IDPermissao INT AUTO_INCREMENT PRIMARY KEY,
    Nome VARCHAR(100) NOT NULL UNIQUE,
    Descricao TEXT
) ENGINE=InnoDB;

CREATE TABLE PerfilPermissao (
    IDPerfil INT NOT NULL,
    IDPermissao INT NOT NULL,
    PRIMARY KEY (IDPerfil, IDPermissao),
    FOREIGN KEY (IDPerfil) REFERENCES Perfil(IDPerfil) ON DELETE CASCADE,
    FOREIGN KEY (IDPermissao) REFERENCES Permissao(IDPermissao) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Pedido (
    IDPedido INT AUTO_INCREMENT PRIMARY KEY,
    IDCliente INT NOT NULL,
    IDEnderecoEntrega INT,
    DataPedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    Status ENUM('PENDENTE', 'CONFIRMADO', 'PREPARANDO', 'ENVIADO', 'ENTREGUE', 'CANCELADO') DEFAULT 'PENDENTE',
    ValorTotal DECIMAL(12, 2) DEFAULT 0,
    Observacoes TEXT,
    FOREIGN KEY (IDCliente) REFERENCES Entidade(IDEntidade) ON DELETE RESTRICT,
    FOREIGN KEY (IDEnderecoEntrega) REFERENCES EnderecoBase(IDEndereco) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE ItemPedido (
    IDItemPedido INT AUTO_INCREMENT PRIMARY KEY,
    IDPedido INT NOT NULL,
    IDProduto INT NOT NULL,
    Quantidade DECIMAL(10, 2) NOT NULL,
    PrecoUnitario DECIMAL(10, 2) NOT NULL,
    Subtotal DECIMAL(10, 2) AS (Quantidade * PrecoUnitario) STORED,
    FOREIGN KEY (IDPedido) REFERENCES Pedido(IDPedido) ON DELETE CASCADE,
    FOREIGN KEY (IDProduto) REFERENCES ProdutoBase(IDProduto) ON DELETE RESTRICT,
    UNIQUE (IDPedido, IDProduto)
) ENGINE=InnoDB;

CREATE TABLE MovimentacaoEstoque (
    IDMovimentacao INT AUTO_INCREMENT PRIMARY KEY,
    IDProduto INT NOT NULL,
    TipoMovimentacao ENUM('ENTRADA', 'SAIDA', 'AJUSTE') NOT NULL,
    Quantidade DECIMAL(10, 2) NOT NULL,
    DataMovimentacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    IDPedido INT NOT NULL,
    IDNotaFiscal INT NOT NULL,
    IDUsuario INT NOT NULL,
    Observacao TEXT
) ENGINE=InnoDB;

CREATE TABLE NotaFiscal (
    IDNotaFiscal INT AUTO_INCREMENT PRIMARY KEY,
    IDPedido INT NOT NULL,
    DataEmissao DATETIME NOT NULL,
    ValorTotal DECIMAL(10, 2) NOT NULL,
    XMLNotaFiscal TEXT,
    Status ENUM('RASCUNHO', 'EMITIDA', 'CANCELADA') DEFAULT 'RASCUNHO',
    IDEmitente INT NOT NULL,
    IDDestinatario INT NOT NULL,
    TipoNota ENUM('ENTRADA', 'SAIDA') NOT NULL,
    Observacoes TEXT,
    FOREIGN KEY (IDPedido) REFERENCES Pedido(IDPedido) ON DELETE RESTRICT,
    FOREIGN KEY (IDEmitente) REFERENCES Entidade(IDEntidade) ON DELETE RESTRICT,
    FOREIGN KEY (IDDestinatario) REFERENCES Entidade(IDEntidade) ON DELETE RESTRICT,
    INDEX(DataEmissao)
) ENGINE=InnoDB;

CREATE TABLE LogAcoes (
    IDLog INT AUTO_INCREMENT PRIMARY KEY,
    IDUsuario INT,
    Acao VARCHAR(255) NOT NULL,
    TabelaAfetada VARCHAR(100),
    IDRegistroAfetado INT,
    TimestampAcao DATETIME DEFAULT CURRENT_TIMESTAMP,
    DadosAntigos TEXT,
    DadosNovos TEXT,
    FOREIGN KEY (IDUsuario) REFERENCES Usuario(IDUsuario) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE VIEW VW_Clientes AS
SELECT
    IDEntidade,
    Nome,
    CPF,
    CNPJ,
    Ativo,
    DataCriacao
FROM Entidade
WHERE EhCliente = TRUE;

CREATE VIEW VW_Fornecedores AS
SELECT
    IDEntidade,
    Nome,
    CPF,
    CNPJ,
    Ativo,
    DataCriacao
FROM Entidade
WHERE EhFornecedor = TRUE;

CREATE VIEW VW_ClientesFornecedores AS
SELECT
    IDEntidade,
    Nome,
    CPF,
    CNPJ,
    Ativo,
    DataCriacao
FROM Entidade
WHERE EhCliente = TRUE AND EhFornecedor = TRUE;

CREATE INDEX idx_entidade_tipo ON Entidade(EhCliente, EhFornecedor);
CREATE INDEX idx_entidade_documento ON Entidade(CPF, CNPJ);
CREATE INDEX idx_pedido_entidade ON Pedido(IDCliente, DataPedido);
CREATE INDEX idx_movimento_produto ON MovimentacaoEstoque(IDProduto, DataMovimentacao);

-- Trigger para validar se a entidade é um cliente ativo ao criar pedido
DELIMITER //

CREATE TRIGGER trg_pedido_validar_cliente
BEFORE INSERT ON Pedido
FOR EACH ROW
BEGIN
    DECLARE eh_cliente INT DEFAULT 0;

    -- Verifica se a entidade existe e é cliente ativo
    SELECT EhCliente
    INTO eh_cliente
    FROM Entidade
    WHERE IDEntidade = NEW.IDCliente AND Ativo = TRUE
    LIMIT 1;

    IF eh_cliente = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Entidade deve ser um cliente ativo para criar pedido';
    END IF;
END//

DELIMITER ;


-- Trigger para atualizar valor total do pedido após inserção de item
DELIMITER //

CREATE TRIGGER trg_item_pedido_total_insert
AFTER INSERT ON ItemPedido
FOR EACH ROW
BEGIN
    UPDATE Pedido
    SET ValorTotal = (
        SELECT COALESCE(SUM(Subtotal), 0)
        FROM ItemPedido
        WHERE IDPedido = NEW.IDPedido
    )
    WHERE IDPedido = NEW.IDPedido;
END//

DELIMITER ;


-- Trigger para atualizar valor total do pedido após atualização de item
DELIMITER //

CREATE TRIGGER trg_item_pedido_total_update
AFTER UPDATE ON ItemPedido
FOR EACH ROW
BEGIN
    UPDATE Pedido
    SET ValorTotal = (
        SELECT COALESCE(SUM(Subtotal), 0)
        FROM ItemPedido
        WHERE IDPedido = NEW.IDPedido
    )
    WHERE IDPedido = NEW.IDPedido;
END//

DELIMITER ;


-- Trigger para atualizar valor total do pedido após exclusão de item
DELIMITER //

CREATE TRIGGER trg_item_pedido_total_delete
AFTER DELETE ON ItemPedido
FOR EACH ROW
BEGIN
    UPDATE Pedido
    SET ValorTotal = (
        SELECT COALESCE(SUM(Subtotal), 0)
        FROM ItemPedido
        WHERE IDPedido = OLD.IDPedido
    )
    WHERE IDPedido = OLD.IDPedido;
END//

DELIMITER ;


-- Trigger para atualizar estoque após movimentação
DELIMITER //

CREATE TRIGGER trg_movimento_atualizar_estoque
AFTER INSERT ON MovimentacaoEstoque
FOR EACH ROW
BEGIN
    DECLARE fator INT DEFAULT 1;

    IF NEW.TipoMovimentacao = 'SAIDA' THEN
        SET fator = -1;
    END IF;

    INSERT INTO Estoque (IDProduto, Quantidade, UltimaMovimentacao)
    VALUES (NEW.IDProduto, NEW.Quantidade * fator, NEW.DataMovimentacao)
    ON DUPLICATE KEY UPDATE
        Quantidade = Quantidade + (NEW.Quantidade * fator),
        UltimaMovimentacao = NEW.DataMovimentacao;
END//

DELIMITER ;


-- Trigger para log de ações na tabela Entidade
DELIMITER //

CREATE TRIGGER TRG_LogUpdateEntidade
AFTER UPDATE ON Entidade
FOR EACH ROW
BEGIN
    INSERT INTO LogAcoes (
        IDUsuario,
        Acao,
        TabelaAfetada,
        IDRegistroAfetado,
        DadosAntigos,
        DadosNovos
    )
    VALUES (
        NULL,
        'UPDATE',
        'Entidade',
        OLD.IDEntidade,
        JSON_OBJECT('Nome', OLD.Nome, 'Ativo', OLD.Ativo),
        JSON_OBJECT('Nome', NEW.Nome, 'Ativo', NEW.Ativo)
    );
END//

DELIMITER ;
