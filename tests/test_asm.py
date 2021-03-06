"""
Still figuring out what I'm doing here
"""
import cpython_assembly.asm as asm
import dis
import traceback


SAMPLE_CODE = """\

.stacksize  2   ;comment

.consts
   4

; line with comment
.code;comment
   LOAD_FAST 0
   LOAD_CONST 1
   BINARY_ADD
   RETURN_VALUE ;another comment

"""

def test_preprocess():

    result = asm.preprocess(SAMPLE_CODE)

    assert result['code'][0][1] == 'LOAD_FAST 0'
    assert result['code'][3][1] == 'RETURN_VALUE'
    assert len(result['code']) == 4
    assert result['consts'] == ['4']
    assert result['stacksize'] == ['2']

def test_assemble_code():
    machine = asm.Assembler()
    machine.src['code'] = [
        'LOAD_FAST 0',
        'LOAD_CONST 1',
        'binary_add',
        'RETURN_VALUE'
    ]
    # fake the line numbers
    machine.src['code'] = enumerate(machine.src['code'])

    machine.assemble_code()
    assert machine.code == b'|\x00d\x01\x17\x00S\x00'


def test_assemble_code_targets():
    machine = asm.Assembler()
    machine.src['code'] = [
        'foo: LOAD_FAST 0',
        'LOAD_CONST 1',
        'bar:',
        'binary_add',
        'baz: RETURN_VALUE'
    ]
    # fake the line numbers
    machine.src['code'] = enumerate(machine.src['code'])

    machine.assemble_code()
    assert machine.code == b'|\x00d\x01\x17\x00S\x00'
    assert machine.targets == {'foo': 0, 'bar': 4, 'baz': 6}


def test_assemble_code_target_positions():
    machine = asm.Assembler()
    machine.src['code'] = [
        '  SETUP_LOOP              after_loop',
        'start_loop:',
        '  LOAD_FAST               0',
        '  LOAD_CONST              1',
        '  COMPARE_OP               4', 
        '  POP_JUMP_IF_FALSE       end_loop',
        '  LOAD_FAST                0',
        '  LOAD_CONST               2',
        '  INPLACE_SUBTRACT',
        '  STORE_FAST               0',
        '  JUMP_ABSOLUTE            start_loop',
        'end_loop:  POP_BLOCK',
        'after_loop:',
        '  LOAD_FAST                0',
        '  RETURN_VALUE'
    ]
    # fake the line numbers
    machine.src['code'] = enumerate(machine.src['code'])

    machine.assemble_code()

    assert machine.code == b'x\x14|\x00d\x01k\x04r\x14|\x00d\x028\x00}\x00q\x02W\x00|\x00S\x00'


def test_assemble_consts():
    machine = asm.Assembler()
    machine.src['consts'] = [
        'four = 4',
        '23.2',
        'string =     "foo" + "bar"'
    ]

    machine.assemble_consts()

    assert machine.consts == (None, 4, 23.2, "foobar")
    assert machine.consts_alias == {'__doc__': 0, 'four': 1, 'string': 3}


def test_assemble_stacksize():
    machine = asm.Assembler()
    machine.src['stacksize'] = ['10']

    machine.assemble_stacksize()

    assert machine.stacksize == 10


def test_assemble_locals_and_params():
    machine = asm.Assembler()
    machine.src['params'] = ['a', 'b']
    machine.src['locals'] = [
        'c, d, e',
        'f, g',
        'h'
    ]

    machine.assemble_params()
    machine.assemble_locals()

    assert machine.varnames == ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h')
    assert machine.argcount == 2

def test_assemble_names():
    machine = asm.Assembler()
    machine.src['names'] = [
        'c, d, e',
        'f, g',
        'h'
    ]

    machine.assemble_names()

    assert machine.names == ('c', 'd', 'e', 'f', 'g', 'h')

def test_assemble_flags():
    machine = asm.Assembler()
    machine.src['flags'] = [
        'newlocals, OPTimized',
        '0x40'
    ]

    machine.assemble_flags()

    assert machine.flags == 67


def test_fibonacci():

    @asm.asm
    def fib(n):
        """
        Return the nth fibonacci number
        :::asm

        .stacksize 4
        .flags optimized, newlocals, nofree
        .locals a, b, idx
        .names range
        .consts
          int0 = 0
          int1 = 1

        .code
          LOAD_CONST               int0
          STORE_FAST               a

          LOAD_CONST               int1
          STORE_FAST               b

          SETUP_LOOP               after_loop
          LOAD_GLOBAL              range
          LOAD_FAST                n
          CALL_FUNCTION            1
          GET_ITER
        start_loop:
          FOR_ITER                 end_loop
          STORE_FAST               idx
          LOAD_FAST                b
          LOAD_FAST                a
          LOAD_FAST                b
          BINARY_ADD
          ROT_TWO
          STORE_FAST               a
          STORE_FAST               b
          JUMP_ABSOLUTE            start_loop
        end_loop:
          POP_BLOCK
        after_loop:
          LOAD_FAST                a
          RETURN_VALUE
        """

    assert fib(6) == 8
    assert fib(7) == 13
    assert fib.__doc__ == '\n        Return the nth fibonacci number\n        '
    assert fib.__code__.co_consts[0] == (
        '\n        Return the nth fibonacci number\n        '
    )


def test_fibonacci_no_flags():

    @asm.asm
    def fib(n):
        """
        Return the nth fibonacci number
        :::asm

        .stacksize 4
        .locals a, b, idx
        .names range
        .consts
          int0 = 0
          int1 = 1

        .code
          LOAD_CONST               int0
          STORE_FAST               a

          LOAD_CONST               int1
          STORE_FAST               b

          SETUP_LOOP               after_loop
          LOAD_GLOBAL              range
          LOAD_FAST                n
          CALL_FUNCTION            1
          GET_ITER
        start_loop:
          FOR_ITER                 end_loop
          STORE_FAST               idx
          LOAD_FAST                b
          LOAD_FAST                a
          LOAD_FAST                b
          BINARY_ADD
          ROT_TWO
          STORE_FAST               a
          STORE_FAST               b
          JUMP_ABSOLUTE            start_loop
        end_loop:
          POP_BLOCK
        after_loop:
          LOAD_FAST                a
          RETURN_VALUE
        """

    assert fib(6) == 8
    assert fib(7) == 13
    assert fib.__code__.co_flags == 83 # this gets the nested flag (16)


def test_fibonacci_kwonly():

    @asm.asm
    def fib(n, *, a, b):
        """
        Return the nth fibonacci number
        :::asm

        .stacksize 4
        .flags optimized, newlocals, nofree
        .locals idx
        .names range

        .code
          SETUP_LOOP               after_loop
          LOAD_GLOBAL              range
          LOAD_FAST                n
          CALL_FUNCTION            1
          GET_ITER
        start_loop:
          FOR_ITER                 end_loop
          STORE_FAST               idx
          LOAD_FAST                b
          LOAD_FAST                a
          LOAD_FAST                b
          BINARY_ADD
          ROT_TWO
          STORE_FAST               a
          STORE_FAST               b
          JUMP_ABSOLUTE            start_loop
        end_loop:
          POP_BLOCK
        after_loop:
          LOAD_FAST                a
          RETURN_VALUE
        """

    assert fib(6, a=0, b=1) == 8
    assert fib(7, a=0, b=1) == 13


def test_fibonacci_generator():

    @asm.asm
    def fibgen(n):
        """
        Generate the fibonacci numbers
        :::asm

        .stacksize 4
        .flags optimized, newlocals, nofree, generator
        .locals a, b, idx
        .names range
        .consts
          int0 = 0
          int1 = 1
          none = None

        .code
          LOAD_CONST               int0
          STORE_FAST               a
          LOAD_CONST               int1
          STORE_FAST               b
          SETUP_LOOP               after_loop
          LOAD_GLOBAL              range
          LOAD_FAST                n
          CALL_FUNCTION            1
          GET_ITER
        start_loop:
          FOR_ITER                 end_loop
          STORE_FAST               idx
          LOAD_FAST                b
          LOAD_FAST                a
          LOAD_FAST                b
          BINARY_ADD
          ROT_TWO
          STORE_FAST               a
          STORE_FAST               b
          LOAD_FAST                a
          YIELD_VALUE
          POP_TOP
          JUMP_ABSOLUTE            start_loop
        end_loop:
          POP_BLOCK
        after_loop:
          LOAD_CONST               none
          RETURN_VALUE
        """

    nums = [x for x in fibgen(7)]

    assert nums == [1, 1, 2, 3, 5, 8, 13]


def test_fibonacci_high_args():

    def fib(n):
        """
        Return the nth fibonacci number
        :::asm

        .stacksize 4
        .flags optimized, newlocals, nofree
        .locals a, b, idx
        .names range
        .consts
          int0 = 0
          int1 = 1

        .code
          LOAD_CONST               int0
          STORE_FAST               a

          LOAD_CONST               int1
          STORE_FAST               b

          SETUP_LOOP               after_loop
        """

    nops = ["NOP"]*500
    fib.__doc__ += '\n'.join(nops)
    fib.__doc__ += """
          LOAD_GLOBAL              range
          LOAD_FAST                n
          CALL_FUNCTION            1
          GET_ITER
        start_loop:
          FOR_ITER                 end_loop
          STORE_FAST               idx
          LOAD_FAST                b
          LOAD_FAST                a
          LOAD_FAST                b
          BINARY_ADD
          ROT_TWO
          STORE_FAST               a
          STORE_FAST               b
          JUMP_ABSOLUTE            start_loop
        end_loop:
          POP_BLOCK
        after_loop:
          LOAD_FAST                a
          RETURN_VALUE
        """
    fib = asm.asm(fib)

    assert fib(6) == 8
    assert fib(7) == 13

def test_fibonacci_very_high_args():

    def fib(n):
        """
        Return the nth fibonacci number
        :::asm

        .stacksize 4
        .flags optimized, newlocals, nofree
        .locals a, b, idx
        .names range
        .consts
          int0 = 0
          int1 = 1

        .code
          LOAD_CONST               int0
          STORE_FAST               a

          LOAD_CONST               int1
          STORE_FAST               b

          SETUP_LOOP               after_loop
        """

    nops = ["NOP"]*68000
    fib.__doc__ += '\n'.join(nops)
    fib.__doc__ += """
          LOAD_GLOBAL              range
          LOAD_FAST                n
          CALL_FUNCTION            1
          GET_ITER
        start_loop:
          FOR_ITER                 end_loop
          STORE_FAST               idx
          LOAD_FAST                b
          LOAD_FAST                a
          LOAD_FAST                b
          BINARY_ADD
          ROT_TWO
          STORE_FAST               a
          STORE_FAST               b
          JUMP_ABSOLUTE            start_loop
        end_loop:
          POP_BLOCK
        after_loop:
          LOAD_FAST                a
          RETURN_VALUE
        """
    fib = asm.asm(fib)

    assert fib(6) == 8
    assert fib(7) == 13


def test_lnotab_longbad():
    """
    Make sure the test module raising an exception
    produces a valid traceback from lnotab
    """
    from tests.assets.longbad import bad

    try:
        bad(0)
    except ValueError as e:
        ex = e

    tb = traceback.extract_tb(ex.__traceback__)[-1]

    assert tb[0] == 'bad'
    assert tb[1] == 350
    assert tb[2].endswith('longbad.py')
    assert tb[3] == 'RAISE_VARARGS            1'


def test_closure_metafib():
    from tests.assets.metafib import metafib

    fib = metafib(0, 1)


    assert fib(6) == 8
    assert fib(7) == 13
