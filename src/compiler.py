import sys
from lexer import CPLLexer
from ast_parser import CPLParser
from symbol_table import resolve_offsets
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
    quad_lines, failed = quad_transformer.compute()

    if failed:
        return

    # Offsets need to be updated
    quad_lines = resolve_offsets(quad_lines)

    open(outfile ,'w').writelines(
        l+'\n' for l in quad_lines
    )

    return outfile


def main():
    tests = [
        "andor.cpl",
        "cnv.cpl",
        "sqrt.cpl",
        "div.cpl",
        "cast.cpl",
        "primes.cpl",
        "sin.cpl",
        "basic.cpl",
        "binary.cpl",
        "fibo.cpl",
        "mytest.cpl",
        "easyswitch.cpl",
        "nested_switch.ou",
    ]
    for test in tests:
        print("Compiling", test)
        compile("tests/"+test, f"tests/{test}.quad")


if __name__ == '__main__':
    main()
    #compile()
