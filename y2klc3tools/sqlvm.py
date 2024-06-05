import array
from collections.abc import Iterable
from pathlib import Path
import sqlite3
import sys
from typing import Any

from . import UINT16_MAX, PC_START
from .vm_def import OP, R, FL

import sqlparse
from tabulate import tabulate


class SqlMemory:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

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

        origin = int.from_bytes(image_binary[:2], byteorder='big')

        # write image
        max_read = (UINT16_MAX - origin) * 2
        if len(image_binary[2:]) > max_read:
            raise Exception("Image file too big to load.")
        if len(image_binary[2:]) % 2 != 0:
            raise Exception("Image file doesn't map to a whole number of 2 byte words.")
        memory = array.array("H", image_binary[2:])
        memory.byteswap()

        # bulk insert into memory
        sql = """INSERT INTO memory (address, value) VALUES (?, ?)
            ON CONFLICT(address) DO UPDATE SET value = excluded.value"""
        self.conn.executemany(sql, ((i, v) for i, v in enumerate(memory, origin)))
        self.conn.commit()

    def __getitem__(self, address):
        address = address % UINT16_MAX
        sql = "SELECT value FROM memory WHERE address = ?"
        cur = self.conn.execute(sql, (address,))
        try:
            return cur.fetchone()[0]
        except TypeError:
            return 0

    def __setitem__(self, address, val):
        address = address % UINT16_MAX
        # insert on conflict update
        sql = """
            INSERT INTO memory (address, value) VALUES (?, ?)
            ON CONFLICT(address) DO UPDATE SET value = excluded.value
            """
        self.conn.execute(sql, (address, val))
        self.conn.commit()

    def __len__(self):
        return UINT16_MAX


class SqlRegisters:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def __getitem__(self, __name: R) -> Any:
        if not isinstance(__name, R):
            raise AttributeError(f"Invalid Register {__name}")
        sql = f"SELECT {__name.name} FROM register"
        cur = self.conn.execute(sql)
        return cur.fetchone()[0]

    def __setitem__(self, __name: R, __value: int) -> None:
        if not isinstance(__name, R):
            raise AttributeError(f"Invalid Register {__name}")
        sql = f"UPDATE register SET {__name.name} = ?"
        self.conn.execute(sql, (__value % UINT16_MAX,))
        self.conn.commit()

    def values(self) -> Iterable[int]:
        sql = f"SELECT {','.join(R._member_names_)} FROM register"
        cur = self.conn.execute(sql)
        yield from cur.fetchone()


class SqlOutput:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _write(self, text: str, channel: str):
        sql = "INSERT INTO msgout VALUES(?, ?)"
        self.conn.execute(sql, (text, channel))
        self.conn.commit()

    def _read(self, channel: str):
        sql = f"SELECT msg FROM msgout WHERE channel = '{channel}'"
        cur = self.conn.execute(sql)
        msg_lines = ''.join(msg + '\n' for (msg,) in cur.fetchall())

        sql = f"DELETE FROM msgout WHERE channel = '{channel}'"
        self.conn.execute(sql)
        self.conn.commit()

        return msg_lines

    def write(self, text: str):
        self._write(text, 'output')

    def write_err(self, text: str):
        self._write(text, 'error')

    def read(self) -> str:
        return self._read('output')

    def read_err(self):
        return self._read('error')


class SqlVM:
    def __init__(self, trace_registers: bool = False):
        self.trace_registers = trace_registers
        self.reg_trace = []

        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()

        self.create_hardware()

        self.memory: SqlMemory = SqlMemory(self.conn)
        self.reg: SqlRegisters = SqlRegisters(self.conn)
        self.out: SqlOutput = SqlOutput(self.conn)

    @property
    def is_running(self) -> bool:
        sql = "SELECT is_running FROM signal"
        cur = self.conn.execute(sql)
        return cur.fetchone()[0] == 1

    @is_running.setter
    def is_running(self, value: bool):
        sql = "UPDATE signal SET is_running = ?"
        intvalue = 1 if value else 0
        self.conn.execute(sql, (intvalue,))
        self.conn.commit()

    def run_and_print(self, sql):
        try:
            self.cursor.execute(sql)
        except sqlite3.OperationalError as e:
            print("Error:\n", sql, file=sys.stderr)
            raise e

        self.conn.commit()

        rows = self.cursor.fetchall()
        if self.cursor.description is None:
            return

        # format ints as hex
        frows = []
        for r in rows:
            fr = []
            for v in r:
                if isinstance(v, int):
                    fr.append(f"0x{v:02x}")
                else:
                    fr.append(v)
            frows.append(fr)

        print(tabulate(frows, headers=[d[0] for d in self.cursor.description]), end='\n\n')

    def run(self, sqlscript):
        for sql in sqlparse.split(sqlscript):
            self.run_and_print(sql)

    def run_and_trace(self, sqlscript):
        self.run_and_print("DELETE FROM msgout WHERE channel = 'trace'")
        self.run(sqlscript)
        self.run_and_print("SELECT * FROM msgout WHERE channel = 'trace'")

    def create_hardware(self):
        THIS_DIR = Path(__file__).parent
        with open(THIS_DIR / 'sqlvm.sql') as f:
            sqlscript = f.read()
        self.run(sqlscript)

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

    def load_binary_from_bytes(self, image_binary_bytes: bytes):
        """Load bytes directly into memory."""
        self.memory.load_binary(image_binary_bytes)

    def reset(self):
        self.out.write_err('-- RESET --')
        self.reg[R.R0] = 0
        self.reg[R.R1] = 0
        self.reg[R.R2] = 0
        self.reg[R.R3] = 0
        self.reg[R.R4] = 0
        self.reg[R.R5] = 0
        self.reg[R.R6] = 0
        self.reg[R.R7] = 0
        self.reg[R.PC] = PC_START
        self.reg[R.COND] = 1  # FL.POS
        self.is_running = True
        self.tracing = 0

    def step(self, trace=False):
        if not self.is_running:
            self.out.write_err('-- HALTED --')
            return

        if self.trace_registers:
            self.reg_trace.append(list(self.reg.values()))

        if trace:
            runner = self.run_and_trace
        else:
            runner = self.run

        sqlscript = """
            UPDATE signal SET clk = 1;
            UPDATE signal SET clk = 0;
            """
        runner(sqlscript)

    def continue_(self):
        if not self.is_running:
            self.out.write_err('-- HALTED --')
            return
        while self.is_running:
            self.step()
