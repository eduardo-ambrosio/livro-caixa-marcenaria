"""Ponto de entrada do protótipo Livro Caixa da Marcenaria."""

from livro_caixa.application import LivroCaixaApp


def main() -> None:
    app = LivroCaixaApp()
    app.mainloop()


if __name__ == "__main__":
    main()
