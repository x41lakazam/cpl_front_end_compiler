import builtins
from dataclasses import dataclass
from typing import Any

from sly import Parser

from lexer import CPLLexer
from quad_translate import QuadTranslator

OUTFILE = "output.quad"
_OUTPUT_LINES = []

class ParserError(Exception):
    pass


@dataclass
class ReturnModel:
    value: Any
    start_of_block: int


class Variable:
    def __init__(self, name, type, defined_at=None, from_block=None):
        self.name = name
        self.type = type
        self.defined_at = defined_at
        self.from_block = from_block

class VariablesManager:

    def __init__(self, quad_translator):
        self.vars = {
            # var_name: Variable()
        }
        self.next_tmp = 0
        self.quad_translator = quad_translator


    def def_var(self, varname, type, defined_at=None, from_block=None):
        # if varname in self.vars:
        #     raise ValueError(f"Variable {varname} previously defined")

        variable = Variable(varname, type, defined_at, from_block)
        self.vars[varname] = variable

    def get_tmp_var(self, type, from_block=None, in_block_of=None):
        varname = f"t{self.next_tmp}"
        self.next_tmp += 1
        if in_block_of:
            from_block = self.get_block_offset(in_block_of)
        self.def_var(varname, type, defined_at=self.quad_translator.offset+1, from_block=from_block)
        return varname

    def get_tmp_var_like(self, like_varname, in_block_of):
        """Get temp variable of the same type as <like_varname>"""
        like_var = self.get_var(like_varname)
        return self.get_tmp_var(like_var.type, in_block_of=in_block_of)

    def get_var(self, varname):
        return self.vars[varname]

    def is_float(self, varname):
        if isinstance(varname, int):
            return False
        elif isinstance(varname, float):
            return True

        return self.get_var(varname).type == 'float'

    def get_block_offset(self, varname):
        var = self.get_var(varname)
        return var.from_block or var.defined_at


class CPLParser(Parser):

    tokens = CPLLexer.tokens
    literals = CPLLexer.literals


    def __init__(self, *args, **kwargs):
        self.translator = QuadTranslator()
        self.vars_mgr = VariablesManager(self.translator)
        super().__init__(*args, **kwargs)

    def _def_var(self, varname, type):
        """Register a variable in the manager"""
        self.vars_mgr.def_var(varname, type)

    @_('declarations stmt_block')
    def program(self, p):
        return p

    @_('declarations declaration', '')
    def declarations(self, p):
        return p

    @_('idlist ":" type ";"')
    def declaration(self, p):
        for var_name in p.idlist:
            self._def_var(var_name, p.type)
        return

    @_('INT', 'FLOAT')
    def type(self, p):
        return p[0].lower()

    @_('idlist "," ID', 'ID')
    def idlist(self, p):
        idlist = getattr(p, "idlist", [])
        idlist.append(p.ID)
        return idlist

    @_('assignment_stmt', 'input_stmt', 'output_stmt', 'if_stmt', 'while_stmt', 'switch_stmt', 'break_stmt', 'stmt_block')
    def stmt(self, p):
        return p

    @_('ID "=" expression ";"')
    def assignment_stmt(self, p):
        # TODO check var exist
        self.translator.gen(f"IASN {p.ID} {p.expression}")
        return p

    @_('INPUT "(" ID ")" ";"')
    def input_stmt(self, p):
        # TODO check var exist
        self.translator.gen(f"RINP {p.ID}")
        return

    @_('OUTPUT "(" expression ")" ";"')
    def output_stmt(self, p):
        self.translator.gen(f"IPRT {p.expression}")
        return

    @_('IF "(" boolexpr ")" stmt', 'IF "(" boolexpr ")" stmt ELSE stmt')
    def if_stmt(self, p):
        return p

    @_('WHILE "(" boolexpr ")" stmt')
    def while_stmt(self, p):
        start_of_expr_block = self.vars_mgr.get_var(p.boolexpr).from_block
        self.translator.gen(f"JUMP {start_of_expr_block}")
        return p

    @_('SWITCH "(" expression ")" "{" caselist DEFAULT ":" stmtlist "}"')
    def switch_stmt(self, p):
        # TODO
        return p

    @_('caselist CASE NUM ":" stmtlist', '')
    def caselist(self, p):
        # TODO
        return p

    @_('BREAK ";"')
    def break_stmt(self, p):
        # TODO
        return p

    @_('"{" stmtlist "}"')
    def stmt_block(self, p):
        return p

    @_('stmtlist stmt', 'stmt')
    def stmtlist(self, p):
        return p

    @_('boolexpr OR boolterm', 'boolterm')
    def boolexpr(self, p):
        """Return the variable containing the bool expr (type int)"""
        if not hasattr(p, "OR"):
            return p[0]

        res_var = self.vars_mgr.get_tmp_var("int", in_block_of=p.boolexpr)
        self.translator.or_(res_var, p.boolexpr, p.boolterm)
        return res_var

    @_('boolterm AND boolfactor', 'boolfactor')
    def boolterm(self, p):
        """Return the variable containing the bool expr (type int)"""
        if not hasattr(p, "AND"):
            return p[0]

        res_var = self.vars_mgr.get_tmp_var("int", in_block_of=p.boolterm)
        self.translator.and_(res_var, p.boolterm, p.boolfactor)
        return res_var

    @_('NOT "(" boolexpr ")"', 'expression RELOP expression')
    def boolfactor(self, p):
        """Return the variable containing the expression (type int)"""
        if hasattr(p, "NOT"):
            result_var = self.vars_mgr.get_tmp_var_like(p.boolexpr)
            self.translator.gen(f"REQL {p.boolexpr} {result_var} 0")
            return result_var

        # Get offset of expr block
        if isinstance(p.expression0, int) or isinstance(p.expression0, float):
            if isinstance(p.expression1, int) or isinstance(p.expression1, float):
                expr_block = self.translator.offset
            else:
                expr_block = self.vars_mgr.get_block_offset(p.expression1)
        else:
            expr_block = self.vars_mgr.get_block_offset(p.expression0)

        exp0, exp1 = p.expression0, p.expression1
        if self.vars_mgr.is_float(exp0) and not self.vars_mgr.is_float(exp1):
            # exp0 is a float but exp1 is an int
            exp1_as_float = self.vars_mgr.get_tmp_var('float')
            self.translator.gen(f"ITOR {exp1_as_float} {exp1}")
            exp1 = exp1_as_float
        elif self.vars_mgr.is_float(exp0) and not self.vars_mgr.is_float(exp1):
            exp0_as_float = self.vars_mgr.get_tmp_var('float')
            self.translator.gen(f"ITOR {exp0_as_float} {exp0}")
            exp0 = exp0_as_float
        # else they are both int or both float

        result_var = self.vars_mgr.get_tmp_var('int', from_block=expr_block)  # Result is a bool represented by an int
        self.translator.relop(p.RELOP, result_var, exp0, exp1)

        return result_var

    @_('expression ADDOP term', 'term')
    def expression(self, p):
        """Return a variable containing the expression result"""
        if not hasattr(p, "ADDOP"):
            return p.term

        # Create result variable
        if self.vars_mgr.is_float(p.term) or self.vars_mgr.is_float(p.expression):
            result_var_type = 'float'
        else:
            result_var_type = int
        result_var = self.vars_mgr.get_tmp_var(result_var_type, in_block_of=p.expression) # TODO check type

        self.translator.muladd_op(p.ADDOP, result_var, p.expression, p.term)

        return result_var

    @_('term MULOP factor', 'factor')
    def term(self, p):
        """Return a variable containing the expression result"""
        if not hasattr(p, "MULOP"):
            return p.factor

        # Create result variable
        if self.vars_mgr.is_float(p.term) or self.vars_mgr.is_float(p.factor):
            result_var_type = 'float'
        else:
            result_var_type = 'int'

        result_var = self.vars_mgr.get_tmp_var(result_var_type, in_block_of=p.term) # TODO check type

        # Generate quad line
        self.translator.muladd_op(p.MULOP, result_var, p.term, p.factor)
        return result_var

    @_('"(" expression ")"')
    def factor(self, p):
        """Return the variable containing the factor"""
        return p[0]

    @_('CAST "(" expression ")"')
    def cast_factor(self, p):
        """Return the variable if it is already in the right type or a new variable in the right type"""
        if p.CAST not in ("int", "float"):
            raise ValueError(f"Invalid type {p.CAST}")

        if self.vars_mgr.get_var(p).type == p.CAST:
            return p

        new_var = self.vars_mgr.get_tmp_var(p.CAST)
        op = "ITOR" if p.CAST == 'float' else "RTOI"
        self.translator.gen(f"{op} {new_var} {p.expression}")
        return new_var

    @_('ID', 'NUM')
    def factor(self, p):
        return p[0]

    def on_finish(self):
        self.translator.gen("HALT")
        self.translator.output()

    def error(self, p):
        if not p:
            self.on_finish()
            print('End of File!')
            raise EOFError

        print(f"ERROR on {p}")
        raise SyntaxError


if __name__ == "__main__":
    text = """
    a, b: float;
    
    {
        input(a);
        input(b);
        while (a+b>5)
            b = b+5;
    } 
    """

    parser = CPLParser()
    lexer = CPLLexer()
    try:
        #text = input("calc > ")
        result = parser.parse(lexer.tokenize(text))
        parser.on_finish()
        print(result)
    except EOFError:
        pass