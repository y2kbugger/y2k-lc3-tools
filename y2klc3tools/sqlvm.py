import array
from collections.abc import Iterable
from pathlib import Path
import sqlite3
import sys
from typing import Any

from . import UINT16_MAX, PC_START
from .vm_def import OP, R, FL
from .vm_abc import Memory, Output, Registers, RunningState, VM

import sqlparse
from tabulate import tabulate


class SqlMemory(Memory):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def load_words_at_address(self, words: array.array[int], address: int):
        assert len(words) + address <= UINT16_MAX
        assert address >= 0
        assert words.itemsize == 2  # 2 bytes per word

        # use executemany for an approximate 3x speedup over naive loop
        sql = """INSERT INTO memory (address, value) VALUES (?, ?)
            ON CONFLICT(address) DO UPDATE SET value = excluded.value"""
        self.conn.executemany(sql, ((a, w) for a, w in enumerate(words, address)))

    def __getitem__(self, address: int) -> int:
        address = address % UINT16_MAX
        sql = "SELECT value FROM memory WHERE address = ?"
        cur = self.conn.execute(sql, (address,))
        try:
            return cur.fetchone()[0]
        except TypeError:
            return 0

    def __setitem__(self, address: int, val: int):
        address = address % UINT16_MAX
        # insert on conflict update
        sql = """
            INSERT INTO memory (address, value) VALUES (?, ?)
            ON CONFLICT(address) DO UPDATE SET value = excluded.value
            """
        self.conn.execute(sql, (address, val))
        self.conn.commit()


class SqlRegisters(Registers):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        super().__init__()

    def __getitem__(self, key: R) -> int:
        if not isinstance(key, R):
            raise AttributeError(f"Invalid Register {key}")
        sql = f"SELECT {key.name} FROM register"
        cur = self.conn.execute(sql)
        return cur.fetchone()[0]

    def __setitem__(self, key: R, val: int) -> None:
        if not isinstance(key, R):
            raise AttributeError(f"Invalid Register {key}")
        sql = f"UPDATE register SET {key.name} = ?"
        self.conn.execute(sql, (val % UINT16_MAX,))
        self.conn.commit()


class SqlRunningState(RunningState):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        super().__init__()

    @property
    def is_running(self):
        sql = "SELECT is_running FROM signal"
        cur = self.conn.execute(sql)
        return cur.fetchone()[0] == 1

    @is_running.setter
    def is_running(self, value: bool):
        sql = "UPDATE signal SET is_running = ?"
        intvalue = 1 if value else 0
        self.conn.execute(sql, (intvalue,))
        self.conn.commit()


class SqlOutput(Output):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _write(self, text: str, channel: str):
        sql = "INSERT INTO msgout VALUES(?, ?)"
        self.conn.execute(sql, (text, channel))
        self.conn.commit()

    def _read(self, channel: str):
        sql = f"SELECT msg FROM msgout WHERE channel = '{channel}'"
        cur = self.conn.execute(sql)
        msg = ''.join(msg for (msg,) in cur.fetchall())

        sql = f"DELETE FROM msgout WHERE channel = '{channel}'"
        self.conn.execute(sql)
        self.conn.commit()

        return msg


class SqlVM(VM):
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        self.create_hardware()

        self.mem = SqlMemory(self.conn)
        self.runstate = SqlRunningState(self.conn)
        self.reg = SqlRegisters(self.conn)
        self.out = SqlOutput(self.conn)

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

    def _step(self):
        sqlscript = """
            UPDATE signal SET clk = 1;
            UPDATE signal SET clk = 0;
            """
        self.run(sqlscript)
