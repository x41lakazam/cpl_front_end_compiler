from errors import BreakOutsideOfLoop


class QuadTranslator:

    def and_(self, res_var, var1, var2):
        """res_var = var1 && var2
        1: res_var = 0
        2: JMPZ var1 5
        3: JMPZ var2 5
        4: res_var = 1
        5: <end_of_block>
        """
        return [
            f"IASN {res_var} 0",
            f"JMPZ %+3 {var1} ",
            f"JMPZ %+2 {var2}",
            f"IASN {res_var} 1",
        ]

    def or_(self, res_var, var1, var2):
        """res_var = var1 || var2
        1: res_var = 0
        2: JMPZ var1 4
        3: res_var = 1
        4: JMPZ var2 6
        5: res_var = 1
        6: <end_of_block>
        """
        return [
            f"IASN {res_var} 0",
            f"JMPZ %+2 {var1}",
            f"IASN {res_var} 1",
            f"JMPZ %+2 {var2}",
            f"IASN {res_var} 1",
        ]


    def le_ints(self, res_var, var1, var2):
        """ res_var = 1 if var1 <= var2 else 0
        1: res_var = var1 == var2
        2: JMPZ 4
        3: JMP 5 // jmp to end
        4: res_var = var1 < var2
        5: <END>
        """
        return [
            f"IEQL {res_var} {var1} {var2}",
            f"JMPZ %+2 {res_var}",
            f"JUMP %+2",
            f"ILSS {res_var} {var1} {var2}",
        ]

    def le_reals(self, res_var, var1, var2):
        """ res_var = 1 if var1 <= var2 else 0
        1: res_var = var1 == var2
        2: JMPZ 4
        3: JMP 5 // jmp to end
        4: res_var = var1 < var2
        5: <END>
        """
        return [
            f"REQL {res_var} {var1} {var2}",
            f"JMPZ %+2 {res_var}",
            f"JUMP %+2",
            f"RLSS {res_var} {var1} {var2}",
        ]

    def ge_reals(self, res_var, var1, var2):
        """ res_var = 1 if var1 >= var2 else 0
        1: res_var = var1 == var2
        2: JMPZ 4
        3: JMP 5 // jmp to end
        4: res_var = var1 > var2
        5: <END>
        """
        return [
            f"REQL {res_var} {var1} {var2}",
            f"JMPZ %+2 {res_var}",
            f"JUMP %+2",
            f"RGRT {res_var} {var1} {var2}",
        ]

    def ge_ints(self, res_var, var1, var2):
        """ res_var = 1 if var1 >= var2 else 0
        1: res_var = var1 == var2
        2: JMPZ 4
        3: JMP 5 // jmp to end
        4: res_var = var1 > var2
        5: <END>
        """
        return [
            f"IEQL {res_var} {var1} {var2}",
            f"JMPZ %+2 {res_var}",
            f"JUMP %+2",
            f"IGRT {res_var} {var1} {var2}",
        ]

    def relop_ints(self, op, res_var, var1, var2):

        relop_map = {
            "==": "IEQL",
            "!=": "INQL",
            "<": "ILSS",
            ">": "IGRT",
            ">=": self.ge_ints,
            "<=": self.le_ints,
        }
        return self._relop(op, res_var, var1, var2, relop_map)

    def relop_reals(self, op, res_var, var1, var2):
        relop_map= {
            "==": "REQL",
            "!=": "RNQL",
            "<": "RLSS",
            ">": "RGRT",
            ">=": self.ge_reals,
            "<=": self.le_reals,
        }
        return self._relop(op, res_var, var1, var2, relop_map)

    def _relop(self, op, res_var, var1, var2, relop_map):
        quad_op = relop_map.get(op)
        if hasattr(quad_op, "__call__"):
            r = quad_op(res_var, var1, var2)
        else:
            r = f"{quad_op} {res_var} {var1} {var2}"

        if not isinstance(r, list):
            r = [r]

        return r

    def muladd_op_ints(self, op, res_var, var1, var2):
        map = {
            "*": "IMLT",
            "/": "IDIV",
            "+": "IADD",
            "-": "ISUB"
        }
        return self._muladd_op(op, res_var, var1, var2, map)

    def muladd_op_reals(self, op, res_var, var1, var2):
        map = {
            "*": "RMLT",
            "/": "RDIV",
            "+": "RADD",
            "-": "RSUB"
        }
        return self._muladd_op(op, res_var, var1, var2, map)

    def _muladd_op(self, op, res_var, var1, var2, map):
        op_name = map.get(op)
        if not op_name:
            raise # UnknownOperation(f"No such operation {op}")

        r = f"{op_name} {res_var} {var1} {var2}"

        if not isinstance(r, list):
            r = [r]

        return r



