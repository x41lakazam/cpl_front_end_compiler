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
    tree: Any
    start_of_block: int = -1


class Variable:
    def __init__(self, name, type, defined_at=None, in_block_from=None):
        self.name = name
        self.type = type
        self.defined_at = defined_at
        self.in_block_from = in_block_from

class VariablesManager:

    def __init__(self, quad_translator):
        self.vars = {
            # var_name: Variable()
        }
        self.next_tmp = 0
        self.quad_translator = quad_translator


    def def_var(self, varname, type, defined_at=None, in_block_from=None):
        # if varname in self.vars:
        #     raise ValueError(f"Variable {varname} previously defined")

        variable = Variable(varname, type, defined_at, in_block_from)
        self.vars[varname] = variable

    def get_tmp_var(self, type, in_block_from=None):
        varname = f"t{self.next_tmp}"
        self.next_tmp += 1
        self.def_var(varname, type, defined_at=self.quad_translator.offset, in_block_from=in_block_from)
        return varname

    def get_tmp_var_like(self, like_varname):
        """Get temp variable of the same type as <like_varname>"""
        var = self.get_var(like_varname)
        return self.get_tmp_var(var.type)

    def get_var(self, varname):
        return self.vars[varname]

    def is_float(self, varname):
        # varname may just be an int/float, in this case just return type
        if isinstance(varname, int):
            return False
        if isinstance(varname, float):
            return True

        # No, varname is really a variable name
        return self.get_var(varname).type == 'float'


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
        return ReturnModel(tree=p.tree, value=p)

    @_('declarations declaration', '')
    def declarations(self, p):
        if hasattr(p, 'declaration'):
            return ReturnModel(tree=p, value=p)
        return ReturnModel(tree=p, value=p)

    @_('idlist ":" type ";"')
    def declaration(self, p):
        for var_name in p.idlist.value:
            self._def_var(var_name, p.type.value)

        return ReturnModel(tree=p, value=p)

    @_('INT', 'FLOAT')
    def type(self, p):
        return ReturnModel(tree=p, value=p[0].lower())

    @_('idlist "," ID', 'ID')
    def idlist(self, p):
        if not hasattr(p, 'idlist'):
            return ReturnModel(tree=p, value=[p[0]])

        idlist = p.idlist.value
        idlist.append(p.ID)
        return ReturnModel(tree=p, value=idlist)

    @_('assignment_stmt', 'input_stmt', 'output_stmt', 'if_stmt', 'while_stmt', 'switch_stmt', 'break_stmt', 'stmt_block')
    def stmt(self, p):
        return ReturnModel(tree=p, value=p)

    @_('ID "=" expression ";"')
    def assignment_stmt(self, p):
        # TODO check var exist
        self.translator.gen(f"IASN {p.ID} {p.expression.value}")
        return ReturnModel(tree=p.tree, value=p)

    @_('INPUT "(" ID ")" ";"')
    def input_stmt(self, p):
        # TODO check var exist
        self.translator.gen(f"RINP {p.ID}")
        return ReturnModel(tree=p, value=p)

    @_('OUTPUT "(" expression ")" ";"')
    def output_stmt(self, p):
        self.translator.gen(f"IPRT {p.expression.value}")
        return ReturnModel(tree=p.tree, value=p)

    @_('IF "(" boolexpr ")" stmt', 'IF "(" boolexpr ")" stmt ELSE stmt')
    def if_stmt(self, p):
        return ReturnModel(tree=p.tree, value=p)

    @_('WHILE "(" boolexpr ")" stmt')
    def while_stmt(self, p):
        return ReturnModel(tree=p.tree, value=p)

    @_('SWITCH "(" expression ")" "{" caselist DEFAULT ":" stmtlist "}"')
    def switch_stmt(self, p):
        # TODO
        return ReturnModel(tree=p.tree, value=p)

    @_('caselist CASE NUM ":" stmtlist', '')
    def caselist(self, p):
        # TODO
        return ReturnModel(tree=p.tree, value=p)

    @_('BREAK ";"')
    def break_stmt(self, p):
        # TODO
        return ReturnModel(tree=p.tree, value=p)

    @_('"{" stmtlist "}"')
    def stmt_block(self, p):
        return ReturnModel(tree=p.tree, value=p)

    @_('stmtlist stmt', 'stmt')
    def stmtlist(self, p):
        return ReturnModel(tree=p, value=p)

    @_('boolexpr OR boolterm', 'boolterm')
    def boolexpr(self, p):
        """Return the variable containing the bool expr (type int)"""
        if not hasattr(p, "OR"):
            return ReturnModel(tree=p.tree, value=p[0])

        boolexpr_var = self.vars_mgr.get_var(p.boolexpr.value)
        block_start = boolexpr_var.in_block_from or boolexpr_var.defined_at
        res_var = self.vars_mgr.get_tmp_var("int", in_block_from=block_start)
        self.translator.or_(res_var, p.boolexpr.value, p.boolterm.value)
        return ReturnModel(tree=p.tree, value=res_var)

    @_('boolterm AND boolfactor', 'boolfactor')
    def boolterm(self, p):
        """Return the variable containing the bool expr (type int)"""
        if not hasattr(p, "AND"):
            return ReturnModel(tree=p.tree, value=p[0])

        boolterm_var = self.vars_mgr.get_var(p.boolterm.value)
        block_start = boolterm_var.in_block_from or boolterm_var.defined_at
        res_var = self.vars_mgr.get_tmp_var("int", in_block_from=block_start)
        self.translator.and_(res_var, p.boolterm.value, p.boolfactor.value)
        return ReturnModel(tree=p.tree, value=res_var)

    @_('NOT "(" boolexpr ")"', 'expression RELOP expression')
    def boolfactor(self, p):
        """Return the variable containing the expression (type int)"""
        if hasattr(p, "NOT"):
            result_var = self.vars_mgr.get_tmp_var_like(p.boolexpr.value)
            self.translator.gen(f"REQL {p.boolexpr} {result_var} 0")
            return ReturnModel(tree=p.tree, value=result_var)

        exp0, exp1 = p.expression0.value, p.expression1.value
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

        result_var = self.vars_mgr.get_tmp_var('int')  # Result is a bool represented by an int
        self.translator.relop(p.RELOP, result_var, exp0, exp1)

        return ReturnModel(tree=p, value=result_var)

    @_('expression ADDOP term', 'term')
    def expression(self, p):
        """Return a variable containing the expression result"""
        if not hasattr(p, "ADDOP"):
            return ReturnModel(tree=p.tree, value=p.term.value)

        # Create result variable
        if self.vars_mgr.is_float(p.term.value) or self.vars_mgr.is_float(p.expression.value):
            result_var_type = 'float'
        else:
            result_var_type = int
        result_var = self.vars_mgr.get_tmp_var(result_var_type) # TODO check type

        self.translator.muladd_op(p.ADDOP, result_var, p.expression.value, p.term.value)

        return ReturnModel(tree=p.tree, value=result_var)

    @_('term MULOP factor', 'factor')
    def term(self, p):
        """Return a variable containing the expression result"""
        if not hasattr(p, "MULOP"):
            return ReturnModel(tree=p, value=p.factor.value)

        # Create result variable
        if self.vars_mgr.is_float(p.term.value) or self.vars_mgr.is_float(p.factor.value):
            result_var_type = 'float'
        else:
            result_var_type = 'int'
        result_var = self.vars_mgr.get_tmp_var(result_var_type) # TODO check type

        # Generate quad line
        self.translator.muladd_op(p.MULOP.value, result_var, p.term.value, p.factor.value)
        return ReturnModel(tree=p.tree, value=result_var)

    @_('"(" expression ")"')
    def factor(self, p):
        """Return the variable containing the factor"""
        return ReturnModel(tree=p.tree, value=p[0])

    @_('CAST "(" expression ")"')
    def cast_factor(self, p):
        """Return the variable if it is already in the right type or a new variable in the right type"""
        if p.CAST.value not in ("int", "float"):
            raise ValueError(f"Invalid type {p.CAST.value}")

        if self.vars_mgr.get_var(p).type == p.CAST.value:
            return ReturnModel(tree=p.tree, value=p)

        new_var = self.vars_mgr.get_tmp_var(p.CAST.value)
        op = "ITOR" if p.CAST.value == 'float' else "RTOI"
        self.translator.gen(f"{op} {new_var} {p.expression}")
        return ReturnModel(tree=p.tree, value=new_var)

    @_('ID', 'NUM')
    def factor(self, p):
        return ReturnModel(tree=p, value=p[0])

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
        
        while (a+b<5)
            b = b + 5;
            
        if (a<b)
            output(a);
        else
            output(b);
        
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