"""
Let's do this!

"""
from dis import opmap, HAVE_ARGUMENT
import types

def asm(f):
    """
    Decorator to assemble a function from a docstring in my imaginary asm format for
    python bytecode
    """
    doc, source = f.__doc__.split(':::asm')
    co_in = f.__code__

    sections = preprocess(source)

    argcount = 1
    kwonlyargcount = 0
    nlocals = 1
    stacksize = 2
    flags = 67
    codestring = b'|\x00d\x01\x17\x00S\x00'
    constants = (None, 4)
    names = ()
    varnames = co_in.co_varnames
    filename = co_in.co_filename
    name = co_in.co_name
    filename = co_in.co_filename
    firstlineno = co_in.co_firstlineno
    lnotab = b'\x00\x01'
    
    co_out = types.CodeType(
        argcount,
        kwonlyargcount,
        nlocals,
        stacksize,
        flags,
        codestring,
        constants,
        names,
        varnames,
        filename,
        name,
        firstlineno,
        lnotab
    )

    result = types.FunctionType(co_out, globals())
    result.__doc__ = doc
    return result


def preprocess(source):
    """
    Remove comments, dedent, split into lines and sections
    """
    lines = [line.split(';')[0].strip() for line in source.splitlines()]
    sections = {'unknown': []}
    current_section = 'unknown'
    for line in lines:
        if not line:
            continue
        if line.startswith('.'):
                sections[line[1:]] = []
                current_section = line[1:]
                continue
        sections[current_section].append(line)

    return sections


class Assembler:
    """
    I *think* I want to make this a class
    """
    def __init__(self, source=None, varnames=()):
        """
        Can be passed source to be preprocessed or
        you can add sections manually (mainly for
        testing convenience) 
        """
        if source is not None:
            self.src = preprocess(source)
        else:
            self.src = {}

        self.code = None
        self.varnames = varnames

    def assemble_code(self):
        """
        Assuming everything else has gone correctly, produce the bytecode
        """
        bytecode = []
        pos = 0
        for line in self.src['code']:
            tokens = line.split()
            op = tokens[0].upper()
            opcode = opmap[op]
            bytecode.append(opcode)
            if opcode >= HAVE_ARGUMENT:
                bytecode.append(int(tokens[1]))
            else:
                bytecode.append(0)

        self.code = bytes(bytecode)


if __name__ == '__main__':

    @asm
    def testfunc():
        """
        Some docstring

        :::asm

        Some code
        """

    print(testfunc(4))