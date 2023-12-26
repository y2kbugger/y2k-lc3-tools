import os
import pytest
import pathlib
from y2klc3tools.asm import assemble, dump_symbol_table

# Collect all .asm files in the tests directory
test_case_dir = pathlib.Path(__file__).parent.parent / 'obj' / 'asm'
asm_files = test_case_dir.glob('*.asm')
test_cases = [os.path.splitext(os.path.basename(f))[0] for f in asm_files]


@pytest.mark.parametrize('case', test_cases)
def test_asm_files(case):
    with open(test_case_dir / f'{case}.asm', 'r') as f:
        asm = f.read()

    symbol_table, assembled_bytes = assemble(asm)

    with open(test_case_dir / f'{case}.obj', 'rb') as f:
        expected_bytes = f.read()
    assert assembled_bytes == expected_bytes

    try:
        with open(test_case_dir / f'{case}.sym', 'r') as f:
            expected_symbol_table = f.read()
        assert dump_symbol_table(symbol_table) == expected_symbol_table
    except FileNotFoundError:
        # no testcase for this asm file
        pass
