"""
Tests parsing EOF bytestreams into code blocks
"""

import pytest

from ethereum_fuzzer_codeblocks.codeblocks import CodeBlockContainer, CodePoint
from ethereum_test_tools import Opcodes as Op

sample_contracts = [
    pytest.param(
        "ef0001010004020001001604000000008000026001e10006600a600255005f35e1fff5600b60025500",
        id="simple",
    ),
    pytest.param(
        "ef00010100100200040005000600080002040001000080000101000001000100"
        "03020300035fe300010050e3000250e43080e300035050e480e4ef",
        id="multiple_code",
    ),
    pytest.param(
        "ef00010100140200050012000800070005000e04004000008000020000000200"
        "0000020000000200000003e30001e30002e30003e30004600160005500610020"
        "d0600155e4d10020600255e4d2600355e4602060206000d3600051600455e400"
        "0100020003000400050006000700080009000a000b000c000d000e000f001000"
        "1100120013001400150016001700180019001a001b001c001d001e001f0020",
        id="data_section",
    ),
    pytest.param(
        "ef0001010004020001000e030001003204000000008000046000600060006000"
        "ec0060005500ef00010100040200010006030001001404000000008000026000"
        "6000ee00ef00010100040200010001040000000080000000",
        id="simple_container",
    ),
    pytest.param(
        "ef0001010008020002000d000603000200320014040000000080000400800002"
        "6000600060006000ec00e5000160006000ee01ef000101000402000100060300"
        "010014040000000080000260006000ee00ef0001010004020001000104000000"
        "0080000000ef00010100040200010001040000000080000000",
        id="double_container",
    ),
    pytest.param(
        "ef0001010004020001001104000000008000025fe10003e0000761201560015500e0fff6",
        id="rjump_positive_negative",
    ),
    pytest.param(
        "ef0001010004020001001604000000008000026001e10006600a600255005f35e1fff5600b60025500",
        id="rjumpi_condition_backwards",
    ),
    pytest.param(
        "ef0001010004020001001404000000008000026000e20200030000fff65b5b0061201560015500",
        id="rjumpv_size_3",
    ),
    pytest.param(
        "ef00010100040200010011040000000080000260015415e1000100612015600155e50000",
        id="one_byte_section",
    ),
    pytest.param(
        "ef0001010004020001000d04000000008000026000e200000061201560015500", id="rjumpv[0]"
    ),
    pytest.param(
        "ef0001010004020001001b04000000008000025f506000e100095f5061201560"
        "0155005f506000e200ffef5f5000",
        id="rjumpv",
    ),
    pytest.param(
        "ef0001010010020004000f0005000e000e040000000080000501030004010400"
        "05010400045fe3000161201560015560006000f3e3000250e4e100045fe50003"
        "5f5f5f5f5f50e45063deadb12d6003555f5f5f5fe4",
        id="RJUMP_CALLF_range",
    ),
    pytest.param(
        "ef000101001002000400120005000e000e040000000080000301030004010400"
        "05010400045fe3000150505061201560015560006000f3e3000250e4e100045f"
        "e500035f5f5f5f5f50e45063deadb12d6003555f5f5f5fe4",
        id="JUMPF_height",
    ),
    pytest.param(
        "ef00010100100200040008000e00040007040000000080000400020004028000" 
        "020000000260006000e30001005f5f600035e10001e45f5fe50002e3000300612015600155e4",
        id="RJUMPI_stack",
    ),
]


@pytest.mark.parametrize(
    "input",
    sample_contracts,
)
def test_parse_bytes(input: str):
    """
    Simple round trip test for parsebytes
    """
    container = CodeBlockContainer(bytes.fromhex(input))
    assert container is not None

    encoded = container.encode()

    actual = encoded.hex()
    assert input.startswith(actual)


@pytest.mark.parametrize(
    "input",
    sample_contracts,
)
def test_insert_opcode(input: str):
    """Insert a push/pop in every block to test reconciliation"""
    container = CodeBlockContainer(bytes.fromhex(input))
    assert container is not None

    for section in container.code_sections:
        for block in section.blocks:
            block.insert_code_point(0, CodePoint(Op.POP))
            block.insert_code_point(0, CodePoint(Op.PUSH0))
    container.reconcile_bytecode()


@pytest.mark.parametrize(
    "input",
    sample_contracts,
)
def test_reconcile(input: str):
    """
    Simple round trip test for parsebytes
    """
    container = CodeBlockContainer(bytes.fromhex(input))
    assert container is not None

    container.reconcile_bytecode()

    encoded = container.encode()
    actual = encoded.hex()
    assert input.startswith(actual)
