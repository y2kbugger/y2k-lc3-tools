import array
import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Iterable
from enum import Enum
from pathlib import Path

from . import PC_START, UINT16_MAX

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


class Memory(ABC):
    def load_words_at_address(self, words: array.array[UINT16], address: UINT16) -> None:
        assert len(words) + address <= UINT16_MAX
        assert address >= 0
        assert words.itemsize == 2  # 2 bytes per word

        for i, v in enumerate(words, address):
            self[i] = v

    def load_binary(self, image_binary: bytes) -> None:
        """Load a flat LC3 binary file into memory.

        This function interprets the given binary data as an image file with a
        specific format and loads it into the global 'memory'. The binary format
        is expected as follows:

        - Origin (2 bytes): The first two bytes specify the 'origin', i.e., the
        starting address in memory where the image data will be loaded. It's
        interpreted as a big-endian unsigned integer.
        - Image Data (variable length): The rest of the binary data represents the image content.

        Parameters:
        image_binary: The binary data of the image to be loaded.

        Raises:
        Exception: If the image data exceeds the maximum allowable size for loading.
        Exception: If the image doesn't map to a whole number of 2 byte words.
        """
        origin = int.from_bytes(image_binary[:2], byteorder='big')
        # write image
        max_read = (UINT16_MAX - origin) * 2
        if len(image_binary[2:]) > max_read:
            raise Exception("Image file too big to load.")
        if len(image_binary[2:]) % 2 != 0:
            raise Exception("Image file doesn't map to a whole number of 2 byte words.")
        memory = array.array("H", image_binary[2:])
        memory.byteswap()

        self.load_words_at_address(memory, origin)

    def load_binary_from_file(self, file_path: str) -> None:
        """Read the contents of a binary file into memory."""
        with Path(file_path).open('rb') as f:
            bytes_read = f.read()
        self.load_binary(bytes_read)

    def load_binary_from_hex(self, image_binary_hex: str) -> None:
        """Load a flat binary hex file into memory.

        Parameters:
        image_binary_hex -- example: '0x3000DEAD'
        """
        image_binary = bytes.fromhex(image_binary_hex)
        self.load_binary(image_binary)

    def load_binary_from_bytes(self, image_binary_bytes: bytes) -> None:
        """Load bytes directly into memory."""
        self.load_binary(image_binary_bytes)

    def __len__(self) -> UINT16:
        return UINT16_MAX

    @abstractmethod
    def __getitem__(self, address: UINT16) -> UINT16: ...

    @abstractmethod
    def __setitem__(self, address: UINT16, val: UINT16): ...


class Registers(ABC):
    def __init__(self):
        self.reset()
        self.trace_enabled = False
        self.traces = []

    def values(self) -> Iterable[UINT16]:
        yield from [self[r] for r in R]

    def save_trace(self) -> None:
        self.traces.append(list(self.values()))

    def reset(self) -> None:
        for r in R:
            self[r] = 0
        self[R.PC] = PC_START
        self[R.COND] = FL.POS.value

    @abstractmethod
    def __getitem__(self, key: R) -> UINT16: ...

    @abstractmethod
    def __setitem__(self, key: R, val: UINT16): ...


class RunningState(ABC):
    def __init__(self):
        self.is_running = False

    def halt(self) -> None:
        self.is_running = False

    def run(self) -> None:
        self.is_running = True

    @property
    @abstractmethod
    def is_running(self) -> bool: ...

    @is_running.setter
    @abstractmethod
    def is_running(self, value: bool): ...


class Output(ABC):
    @abstractmethod
    def _write(self, text: str, channel: str): ...

    @abstractmethod
    def _read(self, channel: str) -> str: ...

    def write(self, text: str) -> None:
        self._write(text, 'output')

    def read(self) -> str:
        return self._read('output')


@dataclasses.dataclass
class VM(ABC):
    reg: Registers
    mem: Memory
    runstate: RunningState
    out: Output

    def reset(self) -> None:
        print('-- RESET --\n')
        self.reg.reset()
        self.runstate.run()

    def continue_(self) -> None:
        self.step()
        while True:
            try:
                self.step()
            except Exception:
                break

    def step(self) -> None:
        if not self.runstate.is_running:
            raise Exception("-- HALTED --\n")

        if self.reg.trace_enabled:
            self.reg.save_trace()

        self._step()

    @abstractmethod
    def _step(self): ...
