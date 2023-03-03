import builtins
from dataclasses import dataclass
from typing import Any

from sly import Parser

from errors import *
from lexer import CPLLexer
from quad_translate import QuadTranslator

OUTFILE = "output.quad"
_OUTPUT_LINES = []


class Variable:
    def __init__(self, name, type, defined_at=None, from_block=None):
        self.name = name
        self.type = type
        self.defined_at = defined_at
        self.from_block = from_block

class VariablesManager:

    def __init__(self, quad_translator):
        self.vars = {}
        self.next_tmp = 0
        self.quad_translator = quad_translator

    def check_var(self, varname):
        self.get_var(varname)  # Raise error if not exist

    def def_var(self, varname, type, defined_at=None, from_block=None):
        # if varname in self.vars:
        #     raise ValueError(f"Variable {varname} previously defined")

        variable = Variable(varname, type, defined_at, from_block)
        self.vars[varname] = variable

    def get_tmp_var(self, type, from_block=None, in_block_of=None):
        varname = f"t{self.next_tmp}"
        self.next_tmp += 1
        if in_block_of:
            if isinstance(in_block_of, (int, float)):       # in_block_of is not a variable
                from_block = self.quad_translator.offset
            else:
                from_block = self.get_block_offset(in_block_of)
        self.def_var(varname, type, defined_at=self.quad_translator.offset, from_block=from_block)
        return varname

    def get_tmp_var_like(self, like_varname, in_block_of):
        """Get temp variable of the same type as <like_varname>"""
        like_var = self.get_var(like_varname)
        return self.get_tmp_var(like_var.type, in_block_of=in_block_of)

    def get_var(self, varname):
        try:
            return self.vars[varname]
        except KeyError:
            raise UnknownVariable(varname)

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
        self.translator.remove_last_line()  # A last %ENDBLOCK% is generated, remove it
        self.translator.gen("HALT")
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
        try:
            self.vars_mgr.check_var(p.ID)
        except Exception as exc:
            self.error(p, message=str(exc))

        self.translator.gen(f"IASN {p.ID} {p.expression}")
        return p

    @_('INPUT "(" ID ")" ";"')
    def input_stmt(self, p):
        try:
            self.vars_mgr.check_var(p.ID)
        except Exception as exc:
            self.error(p, message=str(exc))

        self.translator.gen(f"RINP {p.ID}")
        return

    @_('OUTPUT "(" expression ")" ";"')
    def output_stmt(self, p):
        self.translator.gen(f"IPRT {p.expression}")
        return

    @_('IF "(" boolexpr ")" stmt_block', 'IF "(" boolexpr ")" stmt_block ELSE stmt_block')
    def if_stmt(self, p):
        self.translator.remove_last_line()
        if hasattr(p, "ELSE"):
            endblock_offset = self.translator.replace_last_endblock(f"JUMP {self.translator.offset}")
            self.translator.backref_offset(endblock_offset+1)
        return p

    @_('WHILE "(" boolexpr ")" stmt_block')
    def while_stmt(self, p):
        start_of_expr_block = self.vars_mgr.get_var(p.boolexpr).from_block
        # Replace the end of the block by a jump to the beginning of the block (looping)
        self.translator.replace_last_endblock(f"JUMP {start_of_expr_block}")
        # Replace the %END% at the  end of the NOT-boolexpr by the end of the block (exit the loop)
        self.translator.backref_offset(self.translator.offset)
        # Replace break by a jump to the end of the block (exit the loop)
        self.translator.replace_last_break(f"JUMP {self.translator.offset}")
        return p

    @_('SWITCH "(" expression ")" "{" caselist DEFAULT ":" stmtlist "}"')
    def switch_stmt(self, p):
        self.translator.replace_all_switchvars(p.expression)
        # Last switchcase is default, therefore delete it and the nextcase line
        self.translator.delete_last_next_and_switch_case()
        self.translator.replace_all_breaks(f"JUMP {self.translator.offset}")
        return p

    @_('caselist CASE NUM ":" stmtlist', '')
    def caselist(self, p):
        if not hasattr(p, "CASE"):
            # Check if swiwtch_Var == switch_case --> jump to the next case
            tmp_var = self.vars_mgr.get_tmp_var('int')
            self.translator.gen(f"IEQL {tmp_var} %SWITCHVAR% %SWITCHCASE%")
            self.translator.gen(f"JMPZ {tmp_var} %NEXTCASE%")
            return p

        #
        tmp_var = self.vars_mgr.get_tmp_var('int')
        self.translator.replace_last_nextcase(self.translator.offset)
        self.translator.replace_last_switchcase(p.NUM)
        self.translator.gen(f"IEQL {tmp_var} %SWITCHVAR% %SWITCHCASE%")
        self.translator.gen(f"JMPZ {tmp_var} %NEXTCASE%")
        return p

    @_('BREAK ";"')
    def break_stmt(self, p):
        self.translator.gen("%BREAK%")
        return p

    @_('"{" stmtlist "}"')
    def stmt_block(self, p):
        self.translator.gen("%ENDBLOCK%")
        return p

    @_('stmtlist stmt', 'stmt')
    def stmtlist(self, p):
        return p

    @_('boolexpr OR boolterm', 'boolterm')
    def boolexpr(self, p):
        """Return the variable containing the bool expr (type int)"""
        if not hasattr(p, "OR"):
            # If the boolexpr is not true --> jump to the end of the block
            self.translator.gen(f"JMPZ {p[0]} %END%")
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

    @_('CAST "(" expression ")"', '"(" expression ")"')
    def factor(self, p):
        """Return the variable containing the factor"""
        if not hasattr(p, "CAST"):
            return p[0]

        if p.CAST not in ("static_cast<int>", "static_cast<float>"):
            raise ValueError(f"Invalid type {p.CAST}")

        cast_type = "int" if p.CAST == "static_cast<int>" else 'float'

        new_var = self.vars_mgr.get_tmp_var(cast_type)
        op = "ITOR" if cast_type == 'float' else "RTOI"
        self.translator.gen(f"{op} {new_var} {p.expression}")
        return new_var

    @_('ID', 'NUM')
    def factor(self, p):
        return p[0]

    def on_finish(self):
        self.translator.output()

    def error(self, p, message=None):
        if not p:
            self.on_finish()
            print('End of File!')
            raise EOFError

        if not message:
            message = f"Unexpected token '{p.value}'"
        print(f"Parser error on line {p.lineno}, chars [{p.index}, {p.end}]: {message}")

        raise Exception


if __name__ == "__main__":
    text = """
    a, b: float;
    
    {
        input(a);
        input(b);
        
        b = static_cast<int> (a) + b;
        switch (a+b){
            case 1:
                a = 1;
                output(a);
            case 2:
                a = 2;
                output(a);
            case 3:
                a = 3;
                output(a);
                break;
            default:
                a = 10;
                output(a);
        }
        
        if (a>5+b) {
            b = b+5;
            a = b;
            output(b);
        }
        else {
            b = b +3;
            output(a);
        }
        
        while (a+b>3){
            a = 1;
            break;
            b = 2;
        }
            
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