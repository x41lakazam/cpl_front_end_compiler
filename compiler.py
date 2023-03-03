from lexer import CPLLexer
from parser import CPLParser


def compile():
    import sys

    if len(sys.argv) != 2:
        print("Usage: python compile.py <file.cpl>")

    filename = sys.argv[1]
    text = open(filename).read()

    parser = CPLParser()
    lexer = CPLLexer()
    try:
        result = parser.parse(lexer.tokenize(text))
        parser.on_finish()
        print(result)
    except EOFError:
        pass

if __name__ == '__main__':
    compile()
