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
        self.root.after_idle(self.ajustar_fontes)

    def criar_layout(self) -> None:
        self.root.title("Calculadora")
        self.root.resizable(True, True)
        self.root.geometry("520x760")
        self.root.minsize(380, 560)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.tela_cheia = False
        self.estado_anterior = "normal"
        self.root.bind("<Configure>", self.ajustar_fontes)
        self.root.bind("<F11>", self.alternar_tela_cheia)
        self.root.bind("<Escape>", self.sair_tela_cheia)
        self.root.bind_all("<KeyPress>", self.tratar_tecla)

        principal = ttk.Frame(self.root, padding=12)
        principal.grid(row=0, column=0, sticky="nsew")
        for coluna in range(4):
            principal.columnconfigure(coluna, weight=1, uniform="colunas")
        principal.rowconfigure(0, weight=1)
        for linha in range(1, 6):
            principal.rowconfigure(linha, weight=2, uniform="teclas")
        principal.rowconfigure(7, weight=1)

        self.estilo = ttk.Style(self.root)
        self.estilo.configure("Calculadora.TButton", font=("Segoe UI", 16))
        self.estilo.configure(
            "Calculadora.Copiar.TButton",
            font=("Segoe UI", 9),
            padding=(6, 3),
        )
        self.estilo.configure("Calculadora.TLabel", font=("Segoe UI", 10))
        faixa_display = ttk.Frame(principal)
        faixa_display.grid(
            row=0, column=0, columnspan=4, sticky="nsew", pady=(0, 10)
        )
        faixa_display.columnconfigure(0, weight=1)
        self.display = ttk.Entry(
            faixa_display,
            textvariable=self.display_var,
            font=("Segoe UI", 22),
            justify="right",
            width=MAX_DISPLAY_CHARS,
            state="readonly",
        )
        self.display.grid(row=0, column=0, sticky="nsew")
        ttk.Button(
            faixa_display,
            text="Copiar",
            command=self.copiar_resultado,
            style="Calculadora.Copiar.TButton",
        ).grid(row=0, column=1, sticky="ns", padx=(6, 0))

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
                principal,
                text=texto,
                command=comando,
                style="Calculadora.TButton",
            ).grid(row=linha, column=coluna, sticky="nsew", padx=2, pady=2)

        self.rotulo_historico = ttk.Label(
            principal,
            text="Histórico recente",
            style="Calculadora.TLabel",
        )
        self.rotulo_historico.grid(
            row=6, column=0, columnspan=4, sticky="w", pady=(10, 2)
        )
        self.lista_historico = tk.Listbox(
            principal,
            height=6,
            width=40,
            activestyle="none",
            font=("Segoe UI", 10),
        )
        self.lista_historico.grid(
            row=7, column=0, columnspan=4, sticky="nsew"
        )

    def tratar_tecla(self, evento: tk.Event) -> str | None:
        tecla = evento.char
        teclas_numericas = {
            f"KP_{digito}": str(digito) for digito in range(10)
        }
        if evento.keysym in teclas_numericas:
            self.adicionar_digito(teclas_numericas[evento.keysym])
            return "break"
        if tecla.isdigit():
            self.adicionar_digito(tecla)
            return "break"

        operadores = {
            "plus": "+",
            "KP_Add": "+",
            "minus": "-",
            "KP_Subtract": "-",
            "asterisk": "*",
            "KP_Multiply": "*",
            "slash": "/",
            "KP_Divide": "/",
        }
        operador = (
            tecla
            if tecla and tecla in "+-*/"
            else operadores.get(evento.keysym)
        )
        if operador:
            self.adicionar_operador(operador)
            return "break"

        if (tecla and tecla in ".,") or evento.keysym == "KP_Decimal":
            self.adicionar_decimal()
            return "break"
        if evento.keysym in ("Return", "KP_Enter", "equal", "KP_Equal"):
            self.calcular_atual()
            return "break"
        if evento.keysym == "BackSpace":
            self.apagar_ultimo()
            return "break"
        if evento.keysym == "Delete":
            self.limpar()
            return "break"
        if tecla.isalpha():
            return "break"
        return None

    def ajustar_fontes(self, evento: tk.Event | None = None) -> None:
        if evento is not None and evento.widget is not self.root:
            return
        largura = max(self.root.winfo_width(), 1)
        altura = max(self.root.winfo_height(), 1)
        tamanho = max(12, min(40, int(min(largura / 28, altura / 22))))
        self.estilo.configure(
            "Calculadora.TButton",
            font=("Segoe UI", tamanho),
            padding=(tamanho // 2, tamanho // 3),
        )
        self.estilo.configure(
            "Calculadora.TLabel",
            font=("Segoe UI", max(10, tamanho // 2)),
        )
        self.display.configure(font=("Segoe UI", tamanho + 6))
        self.lista_historico.configure(
            font=("Segoe UI", max(10, tamanho // 2))
        )

    def alternar_tela_cheia(self, evento: tk.Event) -> str:
        if evento.keysym != "F11":
            return "break"
        if self.tela_cheia:
            self.sair_tela_cheia()
        else:
            self.estado_anterior = self.root.state()
            self.root.attributes("-fullscreen", True)
            self.tela_cheia = True
        return "break"

    def sair_tela_cheia(self, evento: tk.Event | None = None) -> str:
        if self.tela_cheia and (evento is None or evento.keysym == "Escape"):
            self.root.attributes("-fullscreen", False)
            self.root.state(self.estado_anterior)
            self.tela_cheia = False
        return "break"

    def atualizar_display(self, valor: str) -> None:
        self.display_var.set(valor[:MAX_DISPLAY_CHARS])

    def copiar_resultado(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.display_var.get())

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
