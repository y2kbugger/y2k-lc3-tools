# Setup
## Python Dependencies

    poetry install

# Development
## Running Tests
    poetry run pytest

## Notebooks
The notebooks are in the `notebooks` directory.

Use the venv created by poetry to run the notebooks, one easy way is from within vscode.

# Todo
1. Simplify the vm code and make it more pythonic
    - make definitions of opcodes and registers more pythonic
1. Get the assembler working in my repo and running under pytest
    - tests for symbol table also (asm.dump_symbol_table convert to returning str)
1. Improve disasm
    - pytests
    - Get .FILL correct
    - Be able to use symbol table to get labels
    - stretch, match the CSU disassembler
1. combine info from all three readme's into one. including history of the projects, e.g. CSU extension with push/pop
1. Document that the original assmember was written in C and had poor cli interface and gui was in tcl and also odd.
1. Document that the original has an acutual operating system written in LC-3 assembly, but our vm stubs out the traps with python
1. Make a nice api for debugging out vm register traces
1. Add unit tests for vm register traces
1. Get C compiler running in notebook
1. Move C compiler tests to use pytest
1. Make C compiler tests use the pure python assembler and vm
1. Remove the dependencies that I installed for the c compiler (bats and moreutils)
1. Convert compiler to use origial multi instruction push and pop
1. Recreate a holistic CLI interface for the assembler, vm, and C compiler

# Previous work
I have modernized the tooling and combined multiple projects for the LC-3 into one repo. The original projects are listed below, and I have included the commit hash of the last commit I pulled from each repo, incase I want to merge in later upstream changes.
## The C compiler for the LC-3
https://github.com/nickodell/lc3-cc
8d41f34 Update documentation
Nickodell's version was, in turn, inspired by [this tutorial](https://github.com/justinmeiners/lc3-vm).
## The LC-3 assembler
https://github.com/paul-nameless/lc3-asm.git
38ac008 Rewrite bunch of IFs in dict condision (why? I see so) Fix disasm
## The LC-3 simulator
https://github.com/paul-nameless/lc3-vm.git
88bdc83
## Other Previous work
original lc3 simulator tools and assembler
CSU extension with push/pop

# Original README.md from the assembler
## Debug

To debug, you can use simple disassembler written by me:

```
python3 disasm.py [obj-file]
```

I found it very usefull trying to understand what went wrong (invalid address in symbol table, invalid LC count, invalid opcode encoding, etc.).

There is a lot of debug information printing out when assembling but it can be ignored or deleted.

## Learning LC-3

You can find usefull information and Instruction Set Architecture (ISA) [here](https://github.com/justinmeiners/lc3-vm) and [here](https://github.com/paul-nameless/lc3-vm)

Also you may find usefull desctiptions in `assembler.h` file to better understand how to implement it [here](https://github.com/davedennis/LC3-Assembler)


## Download

You can download simulator [here](http://highered.mheducation.com/sites/0072467509/student_view0/lc-3_simulator.html)

Or use my own implementation written in pure [python](https://github.com/paul-nameless/lc3-vm)

You can find 2048 game written in lc3 [here](https://github.com/rpendleton/lc3-2048)
