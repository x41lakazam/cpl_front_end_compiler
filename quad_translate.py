from errors import BreakOutsideOfLoop


class QuadTranslator:

    def __init__(self, outfile="outfile.quad"):
        self._output_lines = []
        self.outfile = outfile

    def output(self, with_index=True, file=None):
        file = file or self.outfile
        with open(file, 'w') as fp:
            for ix, l in enumerate(self._output_lines):
                if with_index:
                    l = f"{ix+1}:\t{l}"
                fp.write(f"{l}\n")

        print(f"Wrote output in {self.outfile}")

    @property
    def offset(self):
        return len(self._output_lines)

    def gen(self, data):
        self._output_lines.append(data)

    @property
    def last_endblock_tag(self):
        for i in range(self.offset-1, 0, -1):
            if self._output_lines[i] == "%ENDBLOCK%":
                return i

        return None

    @property
    def last_break_tag(self):
        for i in range(self.offset-1, 0, -1):
            if self._output_lines[i] == "%BREAK%":
                return i

        return None

    @property
    def last_nextcase_tag(self):
        for i in range(self.offset-1, 0, -1):
            if "%NEXTCASE%" in self._output_lines[i]:
                return i

        return None

    @property
    def last_switchvar_tag(self):
        for i in range(self.offset-1, 0, -1):
            if "%SWITCHVAR%" in self._output_lines[i]:
                return i

        return None

    @property
    def last_switchcase_tag(self):
        for i in range(self.offset-1, 0, -1):
            if "%SWITCHCASE%" in self._output_lines[i]:
                return i

        return None
    @property
    def last_end_tag(self):
        for i in range(self.offset-1, 0, -1):
            if "%END%" in self._output_lines[i]:
                return i

        return None


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

    def backref_offset(self, off):
        """Update the last %END% tag with the next offset"""
        if not self.last_end_tag:
            raise SyntaxError

        self._output_lines[self.last_end_tag] = self._output_lines[self.last_end_tag].replace("%END%", str(off))

    def remove_last_line(self):
        self._output_lines.pop(-1)

    def replace_last_endblock(self, line):
        """Replace the last %ENDBLOCK% by another line and return its offset"""
        curr_off = self.last_endblock_tag
        self._output_lines[curr_off] = line

        return curr_off

    def replace_last_break(self, line):
        """Replace the last %BREAK% line by another line and return its offset"""
        curr_off = self.last_break_tag
        if not curr_off:
            # No break, ignoring
            return
        self._output_lines[curr_off] = line
        return curr_off

    def replace_last_nextcase(self, val):
        """Replace the last occurence of %NEXTCASE% by val and return offset"""
        off = self.last_nextcase_tag
        if not off:
            return  # Ignore

        self._output_lines[off] = self._output_lines[off].replace("%NEXTCASE%", str(val))

    def replace_last_switchcase(self, val):
        """Replace the last occurence of %SWITCHCASE% by val and return offset"""
        off = self.last_switchcase_tag
        if not off:
            return  # ignore

        self._output_lines[off] = self._output_lines[off].replace("%SWITCHCASE%", str(val))
        return off

    def replace_all_switchvars(self, val):
        """Replace all the preceding occurences of %SWITCHCASE% by val"""
        off = self.last_switchvar_tag

        while off is not None:
            self._output_lines[off] = self._output_lines[off].replace("%SWITCHVAR%", str(val))
            off = self.last_switchvar_tag

    def replace_all_breaks(self, line):
        """Replace all the preceding lines with %BREAK% by <line>"""
        off = self.last_break_tag

        while off is not None:
            self._output_lines[off] = line
            off = self.last_break_tag

    def on_finish_check(self):
        for line in self._output_lines:
            if "%BREAK%" in line:
                raise BreakOutsideOfLoop()

    def delete_last_next_and_switch_case(self):
        self._output_lines.pop(self.last_nextcase_tag)
        self._output_lines.pop(self.last_switchcase_tag)

