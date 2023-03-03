class BaseExc(Exception):
    pass


class UnknownVariable(BaseExc):
    def __init__(self, varname):
        message = f"Undefined variable {varname}"
        super().__init__(message)

class BreakOutsideOfLoop(BaseExc):
    def __init__(self):
        message = f"Break used outside of loop or switch"
        super().__init__(message)
