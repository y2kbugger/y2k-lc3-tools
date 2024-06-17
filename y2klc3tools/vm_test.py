import pytest

from y2klc3tools import PC_START, UINT16_MAX
from y2klc3tools.pyvm import PyVM, R
from y2klc3tools.sqlvm import SqlVM
from y2klc3tools.vm import VM


@pytest.fixture(params=[SqlVM, PyVM])
def vm(request: pytest.FixtureRequest) -> PyVM:
    IVM = request.param
    vm = IVM()
    vm.reset()
    return vm


NOP = '16BF'
HLT = 'F025'


def test_load_binary(vm: VM) -> None:
    image_bytes = '3000 E005 2213'

    vm.mem.load_binary_from_hex(image_bytes)

    assert vm.mem[0x3000] == 0xE005


def test_poke_memory(vm: VM) -> None:
    vm.mem[0x3000] = 0xBABE
    assert vm.mem[0x3000] == 0xBABE


def test_load_binary_bytes(vm: VM) -> None:
    image_bytes_hex = '3000 E005 2213'
    image_bytes = bytes.fromhex(image_bytes_hex)

    vm.mem.load_binary_from_bytes(image_bytes)

    assert vm.mem[0x3000] == 0xE005


def test_load_binary_memory_size_is_correct(vm: VM) -> None:
    image_bytes = '3000 E005 2213'

    vm.mem.load_binary_from_hex(image_bytes)

    assert len(vm.mem) == UINT16_MAX


def test_load_binary_as_big_as_possible(vm: VM) -> None:
    origin = '0000'
    image_bytes = origin + 'DEAD' * UINT16_MAX

    vm.mem.load_binary_from_hex(image_bytes)

    assert vm.mem[0x0000] == 0xDEAD
    assert vm.mem[0xFFFF] == 0xDEAD


def test_load_binary_fails_when_too_big(vm: VM) -> None:
    origin = '0000'
    image_bytes = origin + 'DEAD' * (UINT16_MAX + 1)

    with pytest.raises(Exception, match="too big"):
        vm.mem.load_binary_from_hex(image_bytes)


def test_load_binary_fails_with_partial_word(vm: VM) -> None:
    origin = '0000'
    image_bytes = origin + 'DEAD EE'

    with pytest.raises(Exception, match="2 byte words"):
        vm.mem.load_binary_from_hex(image_bytes)


def test_is_running_after_reset(vm: VM) -> None:
    assert vm.runstate.is_running


def test_step_moves_pc_by_one(vm: VM) -> None:
    origin = '3000'
    image_bytes = origin + NOP
    vm.mem.load_binary_from_hex(image_bytes)
    pc_start = vm.reg[R.PC]
    print(f'PC start: {pc_start}')

    vm.step()

    assert vm.reg[R.PC] == pc_start + 1


def test_continue_runs_until_halted(vm: VM) -> None:
    origin = '3000'
    image_bytes = origin + NOP * 10 + 'F025'
    vm.mem.load_binary_from_hex(image_bytes)

    vm.continue_()

    assert not vm.runstate.is_running
    assert vm.reg[R.PC] == PC_START + 10 + 1


def test_isnt_running_after_halt(vm: VM) -> None:
    origin = '3000'
    image_bytes = origin + NOP * 10 + 'F025'
    vm.mem.load_binary_from_hex(image_bytes)
    vm.continue_()
    assert not vm.runstate.is_running


def test_step_complains_if_already_halted(vm: VM) -> None:
    origin = '3000'
    image_bytes = origin + NOP * 10 + 'F025'
    vm.mem.load_binary_from_hex(image_bytes)
    vm.continue_()  # run until halt

    with pytest.raises(Exception, match="HALTED"):
        vm.step()


def test_continue_complains_if_already_halted(vm: VM) -> None:
    origin = '3000'
    image_bytes = origin + NOP * 10 + 'F025'
    vm.mem.load_binary_from_hex(image_bytes)
    vm.continue_()  # run until halt

    with pytest.raises(Exception, match="HALTED"):
        vm.continue_()


@pytest.mark.xfail
def test_vm_can_run_looping_progam_with_output(vm: VM) -> None:
    vm.mem.load_binary_from_file('obj/asm/hello2.obj')
    vm.continue_()
    # check that the program output the expected string

    assert vm.out.read() == "Hello, World!\n" * 5
    assert not vm.runstate.is_running


@pytest.mark.xfail
def test_tracing_vm_can_run_looping_progam_with_register_traces(vm: VM) -> None:
    vm.mem.load_binary_from_file('obj/asm/hello2.obj')
    vm.reg.trace_enabled = True
    vm.continue_()
    assert vm.reg.traces == [
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


@pytest.mark.xfail
def test_tracing_vm_can_run_looping_progam_with_register_traces2(vm: VM) -> None:
    vm.mem.load_binary_from_file('obj/asm/hard.obj')
    vm.reg.trace_enabled = True
    vm.continue_()
    assert vm.reg.traces == [
        [0, 0, 0, 0, 0, 0, 0, 0, 12288, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 12289, 2],
        [0, 0, 0, 65531, 0, 0, 0, 0, 12290, 4],
        [0, 0, 0, 15, 0, 0, 0, 0, 12291, 1],
        [0, 0, 0, 15, 0, 0, 0, 0, 12292, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12293, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12294, 2],
        [0, 0, 0, 15, 0, 0, 0, 65535, 12295, 4],
    ]


@pytest.mark.xfail
def test_tracing_vm_can_run_looping_progam_with_register_traces3(vm: VM) -> None:
    vm.mem.load_binary_from_file('obj/asm/legal.obj')
    vm.reg.trace_enabled = True
    vm.continue_()
    assert vm.reg.traces == [
        [0, 0, 0, 0, 0, 0, 0, 0, 12288, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 12289, 2],
        [0, 0, 0, 65531, 0, 0, 0, 0, 12290, 4],
        [0, 0, 0, 15, 0, 0, 0, 0, 12291, 1],
        [0, 0, 0, 15, 0, 0, 0, 0, 12292, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12293, 2],
        [0, 0, 0, 15, 0, 0, 0, 0, 12294, 2],
        [0, 0, 0, 15, 0, 0, 0, 65535, 12295, 4],
    ]


@pytest.mark.xfail
def test_tracing_vm_can_run_looping_progam_with_register_traces4(vm: VM) -> None:
    vm.mem.load_binary_from_file('obj/asm/instructions.obj')
    vm.reg.trace_enabled = True
    vm.continue_()
    assert vm.reg.traces == [
        [0, 0, 0, 0, 0, 0, 0, 0, 12288, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 12289, 2],
        [0, 0, 0, 65531, 0, 0, 0, 0, 12290, 4],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12291, 4],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12292, 2],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12293, 2],
        [0, 0, 0, 65535, 0, 0, 0, 0, 12294, 2],
        [0, 0, 0, 65535, 0, 0, 0, 65535, 12295, 4],
    ]
