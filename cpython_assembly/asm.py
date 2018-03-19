"""
Let's do this!

"""
from dis import (
    opmap, HAVE_ARGUMENT, hasjrel, hasjabs, haslocal, hasname, hasconst
)
import types

def asm(f):
    """
    Decorator to assemble a function from a docstring in my imaginary asm format for
    python bytecode
    """
    doc, source = f.__doc__.split(':::asm')
    co_in = f.__code__

    machine = Assembler(source, co_in.co_varnames)
    co_gen = machine.assemble()

    argcount = 1
    kwonlyargcount = 0
    nlocals = 1
    stacksize = co_gen.co_stacksize
    flags = 67
    codestring = co_gen.co_code
    constants = co_gen.co_consts
    names = co_gen.co_names
    varnames = co_gen.co_varnames
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
    result.__defaults__ = f.__defaults__
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
        self.locals = list(varnames)

    def assemble(self):
        """
        Assemble source into a types.CodeType object and return it
        """
        self.assemble_stacksize()
        self.assemble_locals()
        self.assemble_names()
        self.assemble_consts()
        self.assemble_code()

        return types.CodeType(
            len(self.varnames),
            0,
            0,
            self.stacksize,
            67,
            self.code,
            self.consts,
            self.names,
            self.varnames,
            '',
            '',
            0,
            b''
        )

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

    def assemble_locals(self):
        """
        Local variables in addition to parameters

        These can be multiple on one line, comma separated
        """
        for line in self.src.get('locals', ()):
            self.locals.extend([s.strip() for s in line.split(',')])
        self.varnames = tuple(self.locals)

    def assemble_names(self):
        """
        Names

        These can be multiple on one line, comma separated
        """
        names = []
        for line in self.src.get('names', ()):
            names.extend([s.strip() for s in line.split(',')])
        self.names = tuple(names)

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
                bytecode.append(self._determine_argument(tokens[1], opcode))
            else:
                bytecode.append(0)
            pos += 2

        self.bytecode = bytecode
        self._fix_arguments()

        self.code = bytes(bytecode)

    def _determine_argument(self, arg, opcode):
        """
        Determine what to do with an argument string depending on the opcode

        If the argument is an integer convert and return it
        """
        try:
            return int(arg)
        except ValueError:
            pass

        if opcode in hasjabs:
            return ('jabs', arg)
        if opcode in hasjrel:
            return ('jrel', arg)
        if opcode in haslocal:
            return ('local', arg)
        if opcode in hasname:
            return ('name', arg)
        if opcode in hasconst:
            return ('const', arg)

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

    def _fix_arguments(self):
        """
        Replace target tuples in bytecode with correct positions or
        variable indices
        """
        for idx in range(0, len(self.bytecode), 2):
            arg = self.bytecode[idx+1]
            if not isinstance(arg, tuple):
                continue
            if arg[0] == 'jabs':
                self.bytecode[idx+1] = self.targets[arg[1]]
            elif arg[0] == 'jrel':
                self.bytecode[idx+1] = (
                    self.targets[arg[1]] - (idx + 2)
                )
            elif arg[0] == 'local':
                self.bytecode[idx+1] = self.locals.index(arg[1])
            elif arg[0] == 'name':
                self.bytecode[idx+1] = self.names.index(arg[1])
            elif arg[0] == 'const':
                self.bytecode[idx+1] = self.consts_alias[arg[1]]


if __name__ == '__main__':

    @asm
    def testfunc(x):
        """
        Subtract 3 from x until it is less than 4, then
        return the result
        :::asm

        .stacksize 2
        .consts
           four=4
           three=3

        .code
           SETUP_LOOP               after_loop
        start_loop:
           LOAD_FAST                x
           LOAD_CONST               four
           COMPARE_OP               4
           POP_JUMP_IF_FALSE        end_loop

           LOAD_FAST                x
           LOAD_CONST               three
           INPLACE_SUBTRACT
           STORE_FAST               x
           JUMP_ABSOLUTE            start_loop
        end_loop: 
           POP_BLOCK
        after_loop:
           LOAD_FAST                x
           RETURN_VALUE
        """

    print(testfunc(14))
