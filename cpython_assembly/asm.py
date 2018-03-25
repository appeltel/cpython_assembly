"""
Let's do this!

"""
from dis import (
    opmap, HAVE_ARGUMENT,
    hasjrel, hasjabs, haslocal, hasname, hasconst, hasfree,
    get_instructions
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


def asm(*args):
    """
    Decorator to assemble a function from a docstring in my imaginary asm
    format for python bytecode
    """
    if len(args) == 1 and callable(args[0]):
        return _asm(args[0], ())

    else:
        def decor(f):
            return _asm(f, *args)

        return decor


def _asm(f, *args):
    """
    Interior decorator 
    """
    doc, source = f.__doc__.split(':::asm')
    co_in = f.__code__

    machine = Assembler(
        source,
        co_in.co_varnames,
        doc=doc,
        fl=co_in.co_firstlineno,
        args=args
    )
    co_gen = machine.assemble()

    co_out = types.CodeType(
        co_in.co_argcount,
        co_in.co_kwonlyargcount,
        co_gen.co_nlocals,
        co_gen.co_stacksize,
        co_gen.co_flags,
        co_gen.co_code,
        co_gen.co_consts,
        co_gen.co_names,
        co_gen.co_varnames,
        co_in.co_name,
        co_in.co_filename,
        co_gen.co_firstlineno,
        co_gen.co_lnotab,
        co_gen.co_freevars,
        co_gen.co_cellvars
    )

    # feel kinda iffy about this
    if co_gen.co_freevars:
        return co_out

    result = types.FunctionType(
        code=co_out,
        globals=f.__globals__,
        argdefs=f.__defaults__,
        name=co_in.co_name,
    ) 
    result.__doc__ = doc
    return result


def preprocess(source):
    """
    Remove comments, dedent, split into lines and sections, record line
    numbers with each line for the code section

    allow first line of section to be after the section header,
    for example ``.stacksize 4``
    """
    lines = [line.split(';')[0].strip() for line in source.splitlines()]
    sections = {'unknown': []}
    current_section = 'unknown'
    for lno, line in enumerate(lines):
        if not line:
            continue
        if line.startswith('.'):
                tokens = line[1:].split()
                sections[tokens[0]] = []
                current_section = tokens[0]
                if len(tokens) > 1:
                    if current_section == 'code':
                        sections[tokens[0]].append((lno, ''.join(tokens[1:])))
                    else:
                        sections[tokens[0]].append(''.join(tokens[1:]))
                continue
        if current_section == 'code':
            sections[current_section].append((lno, line))
        else:
            sections[current_section].append(line)

    return sections


class Assembler:
    """
    I *think* I want to make this a class
    """
    def __init__(self, source=None, varnames=(), doc=None, fl=0, args=None):
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
        self.doc = doc
        self.fl = fl
        self.args = args
        if doc is not None:
            self.lnodoc = len(doc.splitlines())
        else:
            self.lnodoc = 0

    def assemble(self):
        """
        Assemble source into a types.CodeType object and return it
        """
        self.assemble_stacksize()
        self.assemble_flags()
        self.assemble_locals()
        self.assemble_names()
        self.assemble_freevars()
        self.assemble_cellvars()
        self.assemble_consts()
        self.assemble_code()
        self.assemble_lnotab()

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
            self.fl,
            self.lnotab,
            self.freevars,
            self.cellvars
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
        will be the docstring. This will be given the name "__doc__"
        """
        consts = [self.doc]
        aliases = {'__doc__': 0}
        for idx, line in enumerate(self.src.get('consts', ())):
            tokens = [t.strip() for t in line.split('=')]
            args = self.args
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

    def assemble_freevars(self):
        """
        Closure stuff

        These can be multiple on one line, comma separated
        """
        freevars = []
        for line in self.src.get('freevars', ()):
            freevars.extend([s.strip() for s in line.split(',')])
        self.freevars = tuple(freevars)

    def assemble_cellvars(self):
        """
        Closure stuff

        These can be multiple on one line, comma separated
        """
        cellvars = []
        for line in self.src.get('cellvars', ()):
            cellvars.extend([s.strip() for s in line.split(',')])
        self.cellvars = tuple(cellvars)

    def assemble_code(self):
        """
        Assuming everything else has gone correctly, produce the bytecode
        """
        bytecode = []
        bytecode_lno = []
        pos = 0
        for lno, line in self.src['code']:

            line = self._extract_target(line, pos)
            if not line:
                continue

            tokens = line.split()
            op = tokens[0].upper()
            opcode = opmap[op]
            bytecode.append(opcode)
            bytecode_lno.append(lno)
            if opcode >= HAVE_ARGUMENT:
                arg = tokens[1]
                try:
                    arg = int(arg)
                except ValueError:
                    pass
                bytecode.append(arg)
            else:
                bytecode.append(0)
            pos += 2

        self.bytecode = bytecode
        self.bytecode_lno = bytecode_lno
        self._fix_arguments()
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

    def _fix_arguments(self):
        """
        Replace target tuples in bytecode with correct positions or
        variable indices
        """
        # first pass, replace non-int arguments with integer values
        for idx in range(0, len(self.bytecode), 2):
            arg = self.bytecode[idx+1]
            if not isinstance(arg, str):
                continue
            if self.bytecode[idx] in hasjabs:
                self.bytecode[idx+1] = self.targets[arg]
            elif self.bytecode[idx] in hasjrel:
                self.bytecode[idx+1] = (
                    self.targets[arg] - (idx + 2)
                )
            elif self.bytecode[idx] in haslocal:
                self.bytecode[idx+1] = self.locals.index(arg)
            elif self.bytecode[idx] in hasname:
                self.bytecode[idx+1] = self.names.index(arg)
            elif self.bytecode[idx] in hasconst:
                self.bytecode[idx+1] = self.consts_alias[arg]
            elif self.bytecode[idx] in hasfree:
                self.bytecode[idx+1] = self._find_freecell(arg)

        # second pass (quadratic), use EXTENDED_ARG ops as needed
        # to reduce down arguments to < 256
        reduced = False
        while not reduced:
            reduced = self._reduce_next_arg()

    def _find_freecell(self, arg):
        """
        Locate the free/cell index of the free/cell variable by name
        """
        if arg in self.cellvars:
            return self.cellvars.index(arg)
        if arg in self.freevars:
            return self.freevars.index(arg) + len(self.cellvars)

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
        self.bytecode_lno.insert(pos // 2, 0)
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

    def assemble_lnotab(self):
        """
        This is a hot mess
        """
        lnotab = []
        current = 0
        dist = 2
        last_entry = 0
        for entry in self.bytecode_lno:
            if entry == 0:
                dist += 2
                continue
            entry += self.lnodoc + 1
            more_entry = 0
            while entry - last_entry > 127:
                lnotab.append(0)
                lnotab.append(127)
                entry -= 127; more_entry += 127
            lnotab.append(current)
            lnotab.append(entry - last_entry)
            last_entry = entry + more_entry
            current = dist
            dist = 2

        self.lnotab = bytes(lnotab)


def dis(func):
    """
    Disassemble a function into cpython_assembly format
    """
    co = func.__code__
    result = []

    if func.__doc__:
        for line in func.__doc__.splitlines():
            result.append(line)
    result.append('    :::asm')

    result.append('    .stacksize {0}'.format(co.co_stacksize))
    flags = []
    for key in CO_FLAGS:
        if co.co_flags & CO_FLAGS[key]:
            flags.append(key.lower())
    result.append('    .flags {0}'.format(', '.join(flags)))

    result.append('    .code')
    for inst in get_instructions(func):
        if inst.is_jump_target:
            result.append('    t{0}:'.format(inst.offset))
        if inst.opcode in hasjabs or inst.opcode in hasjrel:
            arg = 't{0}'.format(inst.argval)
            comment = ''
        elif inst.arg is not None:
            arg = inst.arg % 256
            comment = '; ({0})'.format(inst.argrepr)
        else:
            arg = ''
            comment = ''

        result.append(
            '      {0: <25} {1} {2}'.format(inst.opname, arg, comment)
        )
    return '\n'.join(result)
