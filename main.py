"""
main.py
-------
Ponto de entrada do FerroFlux.

    python main.py
"""

from __future__ import annotations


def main() -> None:
    # Tenta carregar a configuração salva no banco
    try:
        from database.conexao import carregar_config_do_banco, configurar

        config = carregar_config_do_banco()
        if config is not None:
            configurar(config)
            from telas.login import TelaLogin

            TelaLogin().mainloop()
            return
    except Exception:
        pass

    # Sem configuração válida ou banco inacessível — abre tela de conexão
    try:
        from telas.tela_conexao import TelaConexao

        TelaConexao().mainloop()
    except Exception as e:
        # Último recurso: mostra erro numa janela simples
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "FerroFlux — Erro de inicialização",
            f"Não foi possível iniciar o sistema:\n\n{e}\n\n"
            "Verifique se o MySQL ODBC Driver está instalado:\n"
            "https://dev.mysql.com/downloads/connector/odbc/",
        )
        root.destroy()


if __name__ == "__main__":
    main()
