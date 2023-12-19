# Setup
## Python Dependencies

    poetry install

## Notebooks
The notebooks are in the `notebooks` directory.

Use the venv created by poetry to run the notebooks, one easy way is from within vscode.

# Todo
1. Get the simulator working from a notebook e.g. strip out cli tools
1. Get the assembler working from a notebook e.g. strip out cli tools
1. Get the simulator working in my repo and running under pytest
1. Simplify the vm code and make it more pythonic
    - move all state int VM class
    - make definitions of opcodes and registers more pythonic
    - rewrite loader to make it simpler
1. Get the assembler working in my repo and running under pytest
1. combine info from all three readme's into one. including history of the projects, e.g. CSU extension with push/pop
1. Document that the original assmember was written in C and had poor cli interface and gui was in tcl and also odd.
1. Document that the original has an acutual operating system written in LC-3 assembly, but our vm stubs out the traps with python
1. Make a nice api for debugging out vm register traces
1. Add unit tests for vm register traces
1. Implement push and pop in the assembler and python vm
1. Move C compiler tests to use pytest
1. Make C compiler tests use the pure python assembler and vm
1. Remove the dependencies that I installed for the c compiler (bats and moreutils)
1. Recreate a holistic CLI interface for the assembler, vm, and C compiler

# Tests
1. image file too big for VM

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