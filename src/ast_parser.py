import builtins
from dataclasses import dataclass
from typing import Any

from sly import Parser

from errors import *
from lexer import CPLLexer
from quad_translate import QuadTranslator
from models import *

OUTFILE = "output.quad"
_OUTPUT_LINES = []




class CPLParser(Parser):
    """Return the CPL program as AST of models"""

    tokens = CPLLexer.tokens
    literals = CPLLexer.literals

    @_('declarations stmt_block')
    def program(self, p) -> Program:
        return Program(
            declarations=p.declarations,
            stmts=p.stmt_block
        )

    @_('declarations declaration', '')
    def declarations(self, p) -> List[Declaration]:
        if not hasattr(p, 'declarations'):
            return []
        return p.declarations + [p.declaration]

    @_('IdList ":" type ";"')
    def declaration(self, p) -> Declaration:
        return Declaration(id_list=p.IdList, type=p.type)

    @_('INT', 'FLOAT')
    def type(self, p) -> Type:
        return Type(p[0].lower())

    @_('IdList "," ID', 'ID')
    def IdList(self, p) -> IdList:
        idlist = getattr(p, "IdList", IdList())
        idlist.append(ID(p.ID))
        return idlist

    @_('assignment_stmt', 'input_stmt', 'output_stmt', 'if_stmt', 'while_stmt', 'switch_stmt', 'break_stmt', 'stmt_block')
    def stmt(self, p):
        return p[0]

    @_('ID "=" expression ";"')
    def assignment_stmt(self, p) -> AssignmentStmt:
        return AssignmentStmt(id=ID(p.ID), expr=p.expression)

    @_('INPUT "(" ID ")" ";"')
    def input_stmt(self, p) -> InputStmt:
        return InputStmt(ID(p.ID))

    @_('OUTPUT "(" expression ")" ";"')
    def output_stmt(self, p) -> OutputStmt:
        return OutputStmt(p.expression)

    @_('IF "(" boolexpr ")" stmt ELSE stmt')
    def if_stmt(self, p) -> IfStmt:
        if_block = p.stmt0
        else_block = p.stmt1
        if not isinstance(if_block, StmtList):
            if_block = StmtList(stmts=[if_block])
        if not isinstance(else_block, StmtList):
            else_block = StmtList(stmts=[else_block])
        return IfStmt(condition=p.boolexpr, if_block=if_block, else_block=else_block)

    @_('IF "(" boolexpr ")" stmt')
    def if_stmt(self, p) -> IfStmt:
        if_block = p.stmt
        if not isinstance(if_block, StmtList):
            if_block = StmtList(stmts=[if_block])
        return IfStmt(condition=p.boolexpr, if_block=if_block)

    @_('WHILE "(" boolexpr ")" stmt')
    def while_stmt(self, p) -> WhileStmt:
        return WhileStmt(condition=p.boolexpr, stmts=p.stmt)

    @_('SWITCH "(" expression ")" "{" caselist DEFAULT ":" stmtlist "}"')
    def switch_stmt(self, p) -> SwitchStmt:
        return SwitchStmt(
            cases=p.caselist,
            default=Case(stmts=p.stmtlist),
            switch_on=p.expression
        )

    @_('caselist CASE NUM ":" stmtlist', '')
    def caselist(self, p) -> CaseList:
        if not hasattr(p, "CASE"):
            return CaseList()

        caselist = p.caselist
        case = Case(stmts=p.stmtlist, num=NUM(p.NUM))
        caselist.add_case(case)
        return caselist

    @_('BREAK ";"')
    def break_stmt(self, p) -> BreakStmt:
        return BreakStmt()

    @_('"{" stmtlist "}"')
    def stmt_block(self, p) -> StmtList:
        return p.stmtlist

    @_('stmtlist stmt', '')
    def stmtlist(self, p) -> StmtList:
        if not hasattr(p, 'stmtlist'):
            return StmtList()
        stmt_list = p.stmtlist
        stmt_list.append(p.stmt)
        return stmt_list

    @_('boolexpr OR boolterm', 'boolterm')
    def boolexpr(self, p) -> BoolExpr:
        """Return the variable containing the bool expr (type int)"""
        if not hasattr(p, "OR"):
            # If the boolexpr is not true --> jump to the end of the block
            return BoolExpr(right=p.boolterm)

        return BoolExpr(
            left=p.boolexpr,
            right=p.boolterm
        )

    @_('boolterm AND boolfactor', 'boolfactor')
    def boolterm(self, p) -> BoolTerm:
        """Return the variable containing the bool expr (type int)"""
        if not hasattr(p, "AND"):
            return BoolTerm(right=p.boolfactor)

        return BoolTerm(
            left=p.boolterm,
            right=p.boolfactor
        )

    @_('expression RELOP expression')
    def boolfactor(self, p) -> BoolFactorRelop:
        return BoolFactorRelop(left=p.expression0, right=p.expression1, relop=p.RELOP)


    @_('NOT "(" boolexpr ")"')
    def boolfactor(self, p) -> BoolFactorNot:
        """Return the variable containing the expression (type int)"""
        return BoolFactorNot(boolexpr=p.boolexpr)

    @_('expression ADDOP term', 'term')
    def expression(self, p) -> Expression:
        """Return a variable containing the expression result"""
        if not hasattr(p, "ADDOP"):
            return Expression(right=p.term)

        return Expression(left=p.expression, op=p.ADDOP, right=p.term)

    @_('term MULOP factor', 'factor')
    def term(self, p) -> Term:
        """Return a variable containing the expression result"""
        if not hasattr(p, "MULOP"):
            return Term(right=p.factor)

        return Term(op=p.MULOP, left=p.term, right=p.factor)

    @_('CAST "(" expression ")"', '"(" expression ")"')
    def factor(self, p) -> Factor:
        """Return the variable containing the factor"""
        if not hasattr(p, "CAST"):
            return Factor(expression=p.expression)

        if p.CAST not in ("static_cast<int>", "static_cast<float>"):
            raise ValueError(f"Invalid type {p.CAST}")

        cast_type = Type("int") if p.CAST == "static_cast<int>" else Type('float')
        return Factor(expression=p.expression, cast_to=cast_type)

    @_('ID')
    def factor(self, p) -> ID:
        return ID(p[0])

    @_('NUM')
    def factor(self, p) -> NUM:
        return NUM(p[0])

    def error(self, p, message=None):
        if not p:
            print('End of File!')
            raise EOFError

        if not message:
            message = f"Unexpected token '{p.value}'"
        raise SyntaxException(f"Parser error on line {p.lineno}, chars [{p.index}, {p.end}]: {message}")


    def parse(self, tokens):
        ast = super().parse(tokens)
        return ast


if __name__ == "__main__":

    parser = CPLParser()
    lexer = CPLLexer()
    try:
        text = input("calc > ")
        result = parser.parse(lexer.tokenize(text))
        parser.on_finish()
        print(result)
    except EOFError:
        pass