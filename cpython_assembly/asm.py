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

    co_out = Assembler(source, co_in.co_varnames)

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

    allow first line of section to be after the section header,
    for example ``.stacksize 4``
    """
    lines = [line.split(';')[0].strip() for line in source.splitlines()]
    sections = {'unknown': []}
    current_section = 'unknown'
    for line in lines:
        if not line:
            continue
        if line.startswith('.'):
                tokens = line[1:].split()
                sections[tokens[0]] = []
                current_section = tokens[0]
                if len(tokens) > 1:
                    sections[tokens[0]].append(''.join(tokens[1:]))
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

        self.targets = {}
        self.code = None
        self.varnames = varnames

    def assemble(self):
        """
        Assemble source into a types.CodeType object and return it
        """
        self.assemble_consts()
        self.assemble_code()

    def assemble_stacksize(self):
        """
        obviously - come back to this when its time to
        add reasonable error messages
        """
        self.stacksize = int(self.src['stacksize'][0])
        
    def assemble_consts(self):
        """
        Consts must be in the .consts section one per line in
        the form ``name=expression`` to give an alias to the constant
        or just ``expression`` if you don't care to give it an alias
        and refer to it numerically in the assembly code.

        As with the CPython compiler, the first constant in the list
        will always be None. This will be given the alias "none"
        """
        consts = [None]
        aliases = {'none': 0}
        for idx, line in enumerate(self.src['consts']):
            tokens = [t.strip() for t in line.split('=')]
            if len(tokens) == 1:
                consts.append(eval(tokens[0]))
            else:
                consts.append(eval(tokens[1]))
                aliases[tokens[0].lower()] = idx + 1

        self.consts = tuple(consts)
        self.consts_alias = aliases

    def assemble_code(self):
        """
        Assuming everything else has gone correctly, produce the bytecode
        """
        bytecode = []
        pos = 0
        for line in self.src['code']:

            line = self._extract_target(line, pos)
            if not line:
                continue

            tokens = line.split()
            op = tokens[0].upper()
            opcode = opmap[op]
            bytecode.append(opcode)
            if opcode >= HAVE_ARGUMENT:
                bytecode.append(int(tokens[1]))
            else:
                bytecode.append(0)
            pos += 2

        self.code = bytes(bytecode)

    def _extract_target(self, line, pos):
        """
        Extract a target (if any) from the line and return what remains.
        Add the target position to the dict of targets.
        """
        tokens = line.split(':')
        if len(tokens) == 1:
            return line
        target, ops = tokens
        self.targets[target] = pos
        return ops


if __name__ == '__main__':

    @asm
    def testfunc():
        """
        Some docstring

        :::asm

        Some code
        """

    print(testfunc(4))
