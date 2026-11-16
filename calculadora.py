import ast
import re
import tkinter as tk
from decimal import Decimal, DivisionByZero, InvalidOperation, Overflow
from tkinter import ttk


MAX_DISPLAY_CHARS = 32
MAX_HISTORY_ITEMS = 10
VALID_EXPRESSION = re.compile(
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[+\-*/](?:\d+(?:\.\d*)?|\.\d+))*"
)


class ErroCalculadora(Exception):
    pass


def avaliar_expressao(expressao: str) -> Decimal:
    if not isinstance(expressao, str) or len(expressao) > MAX_DISPLAY_CHARS:
        raise ErroCalculadora("Erro: Expressão inválida")

    expressao = expressao.strip()
    if not VALID_EXPRESSION.fullmatch(expressao):
        raise ErroCalculadora("Erro: Expressão inválida")

    try:
        arvore = ast.parse(expressao, mode="eval")
        resultado = _avaliar_no(arvore.body)
    except ErroCalculadora:
        raise
    except (SyntaxError, InvalidOperation, Overflow, ValueError):
        raise ErroCalculadora("Erro: Expressão inválida") from None

    return resultado


def _avaliar_no(no: ast.expr) -> Decimal:
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return Decimal(str(no.value))

    if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.UAdd, ast.USub)):
        valor = _avaliar_no(no.operand)
        return valor if isinstance(no.op, ast.UAdd) else -valor

    if isinstance(no, ast.BinOp):
        esquerda = _avaliar_no(no.left)
        direita = _avaliar_no(no.right)
        if isinstance(no.op, ast.Add):
            return esquerda + direita
        if isinstance(no.op, ast.Sub):
            return esquerda - direita
        if isinstance(no.op, ast.Mult):
            return esquerda * direita
        if isinstance(no.op, ast.Div):
            if direita == 0:
                raise ErroCalculadora("Erro: Divisão por zero")
            return esquerda / direita

    raise ErroCalculadora("Erro: Expressão inválida")


def formatar_resultado(valor: Decimal) -> str:
    if not valor.is_finite():
        raise ErroCalculadora("Erro: Expressão inválida")
    if valor == 0:
        return "0"
    resultado = format(valor.normalize(), "f")
    if "." in resultado:
        resultado = resultado.rstrip("0").rstrip(".")
    if len(resultado) > MAX_DISPLAY_CHARS:
        raise ErroCalculadora("Erro: Resultado excede o display")
    return resultado


class CalculadoraGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.expressao = ""
        self.historico: list[tuple[str, str]] = []
        self.resultado_exibido = False
        self.erro_ativo = False
        self.display_var = tk.StringVar()
        self.criar_layout()
        self.atualizar_display("0")

    def criar_layout(self) -> None:
        self.root.title("Calculadora")
        self.root.resizable(False, False)

        principal = ttk.Frame(self.root, padding=12)
        principal.grid(row=0, column=0, sticky="nsew")
        principal.columnconfigure(0, weight=1)

        display = ttk.Entry(
            principal,
            textvariable=self.display_var,
            font=("Segoe UI", 22),
            justify="right",
            width=MAX_DISPLAY_CHARS,
            state="readonly",
        )
        display.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        botoes = [
            ("C", 1, 0, self.limpar),
            ("←", 1, 1, self.apagar_ultimo),
            ("/", 1, 2, lambda: self.adicionar_operador("/")),
            ("*", 1, 3, lambda: self.adicionar_operador("*")),
            ("7", 2, 0, lambda: self.adicionar_digito("7")),
            ("8", 2, 1, lambda: self.adicionar_digito("8")),
            ("9", 2, 2, lambda: self.adicionar_digito("9")),
            ("-", 2, 3, lambda: self.adicionar_operador("-")),
            ("4", 3, 0, lambda: self.adicionar_digito("4")),
            ("5", 3, 1, lambda: self.adicionar_digito("5")),
            ("6", 3, 2, lambda: self.adicionar_digito("6")),
            ("+", 3, 3, lambda: self.adicionar_operador("+")),
            ("1", 4, 0, lambda: self.adicionar_digito("1")),
            ("2", 4, 1, lambda: self.adicionar_digito("2")),
            ("3", 4, 2, lambda: self.adicionar_digito("3")),
            ("0", 5, 0, lambda: self.adicionar_digito("0")),
            (".", 5, 1, self.adicionar_decimal),
            ("=", 5, 2, self.calcular_atual),
        ]
        for texto, linha, coluna, comando in botoes:
            ttk.Button(
                principal, text=texto, command=comando, width=7
            ).grid(row=linha, column=coluna, sticky="nsew", padx=2, pady=2)

        ttk.Label(principal, text="Histórico recente").grid(
            row=6, column=0, columnspan=4, sticky="w", pady=(10, 2)
        )
        self.lista_historico = tk.Listbox(
            principal, height=6, width=40, activestyle="none"
        )
        self.lista_historico.grid(row=7, column=0, columnspan=4, sticky="ew")

    def atualizar_display(self, valor: str) -> None:
        self.display_var.set(valor[:MAX_DISPLAY_CHARS])

    def tratar_erro(self, mensagem: str) -> None:
        self.expressao = ""
        self.resultado_exibido = False
        self.erro_ativo = True
        self.atualizar_display(mensagem)

    def adicionar_ao_historico(self, expressao: str, resultado: str) -> None:
        self.historico.insert(0, (expressao, resultado))
        texto = f"{expressao} = {resultado}"
        self.lista_historico.insert(0, texto)
        if self.lista_historico.size() > MAX_HISTORY_ITEMS:
            self.lista_historico.delete(MAX_HISTORY_ITEMS, tk.END)

    def adicionar_digito(self, digito: str) -> None:
        if self.erro_ativo or self.resultado_exibido:
            self.expressao = ""
            self.erro_ativo = False
            self.resultado_exibido = False
        if len(self.expressao) >= MAX_DISPLAY_CHARS:
            self.tratar_erro("Erro: Display overflow")
            return
        self.expressao += digito
        self.atualizar_display(self.expressao)

    def adicionar_operador(self, operador: str) -> None:
        if self.erro_ativo:
            self.expressao = ""
            self.erro_ativo = False

        if not self.expressao:
            if operador == "-":
                self.expressao = operador
                self.atualizar_display(self.expressao)
            return

        if self.expressao[-1] in "+-*/":
            if len(self.expressao) == 1 and self.expressao == "-":
                return
            self.expressao = self.expressao[:-1] + operador
        elif len(self.expressao) < MAX_DISPLAY_CHARS:
            self.expressao += operador
        else:
            self.tratar_erro("Erro: Display overflow")
            return

        self.resultado_exibido = False
        self.atualizar_display(self.expressao)

    def adicionar_decimal(self) -> None:
        if self.erro_ativo or self.resultado_exibido:
            self.expressao = ""
            self.erro_ativo = False
            self.resultado_exibido = False
        trecho = re.split(r"[+\-*/]", self.expressao)[-1]
        if "." in trecho:
            return
        if len(self.expressao) + (1 if trecho else 2) > MAX_DISPLAY_CHARS:
            self.tratar_erro("Erro: Display overflow")
            return
        self.expressao += "0." if not trecho else "."
        self.atualizar_display(self.expressao)

    def apagar_ultimo(self) -> None:
        if self.erro_ativo or self.resultado_exibido:
            self.expressao = ""
            self.erro_ativo = False
            self.resultado_exibido = False
        else:
            self.expressao = self.expressao[:-1]
        self.atualizar_display(self.expressao or "0")

    def limpar(self) -> None:
        self.expressao = ""
        self.resultado_exibido = False
        self.erro_ativo = False
        self.historico.clear()
        self.lista_historico.delete(0, tk.END)
        self.atualizar_display("0")

    def calcular_atual(self) -> None:
        self.calcular(self.expressao)

    def calcular(self, expressao: str) -> None:
        try:
            resultado = formatar_resultado(avaliar_expressao(expressao))
        except ErroCalculadora as erro:
            self.tratar_erro(str(erro))
            return
        except (DivisionByZero, InvalidOperation, Overflow, ArithmeticError):
            self.tratar_erro("Erro: Expressão inválida")
            return

        self.adicionar_ao_historico(expressao, resultado)
        self.expressao = resultado
        self.resultado_exibido = True
        self.erro_ativo = False
        self.atualizar_display(resultado)


def main() -> None:
    root = tk.Tk()
    CalculadoraGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
