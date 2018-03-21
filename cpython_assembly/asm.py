"""
Let's do this!

"""
from dis import (
    opmap, HAVE_ARGUMENT, hasjrel, hasjabs, haslocal, hasname, hasconst
)
import types

CO_FLAGS = {
    'OPTIMIZED': 0x1,
    'NEWLOCALS': 0x2,
    'VARARGS': 0x4,
    'VARKEYWORDS': 0x8,
    'NESTED': 0x10,
    'GENERATOR': 0x20,
    'NOFREE': 0x40,
    'COROUTINE': 0x80,
    'ITERABLE_COROUTINE': 0x100,
    'ASYNC_GENERATOR': 0x200
}

def asm(f):
    """
    Decorator to assemble a function from a docstring in my imaginary asm
    format for python bytecode
    """
    doc, source = f.__doc__.split(':::asm')
    co_in = f.__code__

    machine = Assembler(source, co_in.co_varnames)
    co_gen = machine.assemble()

    co_out = types.CodeType(
        len(co_in.co_varnames),
        0,
        co_gen.co_nlocals,
        co_gen.co_stacksize,
        co_gen.co_flags,
        co_gen.co_code,
        co_gen.co_consts,
        co_gen.co_names,
        co_gen.co_varnames,
        co_in.co_name,
        co_in.co_filename,
        co_in.co_firstlineno,
        b'\x00\x01'
    )

    result = types.FunctionType(co_out, f.__globals__) 
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
        self.argcount = len(varnames)
        self.locals = list(varnames)
        self.flags = 0

    def assemble(self):
        """
        Assemble source into a types.CodeType object and return it
        """
        self.assemble_stacksize()
        self.assemble_flags()
        self.assemble_locals()
        self.assemble_names()
        self.assemble_consts()
        self.assemble_code()

        return types.CodeType(
            self.argcount,
            0,
            len(self.varnames),
            self.stacksize,
            self.flags,
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

    def assemble_flags(self):
        """
        Flags can be given as the name of the flag or hexidecimal
        literal, i.e. 0x4 

        These can be multiple on one line, comma separated
        """
        for line in self.src.get('flags', ()):
            flags = (s.strip() for s in line.split(','))
            for flagstr in flags:
                try:
                    flag = int(flagstr, 16)
                except ValueError:
                    flag = CO_FLAGS[flagstr.upper()]
                self.flags |= flag
                
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
        # first pass, replace non-int arguments with integer values
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

        # second pass (quadratic), use EXTENDED_ARG ops as needed
        # to reduce down arguments to < 256
        reduced = False
        while not reduced:
            reduced = self._reduce_next_arg()

    def _reduce_next_arg(self):
        """
        Locate the first instruction with an argument over 255 and
        reduce it using EXTENDED_ARG
        """
        reduced = True
        for idx in range(0, len(self.bytecode), 2):
            arg = self.bytecode[idx+1]
            if arg > 255:
                reduced = False
                if idx > 0 and idx-2 == opmap['EXTENDED_ARG']:
                    self.bytecode[idx-1] += arg >> 8
                    self.bytecode[idx+1] %= 256
                else:
                    self.bytecode[idx+1] %= 256
                    self._insert_extended_arg(idx, arg >> 8)
                break
        return reduced

    def _insert_extended_arg(self, pos, val):
        """
        Insert an EXTENDED_ARG opcode at position pos with argument val
        Then adjust jabs and rel values.
        """
        self.bytecode.insert(pos, val)
        self.bytecode.insert(pos, opmap['EXTENDED_ARG'])
        for idx in range(0, pos, 2):
            if (self.bytecode[idx] in hasjrel and 
                self._get_full_arg(idx) + idx + 2 > pos
            ):
                self.bytecode[idx+1] += 2

        for idx in range(0, len(self.bytecode), 2):
            if self.bytecode[idx] in hasjabs and self._get_full_arg(idx) > pos:
                self.bytecode[idx+1] += 2

    def _get_full_arg(self, pos):
        """
        Get the full argument value (augmented by previous EXTENDED_ARG
        instructions) of the instruction at position pos)
        """
        arg = self.bytecode[pos+1]
        mult = 1
        while pos > 0 and self.bytecode[pos-2] == opmap['EXTENDED_ARG']:
            mult *= 256
            arg += self.bytecode[pos-1] * mult
            pos -= 2
        return arg
