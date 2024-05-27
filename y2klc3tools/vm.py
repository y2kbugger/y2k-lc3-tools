"""
virtual machine for LC-3 assembly language in python
"""

from __future__ import annotations

import array
from collections.abc import Callable
from enum import Enum
import select
import sys
import termios
import tty
from typing import Any
from . import UINT16_MAX, PC_START


def getchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ord(ch) == 3:
        # handle keyboard interrupt
        exit(130)
    return ch


class R:
    """Regisers"""

    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6
    R7 = 7
    PC = 8  # program counter
    COND = 9
    COUNT = 10


class register_dict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value % UINT16_MAX)


class OP(Enum):
    BR = 0  # branch
    ADD = 1  # add
    LD = 2  # load
    ST = 3  # store
    JSR = 4  # jump register
    AND = 5  # bitwise and
    LDR = 6  # load register
    STR = 7  # store register
    RTI = 8  # unused
    NOT = 9  # bitwise not
    LDI = 10  # load indirect
    STI = 11  # store indirect
    RET = 12  # jump
    JMP = 12  # jump
    RES = 13  # reserved (unused)
    LEA = 14  # load effective address
    TRAP = 15  # execute trap


class FL:
    """flags"""

    POS = 1 << 0  # P
    ZRO = 1 << 1  # Z
    NEG = 1 << 2  # N


### OPs implementaion
def bad_opcode(instr):
    raise Exception(f'Bad opcode: {instr}')


def add(instr):
    # destination register (DR)
    r0 = (instr >> 9) & 0x7
    # first operand (SR1)
    r1 = (instr >> 6) & 0x7
    # whether we are in immediate mode
    imm_flag = (instr >> 5) & 0x1

    if imm_flag:
        imm5 = sign_extend(instr & 0x1F, 5)
        reg[r0] = reg[r1] + imm5
    else:
        r2 = instr & 0x7
        reg[r0] = reg[r1] + reg[r2]

    update_flags(r0)


def ldi(instr, mem):
    """Load indirect"""
    # destination register (DR)
    r0 = (instr >> 9) & 0x7
    # PCoffset 9
    pc_offset = sign_extend(instr & 0x1FF, 9)
    # add pc_offset to the current PC, look at that memory location to get
    # the final address
    reg[r0] = mem[mem[reg[R.PC] + pc_offset]]
    update_flags(r0)


def and_(instr):
    r0 = (instr >> 9) & 0x7
    r1 = (instr >> 6) & 0x7
    r2 = instr & 0x7
    imm_flag = (instr >> 5) & 0x1

    if imm_flag:
        imm5 = sign_extend(instr & 0x1F, 5)
        reg[r0] = reg[r1] & imm5
    else:
        reg[r0] = reg[r1] & reg[r2]

    update_flags(r0)


def not_(instr):
    r0 = (instr >> 9) & 0x7
    r1 = (instr >> 6) & 0x7
    reg[r0] = ~reg[r1]
    update_flags(r0)


def br(instr):
    pc_offset = sign_extend((instr) & 0x1FF, 9)
    cond_flag = (instr >> 9) & 0x7
    if cond_flag & reg[R.COND]:
        reg[R.PC] += pc_offset


def jmp(instr):
    r1 = (instr >> 6) & 0x7
    reg[R.PC] = reg[r1]


def jsr(instr):
    r1 = (instr >> 6) & 0x7
    long_pc_offset = sign_extend(instr & 0x7FF, 11)
    long_flag = (instr >> 11) & 1
    reg[R.R7] = reg[R.PC]

    if long_flag:
        reg[R.PC] += long_pc_offset  # JSR
    else:
        reg[R.PC] = reg[r1]


def ld(instr, mem):
    r0 = (instr >> 9) & 0x7
    pc_offset = sign_extend(instr & 0x1FF, 9)
    reg[r0] = mem[reg[R.PC] + pc_offset]
    update_flags(r0)


def ldr(instr, mem):
    r0 = (instr >> 9) & 0x7
    r1 = (instr >> 6) & 0x7
    offset = sign_extend(instr & 0x3F, 6)
    reg[r0] = mem[reg[r1] + offset]
    update_flags(r0)


def lea(instr):
    r0 = (instr >> 9) & 0x7
    pc_offset = sign_extend(instr & 0x1FF, 9)
    reg[r0] = reg[R.PC] + pc_offset
    update_flags(r0)


def st(instr, mem):
    r0 = (instr >> 9) & 0x7
    pc_offset = sign_extend(instr & 0x1FF, 9)
    mem[reg[R.PC] + pc_offset, reg[r0]]


def sti(instr, mem):
    r0 = (instr >> 9) & 0x7
    pc_offset = sign_extend(instr & 0x1FF, 9)
    mem[mem[reg[R.PC] + pc_offset], reg[r0]]


def str_(instr, mem):
    r0 = (instr >> 9) & 0x7
    r1 = (instr >> 6) & 0x7
    offset = sign_extend(instr & 0x3F, 6)
    mem[reg[r1] + offset, reg[r0]]


### TRAPs implementation
def trap_putc(mem: Memory):
    i = reg[R.R0]
    c = mem[i]
    while c != 0:
        sys.stdout.write(chr(c))
        i += 1
        c = mem[i]
    sys.stdout.flush()


def trap_getc():
    reg[R.R0] = ord(getchar())


def trap_out():
    sys.stdout.write(chr(reg[R.R0]))
    sys.stdout.flush()


def trap_in():
    sys.stdout.write("Enter a character: ")
    sys.stdout.flush()
    reg[R.R0] = sys.stdout.read(1)


def trap_puts(mem: Memory):
    for i in range(reg[R.R0], len(mem)):
        c = mem[i]
        if c == 0:
            break
        sys.stdout.write(chr(c))
    sys.stdout.flush()


def trap_putsp(mem: Memory):
    for i in range(reg[R.R0], len(mem)):
        c = mem[i]
        if c == 0:
            break
        sys.stdout.write(chr(c & 0xFF))
        char = c >> 8
        if char:
            sys.stdout.write(chr(char))
    sys.stdout.flush()


def trap_halt(runstate: RunningState):
    print('-- HALT --', file=sys.stderr)
    runstate.halt()


class Trap(Enum):
    GETC = 0x20  # get character from keyboard
    OUT = 0x21  # output a character
    PUTS = 0x22  # output a word string
    IN = 0x23  # input a string
    PUTSP = 0x24  # output a byte string
    HALT = 0x25  # halt the program


def trap(instr, mem: Memory, runstate: RunningState):
    t = Trap(instr & 0xFF)

    if t == Trap.GETC:
        trap_getc()
    elif t == Trap.OUT:
        trap_out()
    elif t == Trap.PUTS:
        trap_puts(mem)
    elif t == Trap.IN:
        trap_in()
    elif t == Trap.PUTSP:
        trap_putsp(mem)
    elif t == Trap.HALT:
        trap_halt(runstate)


def check_key():
    _, o, _ = select.select([], [sys.stdin], [], 0)
    for s in o:
        if s == sys.stdin:
            return True
    return False


def sign_extend(x, bit_count):
    if (x >> (bit_count - 1)) & 1:
        x |= 0xFFFF << bit_count
    return x & 0xFFFF


def update_flags(r):
    if not reg.get(r):
        reg[R.COND] = FL.ZRO
    elif reg[r] >> 15:
        reg[R.COND] = FL.NEG
    else:
        reg[R.COND] = FL.POS


class Memory:
    def __init__(self):
        self._memory = array.array("H", (0 for _ in range(UINT16_MAX)))

    def load_binary(self, image_binary: bytes):
        """Load a flat binary file into memory.

        This function interprets the given binary data as an image file with a specific format and loads it into the global 'memory'. The binary format is expected as follows:

        - Origin (2 bytes): The first two bytes specify the 'origin', i.e., the starting address in memory where the image data will be loaded. It's interpreted as a big-endian unsigned integer.
        - Image Data (variable length): The rest of the binary data represents the image content.

        Parameters:
        image_binary: The binary data of the image to be loaded.

        Raises:
        Exception: If the image data exceeds the maximum allowable size for loading.
        Exception: If the image doesn't map to a whole number of 2 byte words.
        """

        # pad front
        origin = int.from_bytes(image_binary[:2], byteorder='big')
        self._memory = array.array("H", (0 for _ in range(origin)))

        # write image
        max_read = (UINT16_MAX - origin) * 2
        if len(image_binary[2:]) > max_read:
            raise Exception("Image file too big to load.")
        if len(image_binary[2:]) % 2 != 0:
            raise Exception("Image file doesn't map to a whole number of 2 byte words.")
        self._memory.frombytes(image_binary[2:])
        self._memory.byteswap()

        # pad back
        self._memory.frombytes(b'\x00\x00' * (UINT16_MAX - len(self._memory)))

    def __getitem__(self, address):
        KBSR = 0xFE00  # keyboard status
        KBDR = 0xFE02  # keyboard data

        address = address % UINT16_MAX
        if address == KBSR:
            if check_key():
                self._memory[KBSR] = 1 << 15
                self._memory[KBDR] = ord(getchar())
            else:
                self._memory[KBSR] = 0
        return self._memory[address]

    def __setitem__(self, address, val):
        address = address % UINT16_MAX
        self._memory[address] = val

    def __len__(self):
        return len(self._memory)


class RunningState:
    def __init__(self):
        self._is_running: bool = False

    def is_running(self):
        return self._is_running

    def halt(self):
        self._is_running = False

    def run(self):
        self._is_running = True


class VM:
    def __init__(self, tracing=False):
        self.tracing = tracing
        self.reg_trace = []
        self.memory: Memory = Memory()
        self.runstate: RunningState = RunningState()
        self.reg: dict = None

    ###########################
    # PASSTHROUGH STUBS
    # these will eventually encapsulate state that is currently in globals

    @property
    def R(self):
        class _reg:
            def __getattr__(self, __name: str) -> Any:
                global reg
                integer_key = R.__getattribute__(R, __name)
                return reg[integer_key]

            def __setattr__(self, __name: str, __value: Any) -> None:
                global reg
                integer_key = R.__getattribute__(R, __name)
                reg[integer_key] = __value

        return _reg()

    # END PASSTHROUGH STUBS
    ###########################

    def load_binary_from_file(self, file_path: str):
        """Read the contents of a binary file into memory."""
        with open(file_path, 'rb') as f:
            bytes_read = f.read()
        self.memory.load_binary(bytes_read)

    def load_binary_from_hex(self, image_binary_hex: str):
        """Load a flat binary file into memory.

        Parameters:
        image_binary_hex -- example: '0x3000DEAD'
        """
        image_binary = bytes.fromhex(image_binary_hex)
        self.memory.load_binary(image_binary)

    def reset(self):
        print('-- RESET --', file=sys.stderr)
        global reg
        reg = register_dict({i: 0 for i in range(R.COUNT)})
        reg[R.PC] = PC_START
        reg[R.COND] = FL.POS
        self.runstate.run()

    def step(self):
        if not self.runstate.is_running():
            print('-- HALTED --', file=sys.stderr)
            return

        if self.tracing:
            self.reg_trace.append(list(reg.values()))

        instr = self.memory[reg[R.PC]]
        reg[R.PC] += 1
        op = OP(instr >> 12)

        if op == OP.ADD:
            add(instr)
        elif op == OP.NOT:
            not_(instr)
        elif op == OP.AND:
            and_(instr)
        elif op == OP.BR:
            br(instr)
        elif op == OP.JMP:
            jmp(instr)
        elif op == OP.RET:
            jmp(instr)
        elif op == OP.JSR:
            jsr(instr)
        elif op == OP.LD:
            ld(instr, self.memory)
        elif op == OP.LDI:
            ldi(instr, self.memory)
        elif op == OP.LDR:
            ldr(instr, self.memory)
        elif op == OP.LEA:
            lea(instr)
        elif op == OP.ST:
            st(instr, self.memory)
        elif op == OP.STI:
            sti(instr, self.memory)
        elif op == OP.STR:
            str_(instr, self.memory)
        elif op == OP.TRAP:
            trap(instr, self.memory, self.runstate)
        else:
            bad_opcode(instr)

    def continue_(self):
        if not self.runstate.is_running():
            print('-- HALTED --', file=sys.stderr)
            return
        while self.runstate.is_running():
            self.step()
