"""
main.py
-------
Ponto de entrada do FerroFlux.

    python main.py
"""

from __future__ import annotations

from database.conexao import ConexaoError, carregar_config_do_banco, configurar


def main() -> None:
    # Tenta carregar a configuração salva no banco
    try:
        config = carregar_config_do_banco()
        if config is not None:
            configurar(config)
            from telas.login import TelaLogin

            TelaLogin().mainloop()
            return
    except ConexaoError:
        pass

    # Sem configuração válida — abre a tela de conexão inicial
    from telas.conexao import TelaConexao

    TelaConexao().mainloop()


if __name__ == "__main__":
    main()
