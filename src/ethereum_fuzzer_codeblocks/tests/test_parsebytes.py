"""
Tests parsing EOF bytestreams into code blocks
"""

import pytest

from ethereum_fuzzer_codeblocks.codeblocks import CodeBlockContainer


@pytest.mark.parametrize(
    "input",
    [
        pytest.param(
            "ef0001010004020001001604000000008000026001e10006600a600255005f35"
            "e1fff5600b60025500",
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
            "ef0001010004020001001604000000008000026001e10006600a600255005f35"
            "e1fff5600b60025500",
            id="rjumpi_condition_backwards",
        ),
        pytest.param(
            "ef0001010004020001001404000000008000026000e20200030000fff65b5b0061201560015500",
            id="rjumpv_size_3",
        ),
    ],
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
    # assert encoded == input
