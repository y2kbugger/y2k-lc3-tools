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


def test_step_moves_pc_by_one(vm_nops: VM):
    pc_start = vm_nops.R.PC

    vm_nops.step()

    assert vm_nops.R.PC == pc_start + 1


def test_continue_runs_until_halted(vm_nops: VM):
    vm_nops.memory[0x3200] = 0xF025  # HLT
    vm_nops.continue_()
    assert vm_nops.R.PC == 0x3200 + 1
