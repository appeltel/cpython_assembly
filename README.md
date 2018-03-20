![Travis CI Status](https://travis-ci.org/appeltel/cpython_assembly.svg?branch=master)
![python 3.6, 3.7](https://img.shields.io/badge/python-3.6%2C%203.7-brightgreen.svg)

# CPython Assembler

Assembler for CPython bytecode into python functions

This is for educational/demonstration use only. This code is expected
to break things in odd and inexplicable ways, and is very slow.

Let's do this!!!

## Current Status

The assembler only works on CPython 3.6 currently. Previous versions of
python have a fundamentally different bytecode and for the purposes of
assembly constitute a different architecture. I'm pretty sure that each
minor revision should be considered a new architecture, so maintaining this
ought to be interesting.

The current status is an "open learning" project where I wanted to learn
more about the CPython virtual machine and bytecode, so I slapped some code
together to make a rudimentary assembler without much planning or
foresight.

There are a number of things that the assembler does _wrong_, and it is
only expected to work for functions that don't do anything "fancy".

## Assembly language specification

We'll get to that later, here's an example function

    from cpython_assembly.asm import asm


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

## Authorship, License, Warranty

This code was initially written by Eric Appelt and is licensed under the
MIT license. It comes with no warranty and is expected to break anything it
touches, leak memory, and segmentation fault without warning.
