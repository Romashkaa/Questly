from . import (
    lexer, parser,
    token, nodes,
    builder
)

def analyze(src: str):
    tokens = lexer.Lexer(src).tokenize()
    ast = parser.Parser(tokens).parse()
    game = builder.Builder(ast, src).build()

    return game

__all__ = [
    "analyze",
    "lexer",
    "parser",
    "builder",
    "token",
    "nodes",
]