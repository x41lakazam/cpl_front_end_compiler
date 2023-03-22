from __future__ import annotations
from sly.lex import Token

from dataclasses import dataclass, field
from typing import Any, List, Optional, Union



@dataclass
class Expr:
    pass


@dataclass
class ErrorToken(Expr):
    token: Token

@dataclass
class Program(Expr):
    declarations: List[Declaration]
    stmts: StmtList


@dataclass
class Type(Expr):
    type: str

    def __post_init__(self):
        self.type = self.type.upper()


@dataclass
class ID(Expr):
    id: str


@dataclass
class NUM(Expr):
    num: str


@dataclass
class IdList(Expr):
    ids: List[ID] = field(default_factory=list)

    def append(self, ID):
        self.ids.append(ID)


@dataclass
class Declaration(Expr):
    id_list: IdList
    type: Type


@dataclass
class Stmt(Expr):
    pass


@dataclass
class StmtList(Expr):
    stmts: List[Stmt] = field(default_factory=list)

    def append(self, stmt):
        self.stmts.append(stmt)


@dataclass
class IfStmt(Expr):
    condition: BoolExpr
    if_block: StmtList
    else_block: Optional[StmtList] = None


@dataclass
class WhileStmt(Expr):
    condition: BoolExpr
    stmts: StmtList

@dataclass
class InputStmt(Stmt):
    id: ID


@dataclass
class BreakStmt(Stmt):
    pass


@dataclass
class OutputStmt(Stmt):
    expr: Expression

@dataclass
class AssignmentStmt(Stmt):
    """id = expr"""
    id: ID
    expr: Expression


@dataclass
class Term(Expr):
    right: Union[Factor, ID, NUM]
    op: Optional[str] = None
    left: Optional[Term] = None


@dataclass
class Expression(Expr):
    right: Term
    op: Optional[str] = None
    left: Optional[Expression] = None


@dataclass
class Factor(Expr):
    expression: Expression
    cast_to: Optional[Type] = None


@dataclass
class Case(Expr):
    stmts: StmtList
    num: Optional[NUM] = None # None if default


@dataclass
class CaseList(Expr):
    cases: List[Case] = field(default_factory=list)

    def add_case(self, case: Case):
        self.cases.append(case)


@dataclass
class SwitchStmt(Expr):
    switch_on: Expression
    default: Case
    cases: CaseList

    def add_default_case(self, case: Case):
        self.default = case

# BOOL


@dataclass
class BoolFactorRelop(Expr):
    left: Expression
    right: Expression
    relop: str


@dataclass
class BoolFactorNot(Expr):
    boolexpr: BoolExpr


@dataclass
class BoolExpr(Expr):
    """Disjunction"""
    right: BoolTerm
    left: Optional[BoolExpr] = None


@dataclass
class BoolTerm(Expr):
    """Conjunction"""
    right: Union[BoolFactorNot, BoolFactorRelop]
    left: Optional[BoolTerm] = None

