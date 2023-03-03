"""
program -> declarations stmt_block
declarations -> declarations declaration
| epsilon
declaration -> idlist ':' type ';'
type -> INT
| FLOAT
idlist -> idlist ',' ID
| ID
stmt -> assignment_stmt
| input_stmt
| output_stmt
| if_stmt
| while_stmt
| switch_stmt
| break_stmt
| stmt_block
assignment_stmt -> ID '=' expression ';'
input_stmt -> INPUT '(' ID ')' ';'
output_stmt -> OUTPUT '(' expression ')' ';'
if_stmt -> IF ')' boolexpr '(' stmt ELSE stmt
while_stmt -> WHILE ')' boolexpr '(' stmt
switch_stmt -> SWITCH '(' expression ')' '{' caselist
DEFAULT ':' stmtlist '}'
caselist -> caselist CASE NUM ':' stmtlist
| epsilon
break_stmt -> BREAK ';'
stmt_block -> '{' stmtlist '}'
stmtlist -> stmtlist stmt
| epsilon
boolexpr -> boolexpr OR boolterm
| boolterm
boolterm -> boolterm AND boolfactor
| boolfactor
boolfactor -> NOT '(' boolexpr ')'
| expression RELOP expression

expression -> expression ADDOP term
| term
39

term -> term MULOP factor
| factor

factor -> '(' expression ')'
| CAST '(' expression ')'
| ID
| NUM
"""

from sly import Lexer

letter = r"[a-zA-Z]"
digit = [0-9]

class CPLLexer(Lexer):
    ignore = ' \t'
    ignore_comment = r'/\*[^(\*/)]+\*/'

    #tokens = set(t.value for t in Tokens)
    # tokens = {IF, BREAK, CASE, DEFAULT, ELSE, FLOAT, IF, INPUT, INT, OUTPUT, STATIC_CAST, SWITCH, WHILE,
    #           EQUAL, NEQUAL, LESS, GREATER, EQLESS, EQGREATER, PLUS, MINUS, MULTIPLY, DIVIDE, OR, AND, NOT,
    #           ID, NUM}

    tokens = {IF, BREAK, CASE, DEFAULT, ELSE, FLOAT, IF, INPUT, INT, OUTPUT, CAST, SWITCH, WHILE,
              RELOP, ADDOP, MULOP, OR, AND, NOT, ID, NUM}

    BREAK = "break"
    CASE = "case"
    DEFAULT = "default"
    ELSE = "else"
    FLOAT = "float"
    IF = "if"
    INPUT = "input"
    INT = "int"
    OUTPUT = "output"
    SWITCH = "switch"
    WHILE = "while"
    _STATIC_CAST_INT = "static_cast<int>"
    _STATIC_CAST_FLOAT = "static_cast<float>"
    CAST = f"{_STATIC_CAST_INT}|{_STATIC_CAST_FLOAT}"

    # RELOP
    _EQUAL = "=="
    _NEQUAL = "!="
    _LESS = "<"
    _GREATER = ">"
    _EQLESS = "<="
    _EQGREATER = ">="

    RELOP = f"{_EQUAL}|{_NEQUAL}|{_LESS}|{_GREATER}|{_EQLESS}|{_EQGREATER}"

    # ADDOP
    _PLUS = f"\+"
    _MINUS = "-"

    ADDOP = f"{_PLUS}|{_MINUS}"

    # MULOP
    _MULTIPLY = f"\*"
    _DIVIDE = "/"

    MULOP = rf"{_MULTIPLY}|{_DIVIDE}"

    # Logical OP
    OR = r"\|\|"
    AND = "&&"
    NOT = "!"

    ID = rf"[a-zA-Z][a-zA-Z0-9]*"
    NUM = rf"[0-9]+(?:.[0-9]+)?"

    literals = {'(', ')', '{', '}', ',', ':', ';', '='}

    @_(NUM)
    def NUM(self, t):
        try:
            t.value = int(t.value)
        except ValueError:
            t.value = float(t.value)
        return t

    @_(r"\n+")
    def newline(self, t):
        self.lineno+=1


    def error(self, t):
        print('Line %d: Bad character %r' % (self.lineno, t.value[0]))
        self.index += 1



def test_lexer(data):
    lexer = CPLLexer()
    for tok in lexer.tokenize(data):
        print(f'{tok.type=}, {tok.value=}')

if __name__ == '__main__':
    data = 'if (a == b) { a = 2.5 };'
    test_lexer(data)
