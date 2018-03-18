"""
Still figuring out what I'm doing here
"""
import cpython_assembly.asm as asm

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

    assert result['code'][0] == 'LOAD_FAST 0'
    assert result['code'][3] == 'RETURN_VALUE'
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
    assert machine.consts_alias == {'none': 0, 'four': 1, 'string': 3}

def test_assemble_stacksize():
    machine = asm.Assembler()
    machine.src['stacksize'] = ['10']

    machine.assemble_stacksize()

    assert machine.stacksize == 10
