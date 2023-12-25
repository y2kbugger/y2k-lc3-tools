import pytest

from y2klc3tools.vm import VM, mem_read, UINT16_MAX


def test_load_binary():
    image_bytes = '3000 E005 2213'
    vm = VM()

    vm.load_binary_from_hex(image_bytes)

    assert mem_read(0x3000) == 0xE005


def test_load_binary_memory_size_is_correct():
    image_bytes = '3000 E005 2213'
    vm = VM()

    vm.load_binary_from_hex(image_bytes)

    assert len(vm.memory) == UINT16_MAX


def test_load_binary_as_big_as_possible():
    origin = '0000'
    image_bytes = origin + 'DEAD' * UINT16_MAX
    vm = VM()

    vm.load_binary_from_hex(image_bytes)

    assert mem_read(0x0000) == 0xDEAD
    assert mem_read(0xFFFF) == 0xDEAD


def test_load_binary_fails_when_too_big():
    origin = '0000'
    image_bytes = origin + 'DEAD' * (UINT16_MAX + 1)
    vm = VM()

    with pytest.raises(Exception, match="too big"):
        vm.load_binary_from_hex(image_bytes)


def test_load_binary_fails_with_partial_word():
    origin = '0000'
    image_bytes = origin + 'DEAD EE'
    vm = VM()

    with pytest.raises(Exception, match="2 byte words"):
        vm.load_binary_from_hex(image_bytes)


@pytest.fixture()
def vm() -> VM:
    vm = VM()
    vm.reset()
    return vm


@pytest.fixture()
def vm_nops(vm: VM) -> VM:
    """Load a program that does nothing but run add instructions repeatedly"""
    origin = '0000'
    image_bytes = origin + '16BF' * (UINT16_MAX)
    vm.load_binary_from_hex(image_bytes)
    return vm


def test_step_moves_pc_by_one(vm_nops: VM, capsys: pytest.CaptureFixture):
    pc_start = vm_nops.R.PC

    vm_nops.step()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert vm_nops.R.PC == pc_start + 1


def test_continue_runs_until_halted(vm_nops: VM, capsys: pytest.CaptureFixture):
    vm_nops.memory[0x3200] = 0xF025  # HLT
    vm_nops.continue_()
    captured = capsys.readouterr()
    assert captured.err == "-- HALT --\n"
    assert vm_nops.R.PC == 0x3200 + 1


def test_step_complains_if_already_halted(vm_nops: VM, capsys: pytest.CaptureFixture):
    vm_nops.memory[0x3200] = 0xF025  # HLT
    vm_nops.continue_()
    _ = capsys.readouterr()  # clear output
    vm_nops.step()
    captured = capsys.readouterr()
    assert captured.err == "-- HALTED --\n"


def test_continue_complains_if_already_halted(vm_nops: VM, capsys: pytest.CaptureFixture):
    vm_nops.memory[0x3200] = 0xF025  # HLT
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
