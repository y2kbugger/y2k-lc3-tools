#!/usr/bin/env python3
import array
import sys

from . import UINT16_MAX

ops = {
    0: 'BR',
    1: 'ADD',
    2: 'LD',
    3: 'ST',
    4: 'JSRR',
    5: 'AND',
    6: 'LDR',
    7: 'STR',
    8: 'RTI',
    9: 'NOT',
    10: 'LDI',
    11: 'STI',
    12: 'JMP',
    13: 'RES',
    14: 'LEA',
    15: 'TRAP',
    32: 'GETC',
    33: 'OUT',
    34: 'PUTS',
    35: 'IN',
    36: 'PUTSP',
    37: 'HALT',
}


def parse_op(op):
    return ops.get(op >> 12)


def disassemble(image_binary: bytes) -> None:
    origin = int.from_bytes(image_binary[:2], byteorder='big')
    dump = array.array("H", [origin])

    max_read = (UINT16_MAX - origin) * 2
    if len(image_binary[2:]) > max_read:
        raise Exception("Image file too big to load.")
    if len(image_binary[2:]) % 2 != 0:
        raise Exception("Image file doesn't map to a whole number of 2 byte words.")
    dump.frombytes(image_binary[2:])
    dump.byteswap()
    for op in dump[1:]:
        print(f'{hex(origin)}: ({hex(op):>6}) {parse_op(op)} | {chr(op) if op < 256 else ""}')
        origin += 1


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <image file>")
        sys.exit(1)

    with open(sys.argv[1], 'rb') as f:
        image_binary = f.read()

    disassemble(image_binary)


if __name__ == '__main__':
    main()
