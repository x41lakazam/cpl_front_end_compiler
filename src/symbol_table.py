import re

def resolve_offsets(lines):
    for ix, line in enumerate(lines):
        # Increment offsets
        line = re.sub(
            r"%\+(\d+)",
            lambda exp: str(int(exp.group(1)) + ix+1),
            line
        )
        line = re.sub(
            r"%-(\d+)",
            lambda exp: str(ix-int(exp.group(1))+1),
            line
        )
        lines[ix] = line

    return lines
