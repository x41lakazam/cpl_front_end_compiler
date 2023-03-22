import sys
from lexer import CPLLexer
from ast_parser import CPLParser
from src.symbol_table import resolve_offsets
from transformer import AstToQuad


def compile(filename=None, outfile=None):
    import sys

    if not filename:
        if len(sys.argv) < 2:
            print("Usage: python compile.py <file.cpl> <optional: outfile>")
            sys.exit()
        filename = sys.argv[1]
        if len(sys.argv) > 2:
            outfile = sys.argv[2]

    outfile = outfile or "output.quad"
    text = open(filename).read()

    parser = CPLParser()
    lexer = CPLLexer()
    ast = parser.parse(lexer.tokenize(text))
    quad_transformer = AstToQuad(ast)
    quad_lines = quad_transformer.compute()

    # Offsets need to be updated
    quad_lines = resolve_offsets(quad_lines)

    open(outfile ,'w').writelines(
        l+'\n' for l in quad_lines
    )


def main():
    tests = [
        "tests/andor.cpl",
        "tests/cnv.cpl",
        "tests/sqrt.cpl",
        "tests/div.cpl",
        "tests/cast.cpl",
        "tests/primes.cpl",
        "tests/sin.cpl",
        "tests/basic.cpl",
        "tests/binary.cpl",
        "tests/fibo.cpl",
    ]
    compile(tests[9], "output.quad")

if __name__ == '__main__':
    main()
    #compile()
