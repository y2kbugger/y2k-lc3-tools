import pytest

from y2klc3tools import UINT16_MAX, PC_START
from y2klc3tools.vm import VM, R
from y2klc3tools.sqlvm import SqlVM


@pytest.fixture(params=[SqlVM, VM])
def vm(request: pytest.FixtureRequest) -> VM:
    IVM = request.param
    vm = IVM()
    vm.reset()
    return vm


@pytest.fixture()
def vm_nops(vm: VM) -> VM:
    """Load a program that does nothing but run add instructions repeatedly"""
    origin = '0000'
    image_bytes = origin + '16BF' * (UINT16_MAX)
    vm.load_binary_from_hex(image_bytes)
    return vm


def test_load_binary(vm: VM):
    image_bytes = '3000 E005 2213'

    vm.load_binary_from_hex(image_bytes)

    assert vm.memory[0x3000] == 0xE005


def test_poke_memory(vm: VM):
    vm.memory[0x3000] = 0xBABE
    assert vm.memory[0x3000] == 0xBABE


def test_load_binary_bytes(vm: VM):
    image_bytes_hex = '3000 E005 2213'
    image_bytes = bytes.fromhex(image_bytes_hex)

    vm.load_binary_from_bytes(image_bytes)

    assert vm.memory[0x3000] == 0xE005


def test_load_binary_memory_size_is_correct(vm: VM):
    image_bytes = '3000 E005 2213'

    vm.load_binary_from_hex(image_bytes)

    assert len(vm.memory) == UINT16_MAX


def test_load_binary_as_big_as_possible(vm: VM):
    origin = '0000'
    image_bytes = origin + 'DEAD' * UINT16_MAX

    vm.load_binary_from_hex(image_bytes)

    assert vm.memory[0x0000] == 0xDEAD
    assert vm.memory[0xFFFF] == 0xDEAD


def test_load_binary_fails_when_too_big(vm: VM):
    origin = '0000'
    image_bytes = origin + 'DEAD' * (UINT16_MAX + 1)

    with pytest.raises(Exception, match="too big"):
        vm.load_binary_from_hex(image_bytes)


def test_load_binary_fails_with_partial_word(vm: VM):
    origin = '0000'
    image_bytes = origin + 'DEAD EE'

    with pytest.raises(Exception, match="2 byte words"):
        vm.load_binary_from_hex(image_bytes)


def test_step_moves_pc_by_one(vm_nops: VM, capsys: pytest.CaptureFixture):
    pc_start = vm_nops.reg[R.PC]

    vm_nops.step()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert vm_nops.reg[R.PC] == pc_start + 1


def test_is_running_after_reset(vm_nops: VM):
    assert vm_nops.is_running


def test_continue_runs_until_halted(vm_nops: VM, capsys: pytest.CaptureFixture):
    halt_location = PC_START + 0x200
    vm_nops.memory[halt_location] = 0xF025  # HLT
    vm_nops.continue_()
    captured = capsys.readouterr()
    assert captured.err == "-- HALT --\n"
    assert vm_nops.reg[R.PC] == halt_location + 0x1


def test_isnt_running_after_halt(vm_nops: VM):
    halt_location = PC_START + 0x200
    vm_nops.memory[halt_location] = 0xF025  # HLT
    vm_nops.continue_()
    assert not vm_nops.is_running


def test_step_complains_if_already_halted(vm_nops: VM, capsys: pytest.CaptureFixture):
    vm_nops.memory[PC_START + 0x200] = 0xF025  # HLT
    vm_nops.continue_()
    _ = capsys.readouterr()  # clear output
    vm_nops.step()
    captured = capsys.readouterr()
    assert captured.err == "-- HALTED --\n"


def test_continue_complains_if_already_halted(vm_nops: VM, capsys: pytest.CaptureFixture):
    vm_nops.memory[PC_START + 0x200] = 0xF025  # HLT
    vm_nops.continue_()
    _ = capsys.readouterr()  # clear output
    vm_nops.continue_()
    captured = capsys.readouterr()
    assert captured.err == "-- HALTED --\n"


def test_vm_can_run_looping_progam_with_output(vm: VM, capsys: pytest.CaptureFixture):
    vm.load_binary_from_file('obj/asm/hello2.obj')
    vm.continue_()
    # check that the program output the expected string
    captured = capsys.readouterr()
    # assert captured.out == "hell0ddd"
    assert captured.out == "Hello, World!\n" * 5
    assert captured.err == "-- HALT --\n"


def test_tracing_vm_can_run_looping_progam_with_register_traces(vm: VM):
    vm.load_binary_from_file('obj/asm/hello2.obj')
    vm.tracing = True
    vm.continue_()
    assert vm.reg_trace == [
        [0, 0, 0, 0, 0, 0, 0, 0, 12288, 1],
        [12294, 0, 0, 0, 0, 0, 0, 0, 12289, 1],
        [12294, 5, 0, 0, 0, 0, 0, 0, 12290, 1],
        [12294, 5, 0, 0, 0, 0, 0, 0, 12291, 1],
        [12294, 4, 0, 0, 0, 0, 0, 0, 12292, 1],
        [12294, 4, 0, 0, 0, 0, 0, 0, 12290, 1],
        [12294, 4, 0, 0, 0, 0, 0, 0, 12291, 1],
        [12294, 3, 0, 0, 0, 0, 0, 0, 12292, 1],
        [12294, 3, 0, 0, 0, 0, 0, 0, 12290, 1],
        [12294, 3, 0, 0, 0, 0, 0, 0, 12291, 1],
        [12294, 2, 0, 0, 0, 0, 0, 0, 12292, 1],
        [12294, 2, 0, 0, 0, 0, 0, 0, 12290, 1],
        [12294, 2, 0, 0, 0, 0, 0, 0, 12291, 1],
        [12294, 1, 0, 0, 0, 0, 0, 0, 12292, 1],
        [12294, 1, 0, 0, 0, 0, 0, 0, 12290, 1],
        [12294, 1, 0, 0, 0, 0, 0, 0, 12291, 1],
        [12294, 0, 0, 0, 0, 0, 0, 0, 12292, 2],
        [12294, 0, 0, 0, 0, 0, 0, 0, 12293, 2],
    ]


def test_tracing_vm_can_run_looping_progam_with_register_traces2(vm: VM):
    vm.load_binary_from_file('obj/asm/hard.obj')
    vm.tracing = True
    vm.continue_()
    assert vm.reg_trace == [
        [0, 0, 0, 0, 0, 0, 0, 0, 12288, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 12289, 2],
        [0, 0, 0, 65531, 0, 0, 0, 0, 12290, 4],
        [0, 0, 0, 15, 0, 0, 0, 0, 12291, 1],
        [0, 0, 0, 15, 0, 0, 0, 0, 12292, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12293, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12294, 2],
        [0, 0, 0, 15, 0, 0, 0, 65535, 12295, 4],
    ]


def test_tracing_vm_can_run_looping_progam_with_register_traces3(vm: VM):
    vm.load_binary_from_file('obj/asm/legal.obj')
    vm.tracing = True
    vm.continue_()
    assert vm.reg_trace == [
        [0, 0, 0, 0, 0, 0, 0, 0, 12288, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 12289, 2],
        [0, 0, 0, 65531, 0, 0, 0, 0, 12290, 4],
        [0, 0, 0, 15, 0, 0, 0, 0, 12291, 1],
        [0, 0, 0, 15, 0, 0, 0, 0, 12292, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12293, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12294, 2],
        [0, 0, 0, 15, 0, 0, 0, 65535, 12295, 4],
    ]


def test_tracing_vm_can_run_looping_progam_with_register_traces4(vm: VM):
    vm.load_binary_from_file('obj/asm/instructions.obj')
    vm.tracing = True
    vm.continue_()
    assert vm.reg_trace == [
        [0, 0, 0, 0, 0, 0, 0, 0, 12288, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 12289, 2],
        [0, 0, 0, 65531, 0, 0, 0, 0, 12290, 4],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12291, 4],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12292, 2],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12293, 2],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12294, 2],
        [0, 0, 0, 65535, 0, 0, 0, 65535, 12295, 4],
    ]
