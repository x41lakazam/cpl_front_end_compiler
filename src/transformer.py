import builtins
from dataclasses import dataclass
from typing import Any, Tuple

from sly import Parser

from errors import *
from models import *
from lexer import CPLLexer
from quad_translate import QuadTranslator


class Variable:
    def __init__(self, name, type, defined_at=None, from_block=None):
        self.name = name
        self.type = type


class VariablesManager:

    def __init__(self):
        self.vars = {}
        self.next_tmp = 0

    def reset(self):
        self.vars = {}
        self.next_tmp = 0

    def check_var(self, varname):
        self.get_var(varname)  # Raise error if not exist

    def def_var(self, varname, type):
        # if varname in self.vars:
        #     raise ValueError(f"Variable {varname} previously defined")

        variable = Variable(varname, type)
        self.vars[varname] = variable

    def get_tmp_var(self, type):
        varname = f"t{self.next_tmp}"
        self.next_tmp += 1
        self.def_var(varname, type)
        return varname

    def get_tmp_var_like(self, like_varname):
        """Get temp variable of the same type as <like_varname>"""
        like_var = self.get_var(like_varname)
        return self.get_tmp_var(like_var.type)

    def get_var(self, varname):
        try:
            return self.vars[varname]
        except KeyError:
            raise UnknownVariable(varname)

    def get_type(self, varname):
        if isinstance(varname, int):
            return "INT"
        elif isinstance(varname, float):
            return "FLOAT"
        return self.get_var(varname).type

    def is_float(self, varname):
        if isinstance(varname, int):
            return False
        elif isinstance(varname, float):
            return True

        return self.get_var(varname).type == 'FLOAT'

    def get_block_offset(self, varname):
        var = self.get_var(varname)
        return var.from_block or var.defined_at



class AstToQuad:

    def __init__(self, ast):
        self.ast = ast
        self.vm = VariablesManager()
        self.tsl = QuadTranslator()

    def compute(self):
        self.vm.reset()
        lines = self.handle_program(self.ast)
        lines.append("HALT")
        return lines

    def handle_program(self, program: Program):
        for declaration in program.declarations:
            for id in declaration.id_list.ids:
                self.vm.def_var(id.id, declaration.type.type)

        return self.handle_stmtlist(program.stmts)

    def handle_stmtlist(self, stmtlist: StmtList) -> List[str]:
        lines_buf = []
        for stmt in stmtlist.stmts:
            lines = self.handle_stmt(stmt)
            lines_buf.extend(lines)

        return lines_buf

    def handle_stmt(self, stmt: Stmt) -> List[str]:
        if isinstance(stmt, StmtList):
            return self.handle_stmtlist(stmt)
        elif isinstance(stmt, IfStmt):
            return self.handle_if_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            return self.handle_while_stmt(stmt)
        elif isinstance(stmt, InputStmt):
            return self.handle_input_stmt(stmt)
        elif isinstance(stmt, AssignmentStmt):
            return self.handle_assignment_stmt(stmt)
        elif isinstance(stmt, OutputStmt):
            return self.handle_output_stmt(stmt)
        elif isinstance(stmt, SwitchStmt):
            return self.handle_switch_stmt(stmt)
        elif isinstance(stmt, BreakStmt):
            return self.handle_break_stmt(stmt)

        return []

    def handle_input_stmt(self, stmt: InputStmt) -> List[str]:
        lines = []
        if self.vm.is_float(stmt.id.id):
            lines.append(f"RINP {stmt.id.id}")
        else:
            lines.append(f"IINP {stmt.id.id}")

        return lines

    def handle_while_stmt(self, stmt: WhileStmt) -> List[str]:
        lines = []

        # Insert the lines of the while block and then jump back to here
        # if the condition is still true
        slines = self.handle_stmtlist(stmt.stmts)

        # Compute condition and jump back if true
        cond_lines, condition_var = self.handle_boolexpr(stmt.condition)
        lines.extend(cond_lines)
        lines.append(f"JMPZ %+{len(slines)+2} {condition_var}") # If false, jump the block and the jump
        lines.extend(slines)

        lines.append(f"JUMP %-{len(lines)}")    # Back to the beginning of the block

        return lines


    def handle_if_stmt(self, stmt: IfStmt) -> List[str]:
        lines = []
        cond_lines, condition_var = self.handle_boolexpr(stmt.condition)
        lines.extend(cond_lines)

        if_lines = self.handle_stmtlist(stmt.if_block)

        if stmt.else_block:
            else_lines = self.handle_stmtlist(stmt.else_block)
            jump_to_else_off = len(if_lines)+2   # If block + jump-over-else +goto next line
            lines.append(f"JMPZ %+{jump_to_else_off} {condition_var}")
            # If block + jump the else block
            lines.extend(if_lines)

            jump_to_endblock_off = len(else_lines)+1
            lines.append(f"JUMP %+{jump_to_endblock_off}")
            # Else block
            lines.extend(else_lines)
        else:
            jump_to_end_block = len(if_lines) + 1
            lines.append(f"JMPZ %+{jump_to_end_block} {condition_var}")
            lines.extend(if_lines)

        return lines

    def handle_boolexpr(self, expr: BoolExpr):
        lines = []

        rlines, right_var = self.handle_boolterm(expr.right)
        lines.extend(rlines)

        if expr.left is None: # Boolexpr is a boolterm
            return lines, right_var


        # Boolexpr is a disjunction

        llines, left_var = self.handle_boolexpr(expr.left)
        lines.extend(llines)

        res_var = self.vm.get_tmp_var("INT")
        lines.extend(self.tsl.or_(res_var, left_var, right_var))

        return lines, res_var

    def handle_boolterm(self, expr: BoolTerm) -> Tuple[List[str], str]:
        lines = []
        rlines, right_var = self.handle_boolfactor(expr.right)
        lines.extend(rlines)

        if expr.left is None:    # Boolterm is a single factor
            return lines, right_var

        # Boolterm is a conjunction
        llines, left_var = self.handle_boolterm(expr.left)
        lines.extend(llines)

        res_var = self.vm.get_tmp_var("INT")
        lines.extend(
            self.tsl.and_(res_var, right_var, left_var)
        )

        return lines, res_var

    def handle_boolfactor(self, expr: Union[BoolFactorNot, BoolFactorRelop]) -> Tuple[List[str], str]:
        if isinstance(expr, BoolFactorNot):
            return self.handle_boolfactor_not(expr)
        else:
            return self.handle_boolfactor_relop(expr)

    def handle_boolfactor_not(self, expr: BoolFactorNot) -> Tuple[List[str], str]:
        lines = []
        sublines, exp_var = self.handle_boolexpr(expr.boolexpr)
        lines.extend(sublines)

        res_var = self.vm.get_tmp_var("INT")
        lines.append(f"IEQL {res_var} {exp_var} 0")

        return lines, res_var

    def handle_boolfactor_relop(self, expr: BoolFactorRelop) -> Tuple[List[str], str]:
        lines = []

        llines, left_var = self.handle_expression(expr.left)
        lines.extend(llines)

        rlines, right_var = self.handle_expression(expr.right)
        lines.extend(rlines)

        if self.vm.is_float(left_var) and not self.vm.is_float(right_var):
            f_right_var = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {f_right_var} {right_var}")
            right_var = f_right_var
        elif self.vm.is_float(right_var) and not self.vm.is_float(left_var):
            f_left_var = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {f_left_var} {left_var}")
            left_var = f_left_var

        if self.vm.is_float(left_var):
            res_var = self.vm.get_tmp_var("FLOAT")
            lines.extend(self.tsl.relop_reals(expr.relop, res_var, left_var, right_var))
        else:
            res_var = self.vm.get_tmp_var("INT")
            lines.extend(self.tsl.relop_ints(expr.relop, res_var, left_var, right_var))

        return lines, res_var

    def handle_expression(self, expr: Expression) -> Tuple[List[str], str]:
        lines = []
        rlines, right_var = self.handle_term(expr.right)
        lines.extend(rlines)

        if expr.op is None:     # Expression is a single term
            return lines, right_var

        # Expression is the result of an operation

        # Get the left part
        llines, left_var = self.handle_expression(expr.left)
        lines.extend(llines)

        # Compute types
        if self.vm.is_float(right_var) and not self.vm.is_float(left_var):  # Cast left to float
            f_left = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {f_left} {left_var}")
            left_var = f_left
        elif self.vm.is_float(left_var) and not self.vm.is_float(right_var):  # Cast left to float
            f_right = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {f_right} {right_var}")
            right_var = f_right


        if self.vm.is_float(right_var) and self.vm.is_float(left_var):
            res_var = self.vm.get_tmp_var("FLOAT")
            mulop_lines = self.tsl.muladd_op_reals(expr.op, res_var, left_var, right_var)
        else:
            res_var = self.vm.get_tmp_var("INT")
            mulop_lines = self.tsl.muladd_op_ints(expr.op, res_var, left_var, right_var)

        lines.extend(mulop_lines)

        return lines, res_var

    def handle_term(self, term: Term) -> Tuple[List[str], str]:
        lines = []
        rlines, right_var = self.handle_factor(term.right)
        lines.extend(rlines)

        if term.op is None:     # term is a single factor
            return lines, right_var

        # Term is the result of a mulop
        # Get the left part
        llines, left_var = self.handle_term(term.left)
        lines.extend(llines)

        # Compute types
        if self.vm.is_float(right_var) and not self.vm.is_float(left_var):  # Cast left to float
            f_left = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {f_left} {left_var}")
            left_var = f_left
        elif self.vm.is_float(left_var) and not self.vm.is_float(right_var):  # Cast left to float
            f_right = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {f_right} {right_var}")
            right_var = f_right

        if self.vm.is_float(right_var) and self.vm.is_float(left_var):
            res_var = self.vm.get_tmp_var("FLOAT")
            mulop_lines = self.tsl.muladd_op_reals(term.op, res_var, left_var, right_var)
        else:
            res_var = self.vm.get_tmp_var("INT")
            mulop_lines = self.tsl.muladd_op_ints(term.op, res_var, left_var, right_var)

        lines.extend(mulop_lines)

        return lines, res_var



    def handle_factor(self, factor: Union[Factor, ID, NUM]) -> Tuple[List[str], str]:
        lines = []
        if isinstance(factor, ID):
            return lines, factor.id
        elif isinstance(factor, NUM):
            return lines, factor.num

        llines, res_var = self.handle_expression(factor.expression)
        lines.extend(llines)

        if factor.cast_to is not None:
            res_var_type = self.vm.get_type(res_var)
            if factor.cast_to.type == res_var_type:
                print(f"Warning: Casting a {factor.cast_to.type} to {factor.cast_to.type}")
            else:
                casted_var = self.vm.get_tmp_var(factor.cast_to.type)
                op = "ITOR" if self.vm.is_float(casted_var) else "RTOI"
                lines.append(f"{op} {casted_var} {res_var}")
                res_var = casted_var

        return lines, res_var

    def handle_assignment_stmt(self, stmt: AssignmentStmt) -> List[str]:
        lines = []
        assign_var = stmt.id.id
        rlines, rvar = self.handle_expression(stmt.expr)
        lines.extend(rlines)

        # Assigning a float to an int --> This is forbidden, raise error
        if self.vm.is_float(rvar) and not self.vm.is_float(assign_var):
            raise AssignFloatToInt
        # assigning an int to a float --> cast the right side to float
        elif not self.vm.is_float(rvar) and self.vm.is_float(assign_var):
            i_rvar = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {i_rvar} {rvar}")
            rvar = i_rvar

        if self.vm.is_float(rvar):
            lines.append(f"RASN {assign_var} {rvar}")
        else:
            lines.append(f"IASN {assign_var} {rvar}")

        return lines

    def handle_output_stmt(self, stmt: OutputStmt) -> List[str]:
        lines, var = self.handle_expression(stmt.expr)
        if not self.vm.is_float(var):
            f_var = self.vm.get_tmp_var("FLOAT")
            lines.append(f"ITOR {f_var} {var}")
            var = f_var
        lines.append(f"RPRT {var}")
        return lines

    def handle_switch_stmt(self, stmt: SwitchStmt) -> List[str]:
        lines, switch_var = self.handle_expression(stmt.switch_on)
        case_lines = []
        for case in stmt.cases.cases:
            enter_var = self.vm.get_tmp_var("INT")
            block_lines = self.handle_stmtlist(case.stmts)

            block_offset = len(block_lines) + 1

            if case.num:    # case.num is None if it's the default block
                case_lines.append(f"INQL {enter_var} {switch_var} {case.num}")

            case_lines.append(f"JMPZ %+{block_offset} {enter_var}")

        # Replace breaks
        end_of_case_off = len(case_lines) + 1
        for ix, line in enumerate(case_lines):
            if line == "%BREAK":
                case_lines[ix] = f"JUMP %+{end_of_case_off}"

        return lines

    def handle_break_stmt(self, stmt: BreakStmt):
        return ["%BREAK"]


















