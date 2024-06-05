from __future__ import annotations

import array
import select
import sys
import termios
import tty

from . import UINT16_MAX, PC_START
from .vm_def import R, OP, FL, Trap


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


class Registers(dict):
    def __init__(self):
        for r in R:
            self[r] = 0
        super().__init__()

    def __setitem__(self, key: R, value: int):
        super().__setitem__(key, value % UINT16_MAX)


### OPs implementaion
def bad_opcode(instr):
    raise Exception(f'Bad opcode: {instr}')


def add(instr, reg: Registers):
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


def ldi(instr, mem, reg: Registers):
    """Load indirect"""
    # destination register (DR)
    r0 = R((instr >> 9) & 0x7)
    # PCoffset 9
    pc_offset = sign_extend(instr & 0x1FF, 9)
    # add pc_offset to the current PC, look at that memory location to get
    # the final address
    reg[r0] = mem[mem[reg[R.PC] + pc_offset]]
    update_flags(r0, reg)


def and_(instr, reg: Registers):
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


def not_(instr, reg: Registers):
    r0 = R((instr >> 9) & 0x7)
    r1 = R((instr >> 6) & 0x7)
    reg[r0] = ~reg[r1]
    update_flags(r0, reg)


def br(instr, reg: Registers):
    pc_offset = sign_extend((instr) & 0x1FF, 9)
    cond_flag = (instr >> 9) & 0x7
    if cond_flag & reg[R.COND]:
        reg[R.PC] += pc_offset


def jmp(instr, reg: Registers):
    r1 = R((instr >> 6) & 0x7)
    reg[R.PC] = reg[r1]


def jsr(instr, reg: Registers):
    r1 = R((instr >> 6) & 0x7)
    long_pc_offset = sign_extend(instr & 0x7FF, 11)
    long_flag = (instr >> 11) & 1
    reg[R.R7] = reg[R.PC]

    if long_flag:
        reg[R.PC] += long_pc_offset  # JSR
    else:
        reg[R.PC] = reg[r1]


def ld(instr, mem: Memory, reg: Registers):
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    reg[r0] = mem[reg[R.PC] + pc_offset]
    update_flags(r0, reg)


def ldr(instr, mem: Memory, reg: Registers):
    r0 = R((instr >> 9) & 0x7)
    r1 = R((instr >> 6) & 0x7)
    offset = sign_extend(instr & 0x3F, 6)
    reg[r0] = mem[reg[r1] + offset]
    update_flags(r0, reg)


def lea(instr, reg: Registers):
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    reg[r0] = reg[R.PC] + pc_offset
    update_flags(r0, reg)


def st(instr, mem: Memory, reg: Registers):
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    mem[reg[R.PC] + pc_offset, reg[r0]]


def sti(instr, mem: Memory, reg: Registers):
    r0 = R((instr >> 9) & 0x7)
    pc_offset = sign_extend(instr & 0x1FF, 9)
    mem[mem[reg[R.PC] + pc_offset], reg[r0]]


def str_(instr, mem: Memory, reg: Registers):
    r0 = R((instr >> 9) & 0x7)
    r1 = R((instr >> 6) & 0x7)
    offset = sign_extend(instr & 0x3F, 6)
    mem[reg[r1] + offset, reg[r0]]


### TRAPs implementation
def trap_getc(reg: Registers):
    reg[R.R0] = ord(getchar())


def trap_out(reg: Registers, out: Output):
    out.write(chr(reg[R.R0] & 0xFF))


def trap_puts(mem: Memory, reg: Registers, out: Output):
    for i in range(reg[R.R0], len(mem)):
        c = mem[i]
        if c == 0:
            break
        out.write(chr(c))


def trap_in(reg: Registers, out: Output):
    out.write("Enter a character: ")
    c = getchar()
    out.write(c)
    reg[R.R0] = ord(c)


def trap_putsp(mem: Memory, reg: Registers):
    for i in range(reg[R.R0], len(mem)):
        c = mem[i]
        if c == 0:
            break
        sys.stdout.write(chr(c & 0xFF))
        char = c >> 8
        if char:
            sys.stdout.write(chr(char))
    sys.stdout.flush()


def trap_halt(runstate: RunningState, out: Output):
    out.write_err('-- HALT --\n')
    runstate.halt()


def trap(instr, mem: Memory, runstate: RunningState, reg: Registers, out: Output):
    t = Trap(instr & 0xFF)

    if t == Trap.GETC:
        trap_getc(reg)
    elif t == Trap.OUT:
        trap_out(reg, out)
    elif t == Trap.PUTS:
        trap_puts(mem, reg, out)
    elif t == Trap.IN:
        trap_in(reg, out)
    elif t == Trap.PUTSP:
        trap_putsp(mem, reg)
    elif t == Trap.HALT:
        trap_halt(runstate, out)


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


def update_flags(r, reg: Registers):
    if not reg.get(r):
        reg[R.COND] = FL.ZRO.value
    elif reg[r] >> 15:
        reg[R.COND] = FL.NEG.value
    else:
        reg[R.COND] = FL.POS.value


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


class Output:
    def __init__(self):
        self._out = ''
        self._err = ''

    def write(self, text: str):
        self._out += text

    def write_err(self, text: str):
        self._err += text

    def read(self):
        o = self._out
        self._out = ''
        return o

    def read_err(self):
        e = self._err
        self._err = ''
        return e


class VM:
    def __init__(self, trace_registers=False):
        self.trace_registers = trace_registers
        self.reg_trace = []
        self.memory: Memory = Memory()
        self.runstate: RunningState = RunningState()
        self.reg: Registers = Registers()
        self.out: Output = Output()

    @property
    def is_running(self) -> bool:
        return self.runstate.is_running()

    def load_binary_from_file(self, file_path: str):
        """Read the contents of a binary file into memory."""
        with open(file_path, 'rb') as f:
            bytes_read = f.read()
        self.memory.load_binary(bytes_read)

    def load_binary_from_hex(self, image_binary_hex: str):
        """Load a flat binary hex file into memory.

        Parameters:
        image_binary_hex -- example: '0x3000DEAD'
        """
        image_binary = bytes.fromhex(image_binary_hex)
        self.memory.load_binary(image_binary)

    def load_binary_from_bytes(self, image_binary_bytes: bytes):
        """Load bytes directly into memory."""
        self.memory.load_binary(image_binary_bytes)

    def reset(self):
        self.out.write_err('-- RESET --\n')
        self.reg = Registers()
        self.reg[R.PC] = PC_START
        self.reg[R.COND] = FL.POS.value
        self.runstate.run()

    def step(self):
        if not self.runstate.is_running():
            self.out.write_err('-- HALTED --\n')
            return

        if self.trace_registers:
            self.reg_trace.append(list(self.reg.values()))

        instr = self.memory[self.reg[R.PC]]
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
        elif op == OP.JMP:
            jmp(instr, self.reg)
        elif op == OP.RET:
            jmp(instr, self.reg)
        elif op == OP.JSR:
            jsr(instr, self.reg)
        elif op == OP.LD:
            ld(instr, self.memory, self.reg)
        elif op == OP.LDI:
            ldi(instr, self.memory, self.reg)
        elif op == OP.LDR:
            ldr(instr, self.memory, self.reg)
        elif op == OP.LEA:
            lea(instr, self.reg)
        elif op == OP.ST:
            st(instr, self.memory, self.reg)
        elif op == OP.STI:
            sti(instr, self.memory, self.reg)
        elif op == OP.STR:
            str_(instr, self.memory, self.reg)
        elif op == OP.TRAP:
            trap(instr, self.memory, self.runstate, self.reg, self.out)
        else:
            bad_opcode(instr)

    def continue_(self):
        if not self.runstate.is_running():
            self.out.write_err('-- HALTED --\n')
            return
        while self.runstate.is_running():
            self.step()
