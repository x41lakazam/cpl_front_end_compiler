
class QuadTranslator:

    def __init__(self, outfile="outfile.quad"):
        self._output_lines = []
        self.outfile = outfile

    def output(self):
        with open(self.outfile, 'w') as fp:
            for l in self._output_lines:
                fp.write(f"{l}\n")

        print(f"Wrote output in {self.outfile}")

    @property
    def offset(self):
        return len(self._output_lines)

    def gen(self, data):
        self._output_lines.append(data)

    def and_(self, res_var, var1, var2):
        """res_var = var1 && var2
        1: res_var = 0
        2: JMPZ var1 5
        3: JMPZ var2 5
        4: res_var = 1
        5: <end_of_block>
        """
        end_of_block = self.offset + 5
        self.gen(f"IASN {res_var} 0")
        self.gen(f"JMPZ {var1} {end_of_block}")
        self.gen(f"JMPZ {var2} {end_of_block}")
        self.gen(f"IASN {res_var} 1")

    def or_(self, res_var, var1, var2):
        """res_var = var1 || var2
        1: res_var = 0
        2: JMPZ var1 4
        3: res_var = 1
        4: JMPZ var2 6
        5: res_var = 1
        6: <end_of_block>
        """
        self.gen(f"IASN {res_var} 0")
        self.gen(f"JMPZ {var1} {self.offset+2}")
        self.gen(f"IASN {res_var} 1")
        self.gen(f"JMPZ {var2} {self.offset+2}")
        self.gen(f"IASN {res_var} 1")


    def le_(self, res_var, var1, var2):
        """ res_var = 1 if var1 <= var2 else 0
        1: res_var = var1 == var2
        2: JMPZ 4
        3: JMP 5 // jmp to end
        4: res_var = var1 < var2
        5: <END>
        """
        end_of_block = self.offset + 5
        self.gen(f"IEQL {res_var} {var1} {var2}")
        self.gen(f"JMPZ {res_var} {self.offset + 2}")
        self.gen(f"JMP {end_of_block}")
        self.gen(f"ILSS {res_var} {var1} {var2}")

        return


    def ge_(self, res_var, var1, var2):
        """ res_var = 1 if var1 >= var2 else 0
        1: res_var = var1 == var2
        2: JMPZ 4
        3: JMP 5 // jmp to end
        4: res_var = var1 > var2
        5: <END>
        """
        end_of_block = self.offset+5
        self.gen(f"IEQL {res_var} {var1} {var2}")
        self.gen(f"JMPZ {res_var} {self.offset+2}")
        self.gen(f"JMP {end_of_block}")
        self.gen(f"IGRT {res_var} {var1} {var2}")

        return

    def relop(self, op, res_var, var1, var2):
        relop_map= {
            "==": "IEQL",
            "!=": "INQL",
            "<": "ILSS",
            ">": "IGRT",
            ">=": self.ge_,
            "<=": self.le_,
        }
        quad_op = relop_map.get(op)
        if hasattr(quad_op, "__call__"):
            quad_op(res_var, var1, var2)
        else:
            self.gen(f"{quad_op} {res_var} {var1} {var2}")

        return

    def muladd_op(self, op, res_var, var1, var2):
        self.map = {
            "*": "IMLT",
            "/": "IDIV",
            "+": "IADD",
            "-": "ISUB"
        }
        op_name = self.map.get(op)
        if not op_name:
            raise # UnknownOperation(f"No such operation {op}")

        self.gen(f"{op_name} {res_var} {var1} {var2}")


