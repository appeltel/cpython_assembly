from cpython_assembly.asm import asm

@asm
def fib_inner(n):
    """
    Closure test function
    :::asm
    .stacksize 4
    .freevars a, b
    .locals x, y, idx
    .flags optimized, newlocals, nested
    .names range
    .code
      LOAD_DEREF               a
      STORE_FAST               x

      LOAD_DEREF               b
      STORE_FAST               y

      SETUP_LOOP               after_loop
      LOAD_GLOBAL              range
      LOAD_FAST                n
      CALL_FUNCTION            1
      GET_ITER
    start_loop:
      FOR_ITER                 end_loop
      STORE_FAST               idx

      LOAD_FAST                y
      LOAD_FAST                x
      LOAD_FAST                y
      BINARY_ADD
      ROT_TWO
      STORE_FAST               x
      STORE_FAST               y
      JUMP_ABSOLUTE           start_loop
    end_loop:
      POP_BLOCK
    after_loop:
      LOAD_FAST                x
      RETURN_VALUE
    """

@asm(fib_inner)
def metafib(a, b):
    """
    Closure producing function
    :::asm
    .stacksize 3
    .cellvars a, b
    .locals fib
    .flags optimized, newlocals
    .consts
      fcode = args[0]
      fname = 'metafib.<locals>.fib'
    .code
      LOAD_CLOSURE             a
      LOAD_CLOSURE             b
      BUILD_TUPLE              2
      LOAD_CONST               fcode
      LOAD_CONST               fname
      MAKE_FUNCTION            8
      STORE_FAST               fib
      LOAD_FAST                fib
      RETURN_VALUE
    """
