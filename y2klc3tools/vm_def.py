from enum import Enum

type UINT16 = int  # TODO: maybe make this a separate type wrapped in function that guarantees 16-bit int


class R(Enum):
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6
    R7 = 7
    PC = 8
    COND = 9


class OP(Enum):
    BR = 0x0  # branch
    ADD = 0x1  # add
    LD = 0x2  # load
    ST = 0x3  # store
    JSR = 0x4  # jump register
    AND = 0x5  # bitwise and
    LDR = 0x6  # load register
    STR = 0x7  # store register
    RTI = 0x8  # unused
    NOT = 0x9  # bitwise not
    LDI = 0xA  # load indirect
    STI = 0xB  # store indirect
    RET = 0xC  # jump
    JMP = 0xC  # jump
    RES = 0xD  # reserved (unused)
    LEA = 0xE  # load effective address
    TRAP = 0xF  # execute trap


class Trap(Enum):
    GETC = 0x20  # get character from keyboard
    OUT = 0x21  # output a character
    PUTS = 0x22  # output a word string
    IN = 0x23  # input a string
    PUTSP = 0x24  # output a byte string
    HALT = 0x25  # halt the program


class FL(Enum):
    """Flags"""

    POS = 1 << 0  # P
    ZRO = 1 << 1  # Z
    NEG = 1 << 2  # N
