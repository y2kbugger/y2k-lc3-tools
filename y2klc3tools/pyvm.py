from __future__ import annotations

import array
import select
import sys
import termios
import tty
from collections import defaultdict
from typing import NoReturn

from . import UINT16_MAX
from .vm import FL, OP, UINT16, VM, Memory, Output, R, Registers, RunningState, Trap


# OPs implementaion
def bad_opcode(instr: UINT16) -> NoReturn:
    raise Exception(f'Bad opcode: {instr}')


def add(instr: UINT16, reg: Registers) -> None:
    # destination register (DR)
    r0 = R((instr >> 9) & 0x7)
    # first operand (SR1)
    r1 = R((instr >> 6) & 0x7)
    # whether we are in immediate mode
    imm_flag = (instr >> 5) & 0x1

    if imm_flag:
        imm5 = sign_extend(instr & 0x1F, 5)
        reg[r0] = reg[r1] + imm5
    else:
        r2 = R(instr & 0x7)
        reg[r0] = reg[r1] + reg[r2]

    update_flags(r0, reg)


def ldi(instr: UINT16, reg: Registers, mem: Memory) -> None:
    """Load indirect"""
    # destination register (DR)
    r0 = R((instr >> 9) & 0x7)
    # PCoffset 9
    pc_offset = sign_extend(instr & 0x1FF, 9)
    # add pc_offset to the current PC, look at that memory location to get
    # the final address
    reg[r0] = mem[mem[reg[R.PC] + pc_offset]]
    update_flags(r0, reg)


def and_(instr: UINT16, reg: Registers) -> None:
    r0 = R((instr >> 9) & 0x7)
    r1 = R((instr >> 6) & 0x7)
    r2 = R(instr & 0x7)
    imm_flag = (instr >> 5) & 0x1

    if imm_flag:
        imm5 = sign_extend(instr & 0x1F, 5)
        reg[r0] = reg[r1] & imm5
    else:
        reg[r0] = reg[r1] & reg[r2]

    update_flags(r0, reg)


def not_(instr: UINT16, reg: Registers) -> None:
    r0 = R((instr >> 9) & 0x7)
    r1 = R((instr >> 6) & 0x7)
    reg[r0] = ~reg[r1]
    update_flags(r0, reg)


def br(instr: UINT16, reg: Registers) -> None:
    pc_offset = sign_extend((instr) & 0x1FF, 9)
    cond_flag = (instr >> 9) & 0x7
    if cond_flag & reg[R.COND]:
        reg[R.PC] += pc_offset


def jmp(instr: UINT16, reg: Registers) -> None:
    r1 = R((instr >> 6) & 0x7)
    reg[R.PC] = reg[r1]


def jsr(instr: UINT16, reg: Registers) -> None:
    r1 = R((instr >> 6) & 0x7)
    long_pc_offset = sign_extend(instr & 0x7FF, 11)
    long_flag = (instr >> 11) & 1
    reg[R.R7] = reg[R.PC]

    if long_flag:
        reg[R.PC] += long_pc_offset  # JSR
    else:
        reg[R.PC] = reg[r1]


def ld(instr: UINT16, reg: Registers, mem: Memory) -> None:
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    reg[r0] = mem[reg[R.PC] + pc_offset]
    update_flags(r0, reg)


def ldr(instr: UINT16, reg: Registers, mem: Memory) -> None:
    r0 = R((instr >> 9) & 0x7)
    r1 = R((instr >> 6) & 0x7)
    offset = sign_extend(instr & 0x3F, 6)
    reg[r0] = mem[reg[r1] + offset]
    update_flags(r0, reg)


def lea(instr: UINT16, reg: Registers) -> None:
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    reg[r0] = reg[R.PC] + pc_offset
    update_flags(r0, reg)


def st(instr: UINT16, reg: Registers, mem: Memory) -> None:
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    mem[reg[R.PC] + pc_offset] = reg[r0]


def sti(instr: UINT16, reg: Registers, mem: Memory) -> None:
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    mem[mem[reg[R.PC] + pc_offset]] = reg[r0]


def str_(instr: UINT16, reg: Registers, mem: Memory) -> None:
    r0 = R((instr >> 9) & 0x7)
    r1 = R((instr >> 6) & 0x7)
    offset = sign_extend(instr & 0x3F, 6)
    mem[reg[r1] + offset] = reg[r0]


# TRAPs implementation


def check_key() -> bool:
    _, o, _ = select.select([], [sys.stdin], [], 0)
    return any(s == sys.stdin for s in o)


def getchar() -> str:
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


def trap_getc(reg: Registers) -> None:
    reg[R.R0] = ord(getchar())


def trap_out(reg: Registers, out: Output) -> None:
    out.write(chr(reg[R.R0] & 0xFF))


def trap_puts(reg: Registers, mem: Memory, out: Output) -> None:
    for i in range(reg[R.R0], len(mem)):
        c = mem[i]
        if c == 0:
            break
        out.write(chr(c))


def trap_in(reg: Registers, out: Output) -> None:
    out.write("Enter a character: ")
    c = getchar()
    out.write(c)
    reg[R.R0] = ord(c)


def trap_putsp(reg: Registers, mem: Memory) -> None:
    for i in range(reg[R.R0], len(mem)):
        c = mem[i]
        if c == 0:
            break
        sys.stdout.write(chr(c & 0xFF))
        char = c >> 8
        if char:
            sys.stdout.write(chr(char))
    sys.stdout.flush()


def trap_halt(runstate: RunningState, out: Output) -> None:
    print('-- HALT --\n')
    runstate.halt()


def trap(
    instr: UINT16,
    reg: Registers,
    mem: Memory,
    runstate: RunningState,
    out: Output,
) -> None:
    t = Trap(instr & 0xFF)

    if t == Trap.GETC:
        trap_getc(reg)
    elif t == Trap.OUT:
        trap_out(reg, out)
    elif t == Trap.PUTS:
        trap_puts(reg, mem, out)
    elif t == Trap.IN:
        trap_in(reg, out)
    elif t == Trap.PUTSP:
        trap_putsp(reg, mem)
    elif t == Trap.HALT:
        trap_halt(runstate, out)


def sign_extend(x: UINT16, bit_count: int) -> UINT16:
    if (x >> (bit_count - 1)) & 1:
        x |= 0xFFFF << bit_count
    return x & 0xFFFF


def update_flags(r: R, reg: Registers) -> None:
    if not reg[r]:
        reg[R.COND] = FL.ZRO.value
    elif reg[r] >> 15:
        reg[R.COND] = FL.NEG.value
    else:
        reg[R.COND] = FL.POS.value


class PyMemory(Memory):
    def __init__(self):
        self._memory = array.array("H", (0 for _ in range(UINT16_MAX)))

    def __getitem__(self, address: int):
        return self._memory[address % UINT16_MAX]

    def __setitem__(self, address: int, val: int):
        self._memory[address % UINT16_MAX] = val


class PyRegisters(Registers):
    def __init__(self):
        self._registers = dict.fromkeys(R, 0)
        super().__init__()

    def __setitem__(self, key: R, value: int):
        self._registers[key] = value % UINT16_MAX

    def __getitem__(self, key: R) -> int:
        return self._registers[key]


class PyRunningState(RunningState):
    def __init__(self):
        self._is_running = True
        super().__init__()

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool):
        self._is_running = value


class PyOutput(Output):
    def __init__(self):
        self._out = defaultdict(str)

    def _write(self, text: str, channel: str):
        self._out[channel] += text

    def _read(self, channel: str) -> str:
        msg = self._out[channel]
        self._out[channel] = ""
        return msg


class PyVM(VM):
    def __init__(self):
        self.mem = PyMemory()
        self.runstate = PyRunningState()
        self.reg = PyRegisters()
        self.out = PyOutput()

    def _step(self):
        instr: UINT16 = self.mem[self.reg[R.PC]]
        self.reg[R.PC] += 1
        op = OP(instr >> 12)

        if op == OP.ADD:
            add(instr, self.reg)
        elif op == OP.NOT:
            not_(instr, self.reg)
        elif op == OP.AND:
            and_(instr, self.reg)
        elif op == OP.BR:
            br(instr, self.reg)
        elif op == OP.JMP or op == OP.RET:
            jmp(instr, self.reg)
        elif op == OP.JSR:
            jsr(instr, self.reg)
        elif op == OP.LD:
            ld(instr, self.reg, self.mem)
        elif op == OP.LDI:
            ldi(instr, self.reg, self.mem)
        elif op == OP.LDR:
            ldr(instr, self.reg, self.mem)
        elif op == OP.LEA:
            lea(instr, self.reg)
        elif op == OP.ST:
            st(instr, self.reg, self.mem)
        elif op == OP.STI:
            sti(instr, self.reg, self.mem)
        elif op == OP.STR:
            str_(instr, self.reg, self.mem)
        elif op == OP.TRAP:
            trap(instr, self.reg, self.mem, self.runstate, self.out)
        else:
            bad_opcode(instr)
