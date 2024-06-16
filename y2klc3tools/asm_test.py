import pathlib

import pytest

from y2klc3tools.asm import assemble, dump_symbol_table

# Collect all .asm files in the tests directory
test_case_dir = pathlib.Path(__file__).parent.parent / 'obj' / 'asm'
test_cases = [f.stem for f in test_case_dir.glob('*.asm')]


@pytest.mark.parametrize('case', test_cases)
def test_asm_files(case: str) -> None:
    # TODO: split this into obj and sym tests and give better name
    with (test_case_dir / f'{case}.asm').open('r') as f:
        asm = f.read()

    symbol_table, assembled_bytes = assemble(asm)

    with (test_case_dir / f'{case}.obj').open('rb') as f:
        expected_bytes = f.read()
    assert assembled_bytes == expected_bytes

    try:
        with (test_case_dir / f'{case}.sym').open('r') as f:
            expected_symbol_table = f.read()
        assert dump_symbol_table(symbol_table) == expected_symbol_table
    except FileNotFoundError:
        # no symbol testcase for this asm file
        # TODO: ensure all asm files have a corresponding sym file
        pass
