"""
Still figuring out what I'm doing here
"""
import cpython_assembly.asm as asm

SAMPLE_CODE = """\

.stacksize  ; maybe reformat this
   2

.consts
   4

.varnames
   x
; line with comment
.code
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
    assert result['varnames'] == ['x']


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

