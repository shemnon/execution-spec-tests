"""
Tests for opcode strategies
"""
import pytest

from ethereum_fuzzer_basicblocks.basicblocks import BasicBlock
from ethereum_fuzzer_differential.strategies.opcode_strategies import flatten_block
from ethereum_test_tools import Opcodes as Op
from ethereum_test_vm import Bytecode
from ethereum_test_vm.opcode import valid_eof_opcodes_by_num


@pytest.mark.parametrize(
    "initial, expected",
    [
        pytest.param(Op.PUSH0 + Op.POP, Bytecode(), id="push0 / pop"),
        pytest.param(Op.POP + Op.PUSH0, Bytecode(), id="pop / push0"),
        pytest.param(
            Op.PUSH0 + Op.ADD + Op.POP, Op.PUSH0 + Op.ADD + Op.POP, id="push0 / add / pop"
        ),
        pytest.param(
            Op.POP + Op.ADD + Op.PUSH0, Op.POP + Op.ADD + Op.PUSH0, id="pop / add / push0"
        ),
        pytest.param(
            Op.PUSH0 + Op.ADD + Op.POP + Op.PUSH0,
            Op.PUSH0 + Op.ADD,
            id="push0 / add / pop / push0",
        ),
        pytest.param(
            Op.POP + Op.ADD + Op.PUSH0 + Op.POP, Op.POP + Op.ADD, id="pop / add / push0 / pop"
        ),
        *[
            pytest.param(
                valid_eof_opcodes_by_num[0x5F + x] + Op.POP, Bytecode(), id="push%d / pop" % x
            )
            for x in range(1, 33)
        ],
        *[
            pytest.param(
                Op.POP + valid_eof_opcodes_by_num[0x5F + x], Bytecode(), id="pop / push%d" % x
            )
            for x in range(1, 33)
        ],
        pytest.param(
            Op.PUSH0 * 2 + Op.POP * 3 + Op.PUSH0, Bytecode(), id="push0x2 / popx3 / push0"
        ),
    ],
)
def test_flatten_block(initial: Bytecode, expected: Bytecode):
    """Tests flatting of blocks"""
    block = BasicBlock("test")
    block.append_bytecode(initial)
    assert flatten_block(block).bytecode() == expected
