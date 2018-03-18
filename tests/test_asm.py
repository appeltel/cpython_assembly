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
   LOAD_FAST (x)
   LOAD_CONST (4)
   BINARY_ADD
   RETURN_VALUE ;another comment

"""

def test_preprocess():

    result = asm.preprocess(SAMPLE_CODE)

    assert result['code'][0] == 'LOAD_FAST (x)'
    assert result['code'][3] == 'RETURN_VALUE'
    assert len(result['code']) == 4
    assert result['varnames'] == ['x']
