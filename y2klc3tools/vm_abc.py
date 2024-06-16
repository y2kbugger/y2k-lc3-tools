import array
import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Iterable

from . import PC_START, UINT16_MAX
from .vm_def import FL, R


class Memory(ABC):
    def load_words_at_address(self, words: array.array[int], address: int) -> None:
        assert len(words) + address <= UINT16_MAX
        assert address >= 0
        assert words.itemsize == 2  # 2 bytes per word

        for i, v in enumerate(words, address):
            self[i] = v

    def load_binary(self, image_binary: bytes) -> None:
        """Load a flat LC3 binary file into memory.

        This function interprets the given binary data as an image file with a specific format and loads it into the global 'memory'. The binary format is expected as follows:

        - Origin (2 bytes): The first two bytes specify the 'origin', i.e., the starting address in memory where the image data will be loaded. It's interpreted as a big-endian unsigned integer.
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
        with open(file_path, 'rb') as f:
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

    def __len__(self) -> int:
        return UINT16_MAX

    @abstractmethod
    def __getitem__(self, address: int) -> int: ...

    @abstractmethod
    def __setitem__(self, address: int, val: int): ...


class Registers(ABC):
    def __init__(self):
        self.reset()
        self.trace_enabled = False
        self.traces = []

    def values(self) -> Iterable[int]:
        yield from [self[r] for r in R]

    def save_trace(self) -> None:
        self.traces.append(list(self.values()))

    def reset(self) -> None:
        for r in R:
            self[r] = 0
        self[R.PC] = PC_START
        self[R.COND] = FL.POS.value

    @abstractmethod
    def __getitem__(self, key: R) -> int: ...

    @abstractmethod
    def __setitem__(self, key: R, val: int): ...


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

    def write_err(self, text: str) -> None:
        self._write(text, 'error')

    def read(self) -> str:
        return self._read('output')

    def read_err(self):
        return self._read('error')


@dataclasses.dataclass
class VM(ABC):
    reg: Registers
    mem: Memory
    runstate: RunningState
    out: Output

    def reset(self) -> None:
        self.out.write_err('-- RESET --\n')
        self.reg.reset()
        self.runstate.run()

    def continue_(self) -> None:
        if not self.runstate.is_running:
            self.out.write_err('-- HALTED --\n')
            return
        while self.runstate.is_running:
            self.step()

    def step(self) -> None:
        if not self.runstate.is_running:
            self.out.write_err('-- HALTED --\n')
            return

        if self.reg.trace_enabled:
            self.reg.save_trace()

        self._step()

    @abstractmethod
    def _step(self): ...
