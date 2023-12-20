import pytest

from y2klc3tools.vm import VM, mem_read, UINT16_MAX

def test_load_binary():
    image_bytes = b'\x30\x00\xE0\x05\x22\x13'
    vm = VM()

    vm.load_binary(image_bytes)

    assert mem_read(0x3000) == 0xE005

def test_load_image_memory_size_is_correct():
    image_bytes = b'\x30\x00\xE0\x05\x22\x13'
    vm = VM()

    vm.load_binary(image_bytes)

    assert len(vm.memory) == UINT16_MAX

def test_image_file_as_big_as_possible():
    origin = b'\x00\x00'
    image_bytes = origin + b'\xDE\xAD' * UINT16_MAX
    vm = VM()

    vm.load_binary(image_bytes)

    assert mem_read(0x0000) == 0xDEAD
    assert mem_read(0xFFFF) == 0xDEAD

def test_image_file_too_big():
    origin = b'\x00\x00'
    image_bytes = origin + b'\xDE\xAD' * (UINT16_MAX + 1)
    vm = VM()

    with pytest.raises(Exception, match="too big"):
        vm.load_binary(image_bytes)

def test_image_file_fail_with_partial_word():
    origin = b'\x00\x00'
    image_bytes = origin + b'\xDE\xAD\xEE'
    vm = VM()

    with pytest.raises(Exception, match="2 byte words"):
        vm.load_binary(image_bytes)

@pytest.fixture()
def vm():
    vm = VM()
    vm.reset()
    return vm

@pytest.fixture()
def vm_nops(vm):
    """Load a program that does nothing but run add instructions repeatedly"""
    origin = b'\x00\x00'
    image_bytes = origin + b'\x16\xBF' * (UINT16_MAX)
    vm.load_binary(image_bytes)
    return vm

#continue
#step
#halted